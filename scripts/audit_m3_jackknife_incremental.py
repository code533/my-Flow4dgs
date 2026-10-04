#!/usr/bin/env python3
"""Audit incremental reliability value of M3-A jackknife instability beyond FB.

Inputs pair an M3 diagnostic directory with the CSV produced by
scripts/audit_m1_relative_pose_reliability.py.

Primary pre-specified signals:
  translation target <- sigma_jk_translation
  rotation target    <- sigma_jk_rotation

Primary questions:
  1) within-sequence partial Spearman rho(JK, error | FB)
  2) LOSO incremental rank-prediction value:
       M_FB    : error-rank ~ FB-rank
       M_FB+JK : error-rank ~ FB-rank + JK-rank

No SLAM state is modified and no threshold is selected.
"""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import torch


TARGETS = {
    "slam_final_rel_error_t_m": "sigma_jk_translation",
    "slam_final_rel_error_r_rad": "sigma_jk_rotation",
}


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


def percentile_rank(values):
    x = np.asarray(values, dtype=np.float64)
    return (rankdata(x) - 0.5) / float(len(x))


def corr(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    good = np.isfinite(x) & np.isfinite(y)
    if int(good.sum()) < 3:
        return float("nan")
    return corr(rankdata(x[good]), rankdata(y[good]))


def residualize(y, x):
    A = np.column_stack([np.ones(len(x), dtype=np.float64), x])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def partial_spearman(signal, error, fb):
    signal = np.asarray(signal, dtype=np.float64)
    error = np.asarray(error, dtype=np.float64)
    fb = np.asarray(fb, dtype=np.float64)
    good = np.isfinite(signal) & np.isfinite(error) & np.isfinite(fb)
    signal, error, fb = signal[good], error[good], fb[good]
    if len(signal) < 4:
        return float("nan")
    rs, re, rf = rankdata(signal), rankdata(error), rankdata(fb)
    return corr(residualize(rs, rf), residualize(re, rf))


def moving_block_indices(n, block_len, rng):
    block_len = max(1, min(int(block_len), n))
    max_start = n - block_len
    out = []
    while len(out) < n:
        start = int(rng.integers(0, max_start + 1)) if max_start > 0 else 0
        out.extend(range(start, start + block_len))
    return np.asarray(out[:n], dtype=np.int64)


def bootstrap_partial(signal, error, fb, block_len, n_boot, seed):
    point = partial_spearman(signal, error, fb)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = moving_block_indices(len(signal), block_len, rng)
        v = partial_spearman(signal[idx], error[idx], fb[idx])
        if finite(v):
            vals.append(v)
    if not vals:
        return {"rho": point, "ci95": [float("nan"), float("nan")], "n_boot": 0}
    return {
        "rho": point,
        "ci95": [
            float(np.quantile(vals, 0.025)),
            float(np.quantile(vals, 0.975)),
        ],
        "n_boot": len(vals),
    }


def ridge_fit(X, y, lam):
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    A = np.column_stack([np.ones(len(X), dtype=np.float64), X])
    penalty = np.eye(A.shape[1], dtype=np.float64) * float(lam)
    penalty[0, 0] = 0.0
    return np.linalg.solve(A.T @ A + penalty, A.T @ y)


def ridge_predict(X, beta):
    A = np.column_stack(
        [np.ones(len(X), dtype=np.float64), np.asarray(X, dtype=np.float64)]
    )
    return A @ beta


def load_m3(directory):
    out = {}
    directory = Path(directory)
    files = sorted(directory.glob("*.pt"))
    if not files:
        raise FileNotFoundError(f"No M3 jackknife .pt files in {directory}")
    for path in files:
        try:
            d = torch.load(path, map_location="cpu", weights_only=False)
        except TypeError:
            d = torch.load(path, map_location="cpu")
        if d.get("method") != "m3_pose_delete_block_jackknife_v1":
            continue
        frame = int(d.get("frame", int(path.stem)))
        if not bool(d.get("valid", False)):
            continue
        out[frame] = {
            "sigma_jk_translation": float(d["sigma_jk_translation"]),
            "sigma_jk_rotation": float(d["sigma_jk_rotation"]),
            "max_jk_translation": float(d["max_leaveout_delta_translation"]),
            "max_jk_rotation": float(d["max_leaveout_delta_rotation"]),
            "num_valid_blocks": int(d["num_valid_blocks"]),
        }
    if not out:
        raise RuntimeError(f"No valid M3 jackknife payloads in {directory}")
    return out


def load_csv(path):
    out = {}
    with Path(path).open(newline="") as f:
        for row in csv.DictReader(f):
            needed = [
                "frame",
                "fb_error_median_px",
                "slam_final_rel_error_t_m",
                "slam_final_rel_error_r_rad",
            ]
            if not all(k in row for k in needed):
                missing = [k for k in needed if k not in row]
                raise KeyError(f"{path}: missing columns {missing}")
            vals = {k: float(row[k]) for k in needed}
            if not all(finite(vals[k]) for k in needed):
                continue
            out[int(float(row["frame"]))] = vals
    if not out:
        raise RuntimeError(f"No usable rows in {path}")
    return out


def parse_sequence(value):
    if "=" not in value:
        raise ValueError(f"Expected NAME=M3_DIR,CSV, got {value!r}")
    name, rest = value.split("=", 1)
    parts = rest.split(",")
    if len(parts) != 2:
        raise ValueError(f"Expected NAME=M3_DIR,CSV, got {value!r}")
    return name.strip(), Path(parts[0]).expanduser(), Path(parts[1]).expanduser()


def join_sequence(name, m3_dir, csv_path):
    m3 = load_m3(m3_dir)
    base = load_csv(csv_path)
    frames = sorted(set(m3) & set(base))
    rows = []
    for frame in frames:
        r = {"sequence": name, "frame": frame}
        r.update(base[frame])
        r.update(m3[frame])
        rows.append(r)
    if len(rows) < 20:
        raise RuntimeError(
            f"{name}: only {len(rows)} joined frames. "
            "Expand m3_jackknife_frame_range for a stable audit."
        )
    return rows


def summarize_sequence(rows, block_len, n_boot, seed):
    out = {"n": len(rows), "targets": {}}
    fb = np.asarray([r["fb_error_median_px"] for r in rows], dtype=np.float64)
    for target, signal_key in TARGETS.items():
        signal = np.asarray([r[signal_key] for r in rows], dtype=np.float64)
        error = np.asarray([r[target] for r in rows], dtype=np.float64)
        out["targets"][target] = {
            "signal": signal_key,
            "raw_signal_rho": spearman(signal, error),
            "raw_fb_rho": spearman(fb, error),
            "partial_after_fb": bootstrap_partial(
                signal, error, fb, block_len, n_boot, seed
            ),
        }
    return out


def loso(sequences, lam):
    names = list(sequences)
    out = {}
    for held in names:
        train_names = [n for n in names if n != held]
        test = sequences[held]
        fold = {"train": train_names, "targets": {}}

        for target, signal_key in TARGETS.items():
            X0_train, X1_train, y_train = [], [], []
            for name in train_names:
                rows = sequences[name]
                fb = percentile_rank([r["fb_error_median_px"] for r in rows])
                sig = percentile_rank([r[signal_key] for r in rows])
                err = percentile_rank([r[target] for r in rows])
                X0_train.extend(fb[:, None].tolist())
                X1_train.extend(np.column_stack([fb, sig]).tolist())
                y_train.extend(err.tolist())

            beta0 = ridge_fit(X0_train, y_train, lam)
            beta1 = ridge_fit(X1_train, y_train, lam)

            fb_t = percentile_rank([r["fb_error_median_px"] for r in test])
            sig_t = percentile_rank([r[signal_key] for r in test])
            err_t = percentile_rank([r[target] for r in test])

            pred0 = ridge_predict(fb_t[:, None], beta0)
            pred1 = ridge_predict(np.column_stack([fb_t, sig_t]), beta1)
            rho0 = spearman(pred0, err_t)
            rho1 = spearman(pred1, err_t)
            fold["targets"][target] = {
                "rho_fb": rho0,
                "rho_fb_plus_jk": rho1,
                "delta_rho": rho1 - rho0,
            }

        out[held] = fold
    return out


def macro_summary(per_sequence, loso_report):
    out = {}
    for target in TARGETS:
        partials = [
            per_sequence[n]["targets"][target]["partial_after_fb"]["rho"]
            for n in per_sequence
        ]
        deltas = [
            loso_report[n]["targets"][target]["delta_rho"]
            for n in loso_report
        ]
        out[target] = {
            "partial_mean": float(np.nanmean(partials)),
            "partial_positive": int(np.sum(np.asarray(partials) > 0)),
            "partial_total": len(partials),
            "loso_delta_mean": float(np.nanmean(deltas)),
            "loso_delta_positive": int(np.sum(np.asarray(deltas) > 0)),
            "loso_delta_total": len(deltas),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence", nargs="+", required=True)
    ap.add_argument("--block-len", type=int, default=20)
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ridge-lambda", type=float, default=1e-3)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    sequences = {}
    specs = {}
    for value in args.sequence:
        name, m3_dir, csv_path = parse_sequence(value)
        if name in sequences:
            raise ValueError(f"Duplicate sequence name {name!r}")
        sequences[name] = join_sequence(name, m3_dir, csv_path)
        specs[name] = {"m3_dir": str(m3_dir), "csv": str(csv_path)}

    per_sequence = {
        name: summarize_sequence(
            rows, args.block_len, args.bootstrap, args.seed
        )
        for name, rows in sequences.items()
    }
    loso_report = loso(sequences, args.ridge_lambda)
    macro = macro_summary(per_sequence, loso_report)

    report = {
        "method": "m3_jackknife_incremental_value_v1",
        "primary_signals": TARGETS,
        "sequence_inputs": specs,
        "block_len": args.block_len,
        "bootstrap": args.bootstrap,
        "seed": args.seed,
        "ridge_lambda": args.ridge_lambda,
        "per_sequence": per_sequence,
        "loso": loso_report,
        "macro": macro,
        "gate_note": (
            "M3-A should not be connected to runtime SLAM behavior unless "
            "held-out delta-rho is materially positive and consistent. "
            "A practical research gate of roughly +0.03 to +0.05 macro "
            "delta-rho is pre-specified in docs/m3_source_discovery.md."
        ),
    }

    print("=" * 94)
    print("M3-A JACKKNIFE INCREMENTAL-VALUE AUDIT — conditioned on FB consistency")
    print("=" * 94)
    for name, summary in per_sequence.items():
        print(f"\n{name}: n={summary['n']}")
        for target in TARGETS:
            x = summary["targets"][target]
            p = x["partial_after_fb"]
            print(
                f"  {target:30s} "
                f"JK={x['raw_signal_rho']:+.4f} FB={x['raw_fb_rho']:+.4f} "
                f"partial={p['rho']:+.4f} "
                f"CI95=[{p['ci95'][0]:+.4f},{p['ci95'][1]:+.4f}]"
            )

    print("\nLOSO:")
    for held, fold in loso_report.items():
        print(f"  held out {held}; train={'+'.join(fold['train'])}")
        for target in TARGETS:
            x = fold["targets"][target]
            print(
                f"    {target:28s} FB={x['rho_fb']:+.4f} "
                f"FB+JK={x['rho_fb_plus_jk']:+.4f} "
                f"delta={x['delta_rho']:+.4f}"
            )

    print("\nMacro directional summary")
    for target, x in macro.items():
        print(
            f"  {target:30s} "
            f"partial mean={x['partial_mean']:+.4f} "
            f"positive={x['partial_positive']}/{x['partial_total']}; "
            f"LOSO delta mean={x['loso_delta_mean']:+.4f} "
            f"positive={x['loso_delta_positive']}/{x['loso_delta_total']}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=True))
    print(f"\nSaved {args.output}")


if __name__ == "__main__":
    main()
