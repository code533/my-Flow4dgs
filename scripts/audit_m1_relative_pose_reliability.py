#!/usr/bin/env python3
"""Audit whether calibrated M1 local uncertainty predicts baseline relative-pose reliability.

This is diagnostic-only: it does not modify tracking, mapping, masks, keyframes,
or Gaussian state.  The primary target is the FINAL frontend tracking increment
for the same frame transition used by M1.  We reconstruct the actual previous
pose used by that transition from the saved motion prior and M1 applied update,
so the audit does not rely on a stale previous-frame diagnostic after backend
pose refinement.

Primary convention (matched to M1 / Flow4DGS code):
    T_prior_k = T_prev_used @ T_rel_applied
    T_rel_final = inv(T_prev_used) @ T_final_k
    e_final = Log(inv(T_rel_gt) @ T_rel_final)

Positive controls report M1 raw/applied relative-motion error against the same
saved T_rel_gt.  No trajectory alignment is performed.  Flow4DGS initializes
frame 0 from GT, so estimated and GT poses are already expressed in the common
dataset gauge.  We deliberately do not claim that the right-composed increment
is invariant to arbitrary changes of world gauge.
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from utils.m1_mapping_uncertainty import M1MappingSignal
from utils.m2_uncertainty import SE3_log


def load_pt(path):
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def finite(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def rankdata(values):
    x = np.asarray(values, dtype=np.float64)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(x)
    i = 0
    while i < len(x):
        j = i + 1
        while j < len(x) and x[order[j]] == x[order[i]]:
            j += 1
        ranks[order[i:j]] = 0.5 * ((i + 1) + j)
        i = j
    return ranks


def spearman(x, y):
    pairs = [(float(a), float(b)) for a, b in zip(x, y) if finite(a) and finite(b)]
    if len(pairs) < 3:
        return float("nan"), len(pairs)
    xx, yy = zip(*pairs)
    rx, ry = rankdata(xx), rankdata(yy)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return float("nan"), len(pairs)
    return float(np.corrcoef(rx, ry)[0, 1]), len(pairs)


def qstats(values):
    x = np.asarray([float(v) for v in values if finite(v)], dtype=np.float64)
    if x.size == 0:
        return {"n": 0}
    return {
        "n": int(x.size),
        "median": float(np.median(x)),
        "q25": float(np.quantile(x, 0.25)),
        "q75": float(np.quantile(x, 0.75)),
        "q90": float(np.quantile(x, 0.90)),
        "q95": float(np.quantile(x, 0.95)),
        "mean": float(np.mean(x)),
    }


def as_T(x, name):
    if not isinstance(x, torch.Tensor) or tuple(x.shape) != (4, 4):
        raise ValueError(f"{name} must be a 4x4 tensor")
    T = x.detach().cpu().double()
    if not bool(torch.isfinite(T).all()):
        raise ValueError(f"{name} contains non-finite values")
    return T


def se3_error(T_est, T_gt):
    e = SE3_log(torch.linalg.inv(T_gt) @ T_est)
    return float(torch.linalg.norm(e[:3])), float(torch.linalg.norm(e[3:]))


def rot_det_error(T):
    return abs(float(torch.linalg.det(T[:3, :3])) - 1.0)


def last_row_error(T):
    ref = torch.tensor([0.0, 0.0, 0.0, 1.0], dtype=T.dtype)
    return float(torch.max(torch.abs(T[3] - ref)))


def load_by_frame(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    out = {}
    for path in sorted(directory.glob("*.pt")):
        d = load_pt(path)
        frame = int(d.get("frame", int(path.stem)))
        out[frame] = d
    return out


def metric_summary(rows, uncertainty_key="u"):
    targets = (
        "m1_raw_error_t_m", "m1_raw_error_r_rad",
        "m1_applied_error_t_m", "m1_applied_error_r_rad",
        "slam_final_rel_error_t_m", "slam_final_rel_error_r_rad",
    )
    out = {"n": len(rows), "spearman": {}}
    for target in targets:
        rho, n = spearman(
            [r[uncertainty_key] for r in rows],
            [r[target] for r in rows],
        )
        out["spearman"][target] = {"rho": rho, "n": n}

    u = np.asarray([r[uncertainty_key] for r in rows], dtype=np.float64)
    if len(u) >= 3 and np.isfinite(u).all():
        q1, q2 = np.quantile(u, [1.0 / 3.0, 2.0 / 3.0])
        groups = {
            "low": [r for r in rows if r[uncertainty_key] <= q1],
            "medium": [r for r in rows if q1 < r[uncertainty_key] <= q2],
            "high": [r for r in rows if r[uncertainty_key] > q2],
        }
        out["tertiles"] = {
            name: {
                "n": len(g),
                "u_median": float(np.median([r[uncertainty_key] for r in g])) if g else float("nan"),
                "final_t_median_m": float(np.median([r["slam_final_rel_error_t_m"] for r in g])) if g else float("nan"),
                "final_r_median_rad": float(np.median([r["slam_final_rel_error_r_rad"] for r in g])) if g else float("nan"),
            }
            for name, g in groups.items()
        }
        out["tertile_monotonic_final_t"] = bool(
            out["tertiles"]["low"]["final_t_median_m"]
            <= out["tertiles"]["medium"]["final_t_median_m"]
            <= out["tertiles"]["high"]["final_t_median_m"]
        )
        out["tertile_monotonic_final_r"] = bool(
            out["tertiles"]["low"]["final_r_median_rad"]
            <= out["tertiles"]["medium"]["final_r_median_rad"]
            <= out["tertiles"]["high"]["final_r_median_rad"]
        )

        q90 = float(np.quantile(u, 0.90))
        hi = [r for r in rows if r[uncertainty_key] > q90]
        normal = [r for r in rows if r[uncertainty_key] <= q90]
        hi_t = float(np.median([r["slam_final_rel_error_t_m"] for r in hi]))
        no_t = float(np.median([r["slam_final_rel_error_t_m"] for r in normal]))
        hi_r = float(np.median([r["slam_final_rel_error_r_rad"] for r in hi]))
        no_r = float(np.median([r["slam_final_rel_error_r_rad"] for r in normal]))
        out["q90_tail"] = {
            "threshold_u": q90,
            "n_high": len(hi), "n_normal": len(normal),
            "final_t_high_median_m": hi_t,
            "final_t_normal_median_m": no_t,
            "final_t_high_over_normal": hi_t / no_t if no_t > 0 else float("nan"),
            "final_r_high_median_rad": hi_r,
            "final_r_normal_median_rad": no_r,
            "final_r_high_over_normal": hi_r / no_r if no_r > 0 else float("nan"),
        }
    return out


def control_correlations(rows):
    controls = (
        "sigma_t", "sigma_r", "num_pixels", "log10_condition",
        "valid_extent", "fb_error_median_px", "maha_median",
        "motion_scale_joint",
    )
    targets = ("slam_final_rel_error_t_m", "slam_final_rel_error_r_rad")
    out = {}
    for key in controls:
        out[key] = {}
        for target in targets:
            rho, n = spearman([r.get(key) for r in rows], [r[target] for r in rows])
            out[key][target] = {"rho": rho, "n": n}
    return out


def build_rows(run_dir, signal_file, fold):
    run_dir = Path(run_dir)
    m1_dir = run_dir / "m1_pose_uncertainty"
    m2_dir = run_dir / "m2a_pose_uncertainty"
    m1 = load_by_frame(m1_dir)
    m2 = load_by_frame(m2_dir)
    common = sorted(set(m1) & set(m2))
    if len(common) < 100:
        raise RuntimeError(
            f"Only {len(common)} common M1/M2-A frames under {run_dir}; "
            "expected dense diagnostics from a corrected baseline/shadow run."
        )

    signal = M1MappingSignal(signal_file, fold=fold)
    rows = []
    sanity = {
        "max_rotation_det_abs_error": 0.0,
        "max_homogeneous_last_row_abs_error": 0.0,
        "max_prior_reconstruction_fro_error": 0.0,
        "shadow_false_frames": [],
        "missing_cluster_block_frames": [],
    }

    for frame in common:
        a, b = m1[frame], m2[frame]
        if not bool(a.get("shadow_mode", False)):
            sanity["shadow_false_frames"].append(frame)

        clusters = a.get("P_xi_clusters", {})
        P_raw = clusters.get(signal.block_size)
        if P_raw is None:
            P_raw = clusters.get(str(signal.block_size))
        if P_raw is None:
            sanity["missing_cluster_block_frames"].append(frame)
            continue
        sig = signal.evaluate(P_raw)

        T_raw = as_T(a["T_rel_raw"], "T_rel_raw")
        T_applied = as_T(a["T_rel_applied"], "T_rel_applied")
        T_gt = as_T(a["T_rel_gt"], "T_rel_gt")
        T_prior = as_T(b["T_motion_prior"], "T_motion_prior")
        T_final = as_T(b["T_final"], "T_final")

        # Exact algebra under the saved Flow4DGS right-composed update:
        # prior = prev_used @ applied.
        T_prev_used = T_prior @ torch.linalg.inv(T_applied)
        T_rel_final = torch.linalg.inv(T_prev_used) @ T_final
        T_prior_reconstructed = T_prev_used @ T_applied

        raw_t, raw_r = se3_error(T_raw, T_gt)
        app_t, app_r = se3_error(T_applied, T_gt)
        fin_t, fin_r = se3_error(T_rel_final, T_gt)
        corr_t, corr_r = se3_error(T_rel_final, T_applied)

        Ts = (T_raw, T_applied, T_gt, T_prior, T_final, T_prev_used, T_rel_final)
        sanity["max_rotation_det_abs_error"] = max(
            sanity["max_rotation_det_abs_error"], *(rot_det_error(T) for T in Ts)
        )
        sanity["max_homogeneous_last_row_abs_error"] = max(
            sanity["max_homogeneous_last_row_abs_error"], *(last_row_error(T) for T in Ts)
        )
        sanity["max_prior_reconstruction_fro_error"] = max(
            sanity["max_prior_reconstruction_fro_error"],
            float(torch.linalg.norm(T_prior_reconstructed - T_prior)),
        )

        condition = float(torch.as_tensor(a.get("condition", float("nan"))).reshape(()))
        row = {
            "frame": frame,
            "u": sig["u"], "sigma_t": sig["sigma_t"], "sigma_r": sig["sigma_r"],
            "m1_raw_error_t_m": raw_t, "m1_raw_error_r_rad": raw_r,
            "m1_applied_error_t_m": app_t, "m1_applied_error_r_rad": app_r,
            "slam_final_rel_error_t_m": fin_t, "slam_final_rel_error_r_rad": fin_r,
            "tracking_change_from_applied_t_m": corr_t,
            "tracking_change_from_applied_r_rad": corr_r,
            "num_pixels": int(a.get("num_pixels", 0)),
            "log10_condition": math.log10(condition) if condition > 0 and finite(condition) else float("nan"),
            "valid_extent": float(a.get("valid_extent", float("nan"))),
            "fb_error_median_px": float(torch.as_tensor(a.get("fb_error_median_px", float("nan"))).reshape(())),
            "maha_median": float(torch.as_tensor(a.get("maha_median", float("nan"))).reshape(())),
            "motion_scale_joint": float(torch.as_tensor(a.get("motion_scale_joint", float("nan"))).reshape(())),
        }
        rows.append(row)

    if len(rows) < 100:
        raise RuntimeError(f"Only {len(rows)} usable joined rows after covariance checks")
    return rows, sanity, signal


def write_csv(path, rows):
    keys = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def print_summary(report):
    s = report["full_sequence"]
    print("=" * 92)
    print("M1 RELATIVE-MOTION RELIABILITY AUDIT — baseline final tracking increment")
    print("=" * 92)
    print(f"fold={report['fold']} frames={s['n']} block={report['m1_block_size']}")
    print("Primary: Spearman calibrated u vs FINAL baseline relative-pose error")
    for key in ("slam_final_rel_error_t_m", "slam_final_rel_error_r_rad"):
        x = s["spearman"][key]
        print(f"  {key:34s} rho={x['rho']:+.4f} n={x['n']}")
    print("Positive control: u vs M1 RAW relative-motion error")
    for key in ("m1_raw_error_t_m", "m1_raw_error_r_rad"):
        x = s["spearman"][key]
        print(f"  {key:34s} rho={x['rho']:+.4f} n={x['n']}")

    print("FINAL error by uncertainty tertile:")
    for name in ("low", "medium", "high"):
        x = s["tertiles"][name]
        print(
            f"  {name:6s} n={x['n']:3d} u_med={x['u_median']:.4g} "
            f"t={x['final_t_median_m']:.6g} m r={x['final_r_median_rad']:.6g} rad"
        )
    print(
        "  monotonic t/r: "
        f"{s['tertile_monotonic_final_t']} / {s['tertile_monotonic_final_r']}"
    )
    q = s["q90_tail"]
    print(
        f"q90 tail u>{q['threshold_u']:.4g}: high/normal final error "
        f"t={q['final_t_high_over_normal']:.3f}x "
        f"r={q['final_r_high_over_normal']:.3f}x"
    )

    if "around_dystart_pm30" in report:
        d = report["around_dystart_pm30"]
        print(f"dystart={report['dystart']} +/-30 frames n={d['n']}")
        for key in ("slam_final_rel_error_t_m", "slam_final_rel_error_r_rad"):
            x = d["spearman"][key]
            print(f"  {key:34s} rho={x['rho']:+.4f} n={x['n']}")

    z = report["sanity"]
    print("Sanity:")
    print(f"  max |det(R)-1|             {z['max_rotation_det_abs_error']:.3e}")
    print(f"  max homogeneous row error  {z['max_homogeneous_last_row_abs_error']:.3e}")
    print(f"  max prior reconstruction   {z['max_prior_reconstruction_fro_error']:.3e}")
    print(f"  shadow=false frames         {len(z['shadow_false_frames'])}")
    print(f"  missing cluster frames      {len(z['missing_cluster_block_frames'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--signal-file", type=Path, default=Path("results/m1_mapping_signal_bonn_loso.json"))
    ap.add_argument("--fold", required=True, choices=["placing_box", "placing_box2", "placing_box3"])
    ap.add_argument("--dystart", type=int, default=None)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    rows, sanity, signal = build_rows(args.run_dir, args.signal_file, args.fold)
    report = {
        "method": "m1_relative_pose_reliability_audit_v1",
        "run_dir": str(args.run_dir),
        "signal_file": str(args.signal_file),
        "fold": args.fold,
        "m1_block_size": signal.block_size,
        "reference_sigma_t_m": signal.ref_t,
        "reference_sigma_r_rad": signal.ref_r,
        "guardrail": (
            "Diagnostic only. Primary target is the final frontend tracking increment in the same "
            "right-composed convention used by M1. No trajectory alignment is applied. Positive "
            "association is required within each sequence before any pose intervention is considered."
        ),
        "sanity": sanity,
        "full_sequence": metric_summary(rows),
        "simple_signal_controls": control_correlations(rows),
        "error_distributions": {
            "m1_raw_t_m": qstats(r["m1_raw_error_t_m"] for r in rows),
            "m1_raw_r_rad": qstats(r["m1_raw_error_r_rad"] for r in rows),
            "final_t_m": qstats(r["slam_final_rel_error_t_m"] for r in rows),
            "final_r_rad": qstats(r["slam_final_rel_error_r_rad"] for r in rows),
            "tracking_change_t_m": qstats(r["tracking_change_from_applied_t_m"] for r in rows),
            "tracking_change_r_rad": qstats(r["tracking_change_from_applied_r_rad"] for r in rows),
        },
    }

    if args.dystart is not None:
        local = [r for r in rows if abs(r["frame"] - args.dystart) <= 30]
        report["dystart"] = args.dystart
        report["around_dystart_pm30"] = metric_summary(local) if len(local) >= 10 else {"n": len(local)}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        json.dump(report, f, indent=2, allow_nan=True)
    csv_path = args.output.with_suffix(".csv")
    write_csv(csv_path, rows)
    print_summary(report)
    print(f"Saved {args.output}")
    print(f"Saved {csv_path}")


if __name__ == "__main__":
    main()
