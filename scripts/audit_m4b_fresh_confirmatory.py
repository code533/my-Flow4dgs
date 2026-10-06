#!/usr/bin/env python3
"""M4-B strict fresh-sequence confirmatory validation.

Fit coefficients only on the development table (box1/box2/box3).
Apply the frozen models to fresh sequences without refitting.
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np


TARGETS = (
    "slam_final_rel_error_t_m",
    "slam_final_rel_error_r_rad",
)


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


def pct_rank(values):
    x = np.asarray(values, dtype=np.float64)
    return (rankdata(x) - 0.5) / float(len(x))


def spearman(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def ridge_fit(X, y, lam):
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    A = np.column_stack([np.ones(len(X)), X])
    P = np.eye(A.shape[1], dtype=np.float64) * float(lam)
    P[0, 0] = 0.0
    return np.linalg.solve(A.T @ A + P, A.T @ y)


def ridge_predict(X, beta):
    A = np.column_stack([np.ones(len(X)), np.asarray(X, dtype=np.float64)])
    return A @ beta


def load_table(path):
    by_seq = {}
    with Path(path).open(newline="") as f:
        for r in csv.DictReader(f):
            row = {"sequence": r["sequence"], "frame": int(float(r["frame"]))}
            for k, v in r.items():
                if k in ("sequence", "frame"):
                    continue
                row[k] = float(v)
            by_seq.setdefault(row["sequence"], []).append(row)
    if not by_seq:
        raise RuntimeError(f"Empty table: {path}")
    return by_seq


def fit_dev(dev, target, lam):
    X0, X1, y = [], [], []
    for name in sorted(dev):
        rr = dev[name]
        fb = pct_rank([r["fb_error_median_px"] for r in rr])
        mt = pct_rank([r["applied_translation_norm_m"] for r in rr])
        mr = pct_rank([r["applied_rotation_angle_rad"] for r in rr])
        fl = pct_rank([r["direct_flow_median_px"] for r in rr])
        ee = pct_rank([r[target] for r in rr])

        X0.extend(np.column_stack([fb, mt, mr]).tolist())
        X1.extend(np.column_stack([fb, mt, mr, fl]).tolist())
        y.extend(ee.tolist())

    return ridge_fit(X0, y, lam), ridge_fit(X1, y, lam)


def evaluate_sequence(rows, target, beta0, beta1):
    fb = pct_rank([r["fb_error_median_px"] for r in rows])
    mt = pct_rank([r["applied_translation_norm_m"] for r in rows])
    mr = pct_rank([r["applied_rotation_angle_rad"] for r in rows])
    fl = pct_rank([r["direct_flow_median_px"] for r in rows])
    ee = pct_rank([r[target] for r in rows])

    p0 = ridge_predict(np.column_stack([fb, mt, mr]), beta0)
    p1 = ridge_predict(np.column_stack([fb, mt, mr, fl]), beta1)

    rho0 = spearman(p0, ee)
    rho1 = spearman(p1, ee)
    return {
        "rho_fb_motion": rho0,
        "rho_fb_motion_flow": rho1,
        "delta_rho_flow": rho1 - rho0,
    }


def moving_block_indices(n, block_len, rng):
    block_len = max(1, min(int(block_len), n))
    max_start = n - block_len
    out = []
    while len(out) < n:
        s = int(rng.integers(0, max_start + 1)) if max_start > 0 else 0
        out.extend(range(s, s + block_len))
    return np.asarray(out[:n], dtype=np.int64)


def bootstrap_delta(rows, target, beta0, beta1, block_len, n_boot, seed):
    point = evaluate_sequence(rows, target, beta0, beta1)["delta_rho_flow"]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = moving_block_indices(len(rows), block_len, rng)
        sample = [rows[i] for i in idx]
        d = evaluate_sequence(sample, target, beta0, beta1)["delta_rho_flow"]
        if np.isfinite(d):
            vals.append(d)
    if not vals:
        return {"delta": point, "ci95": [float("nan"), float("nan")], "n_boot": 0}
    return {
        "delta": point,
        "ci95": [
            float(np.quantile(vals, 0.025)),
            float(np.quantile(vals, 0.975)),
        ],
        "n_boot": len(vals),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--development", type=Path, required=True)
    ap.add_argument("--fresh", type=Path, required=True)
    ap.add_argument("--ridge-lambda", type=float, default=1e-3)
    ap.add_argument("--block-len", type=int, default=20)
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    dev = load_table(args.development)
    fresh = load_table(args.fresh)

    report = {
        "method": "m4b_fresh_confirmatory_v1",
        "development_sequences": sorted(dev),
        "fresh_sequences": sorted(fresh),
        "ridge_lambda": args.ridge_lambda,
        "block_len": args.block_len,
        "bootstrap": args.bootstrap,
        "seed": args.seed,
        "targets": {},
    }

    print("=" * 98)
    print("M4-B FRESH-SEQUENCE CONFIRMATORY VALIDATION")
    print("=" * 98)
    print("Development fit:", "+".join(sorted(dev)))
    print("Fresh evaluation:", "+".join(sorted(fresh)))

    for target in TARGETS:
        beta0, beta1 = fit_dev(dev, target, args.ridge_lambda)
        per = {}
        deltas = []

        print(f"\n{target}")
        for name in sorted(fresh):
            x = evaluate_sequence(fresh[name], target, beta0, beta1)
            b = bootstrap_delta(
                fresh[name], target, beta0, beta1,
                args.block_len, args.bootstrap, args.seed
            )
            x["bootstrap"] = b
            per[name] = x
            deltas.append(x["delta_rho_flow"])
            print(
                f"  {name:16s} "
                f"M0={x['rho_fb_motion']:+.4f} "
                f"M1={x['rho_fb_motion_flow']:+.4f} "
                f"delta={x['delta_rho_flow']:+.4f} "
                f"CI95=[{b['ci95'][0]:+.4f},{b['ci95'][1]:+.4f}]"
            )

        macro = float(np.nanmean(deltas))
        positive = int(np.sum(np.asarray(deltas) > 0))
        report["targets"][target] = {
            "per_sequence": per,
            "macro_delta": macro,
            "positive_sequences": positive,
            "total_sequences": len(deltas),
        }

        print(
            f"  macro delta={macro:+.4f} "
            f"positive={positive}/{len(deltas)}"
        )

    t = report["targets"]["slam_final_rel_error_t_m"]
    r = report["targets"]["slam_final_rel_error_r_rad"]

    pass_t = t["macro_delta"] >= 0.05 and t["positive_sequences"] >= 2
    pass_r = r["macro_delta"] >= 0.05 and r["positive_sequences"] >= 2
    no_large_t_degrade = t["macro_delta"] >= -0.05
    no_large_r_degrade = r["macro_delta"] >= -0.05

    passed = (
        (pass_t and no_large_r_degrade)
        or (pass_r and no_large_t_degrade)
    )
    report["gate"] = {
        "translation_pass": bool(pass_t),
        "rotation_pass": bool(pass_r),
        "no_large_translation_degradation": bool(no_large_t_degrade),
        "no_large_rotation_degradation": bool(no_large_r_degrade),
        "overall_pass": bool(passed),
    }

    print("\nFrozen gate:")
    print(
        f"  translation pass={pass_t} "
        f"(macro={t['macro_delta']:+.4f}, "
        f"positive={t['positive_sequences']}/3)"
    )
    print(
        f"  rotation pass={pass_r} "
        f"(macro={r['macro_delta']:+.4f}, "
        f"positive={r['positive_sequences']}/3)"
    )
    print(f"  OVERALL PASS={passed}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=True))
    print(f"\nSaved {args.output}")


if __name__ == "__main__":
    main()
