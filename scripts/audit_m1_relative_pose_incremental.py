#!/usr/bin/env python3
"""Audit whether calibrated M1 uncertainty adds relative-pose reliability information
beyond the simpler forward/backward (FB) flow-consistency signal.

Diagnostic-only.  This script consumes CSV files produced by
scripts/audit_m1_relative_pose_reliability.py and never modifies SLAM state.

Two complementary, pre-specified tests are reported:

1) Within-sequence partial Spearman
       rho(u, e | FB)
   implemented as Pearson correlation between rank residuals after separately
   regressing rank(u) and rank(e) on [1, rank(FB)].  This asks whether uncertainty
   retains monotonic association with final relative-pose error after controlling
   for FB consistency.

2) Leave-one-sequence-out (LOSO) rank prediction
       M_FB    : error-rank ~ FB-rank
       M_FB+U  : error-rank ~ FB-rank + u-rank
   Each feature is converted to a percentile rank within its sequence.  Model
   coefficients are fitted ONLY on the other sequences and evaluated on the held-
   out sequence.  The primary predictive metric is Spearman(prediction, error),
   and the reported incremental value is delta-rho = rho(FB+U) - rho(FB).

No hyperparameter is selected from held-out results.  Ridge lambda, block length,
and bootstrap seed are fixed command-line settings (defaults: 1e-3, 20, 1000
replicates, seed 0).  Moving-block bootstrap intervals are descriptive and account
for short-range temporal dependence better than an iid bootstrap; they are not
claimed as exact hypothesis tests for the full SLAM process.
"""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


TARGETS = (
    "slam_final_rel_error_t_m",
    "slam_final_rel_error_r_rad",
)


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
    if len(x) == 0:
        return x
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
    y = np.asarray(y, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)
    A = np.column_stack([np.ones(len(x), dtype=np.float64), x])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def partial_spearman(u, error, fb):
    u = np.asarray(u, dtype=np.float64)
    error = np.asarray(error, dtype=np.float64)
    fb = np.asarray(fb, dtype=np.float64)
    good = np.isfinite(u) & np.isfinite(error) & np.isfinite(fb)
    u, error, fb = u[good], error[good], fb[good]
    if len(u) < 4:
        return float("nan")
    ru, re, rf = rankdata(u), rankdata(error), rankdata(fb)
    return corr(residualize(ru, rf), residualize(re, rf))


def load_csv(path, name):
    path = Path(path)
    rows = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            needed = ["frame", "u", "fb_error_median_px", *TARGETS]
            if not all(k in row for k in needed):
                missing = [k for k in needed if k not in row]
                raise KeyError(f"{path}: missing columns {missing}")
            vals = {k: float(row[k]) for k in needed}
            if not all(finite(vals[k]) for k in needed):
                continue
            vals["frame"] = int(float(row["frame"]))
            vals["sequence"] = name
            rows.append(vals)
    rows.sort(key=lambda r: r["frame"])
    if len(rows) < 100:
        raise RuntimeError(f"{path}: only {len(rows)} usable rows; expected >=100")
    return rows


def arrays(rows, target):
    return (
        np.asarray([r["u"] for r in rows], dtype=np.float64),
        np.asarray([r["fb_error_median_px"] for r in rows], dtype=np.float64),
        np.asarray([r[target] for r in rows], dtype=np.float64),
    )


def moving_block_indices(n, block_len, rng):
    block_len = max(1, min(int(block_len), n))
    max_start = n - block_len
    out = []
    while len(out) < n:
        start = int(rng.integers(0, max_start + 1)) if max_start > 0 else 0
        out.extend(range(start, start + block_len))
    return np.asarray(out[:n], dtype=np.int64)


def bootstrap_partial(u, error, fb, block_len, n_boot, seed):
    point = partial_spearman(u, error, fb)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = moving_block_indices(len(u), block_len, rng)
        v = partial_spearman(u[idx], error[idx], fb[idx])
        if finite(v):
            vals.append(v)
    if not vals:
        return {"rho": point, "ci95": [float("nan"), float("nan")], "n_boot": 0}
    return {
        "rho": point,
        "ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))],
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
    X = np.asarray(X, dtype=np.float64)
    A = np.column_stack([np.ones(len(X), dtype=np.float64), X])
    return A @ beta


def rank_features(rows, target):
    u, fb, error = arrays(rows, target)
    return percentile_rank(u), percentile_rank(fb), percentile_rank(error), error


def loso_fold(train_sets, test_rows, target, lam):
    train_fb, train_u, train_y = [], [], []
    for rows in train_sets:
        ur, fbr, yr, _ = rank_features(rows, target)
        train_fb.append(fbr)
        train_u.append(ur)
        train_y.append(yr)
    train_fb = np.concatenate(train_fb)
    train_u = np.concatenate(train_u)
    train_y = np.concatenate(train_y)

    beta_fb = ridge_fit(train_fb[:, None], train_y, lam)
    beta_fbu = ridge_fit(np.column_stack([train_fb, train_u]), train_y, lam)

    test_u, test_fb, test_y_rank, test_error = rank_features(test_rows, target)
    pred_fb = ridge_predict(test_fb[:, None], beta_fb)
    pred_fbu = ridge_predict(np.column_stack([test_fb, test_u]), beta_fbu)

    rho_fb = spearman(pred_fb, test_error)
    rho_fbu = spearman(pred_fbu, test_error)
    return {
        "rho_fb": rho_fb,
        "rho_fb_plus_u": rho_fbu,
        "delta_rho": rho_fbu - rho_fb,
        "rank_mae_fb": float(np.mean(np.abs(pred_fb - test_y_rank))),
        "rank_mae_fb_plus_u": float(np.mean(np.abs(pred_fbu - test_y_rank))),
        "delta_rank_mae": float(np.mean(np.abs(pred_fbu - test_y_rank)) - np.mean(np.abs(pred_fb - test_y_rank))),
        "beta_fb": beta_fb.tolist(),
        "beta_fb_plus_u": beta_fbu.tolist(),
        "pred_fb": pred_fb,
        "pred_fbu": pred_fbu,
        "test_error": test_error,
    }


def bootstrap_loso_delta(fold, block_len, n_boot, seed):
    point = float(fold["delta_rho"])
    pred_fb = fold["pred_fb"]
    pred_fbu = fold["pred_fbu"]
    error = fold["test_error"]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = moving_block_indices(len(error), block_len, rng)
        a = spearman(pred_fb[idx], error[idx])
        b = spearman(pred_fbu[idx], error[idx])
        if finite(a) and finite(b):
            vals.append(b - a)
    if not vals:
        return {"delta_rho": point, "ci95": [float("nan"), float("nan")], "n_boot": 0}
    return {
        "delta_rho": point,
        "ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))],
        "n_boot": len(vals),
    }


def clean_fold_for_json(fold):
    return {k: v for k, v in fold.items() if k not in {"pred_fb", "pred_fbu", "test_error"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--box1", default="results/m1_relative_reliability_box1.csv")
    ap.add_argument("--box2", default="results/m1_relative_reliability_box2.csv")
    ap.add_argument("--box3", default="results/m1_relative_reliability_box3.csv")
    ap.add_argument("--ridge-lambda", type=float, default=1e-3)
    ap.add_argument("--block-len", type=int, default=20)
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output", default="results/m1_relative_reliability_incremental.json")
    args = ap.parse_args()

    paths = {"box1": args.box1, "box2": args.box2, "box3": args.box3}
    seqs = {name: load_csv(path, name) for name, path in paths.items()}

    report = {
        "inputs": paths,
        "settings": {
            "ridge_lambda": args.ridge_lambda,
            "block_len": args.block_len,
            "bootstrap": args.bootstrap,
            "seed": args.seed,
            "feature_normalization": "within-sequence percentile ranks",
            "target_for_training": "within-sequence final-error percentile rank",
        },
        "within_sequence": {},
        "loso": {},
    }

    print("=" * 96)
    print("M1 RELATIVE-POSE INCREMENTAL-VALUE AUDIT — conditioned on FB consistency")
    print("=" * 96)
    print("Primary questions: partial Spearman rho(u,error | FB), and LOSO delta-rho(FB+U - FB)")
    print(f"block bootstrap: L={args.block_len}, B={args.bootstrap}, seed={args.seed}; ridge lambda={args.ridge_lambda:g}")

    for si, (name, rows) in enumerate(seqs.items()):
        report["within_sequence"][name] = {"n": len(rows), "targets": {}}
        print(f"\n{name}: n={len(rows)}")
        print("  within-sequence partial Spearman after controlling FB rank")
        for ti, target in enumerate(TARGETS):
            u, fb, error = arrays(rows, target)
            raw_u = spearman(u, error)
            raw_fb = spearman(fb, error)
            p = bootstrap_partial(
                u, error, fb, args.block_len, args.bootstrap,
                args.seed + 1000 * si + 100 * ti,
            )
            report["within_sequence"][name]["targets"][target] = {
                "rho_u_error": raw_u,
                "rho_fb_error": raw_fb,
                "partial_u_error_given_fb": p,
            }
            lo, hi = p["ci95"]
            print(
                f"    {target:32s} raw_u={raw_u:+.4f} raw_FB={raw_fb:+.4f} "
                f"partial={p['rho']:+.4f} CI95=[{lo:+.4f},{hi:+.4f}]"
            )

    names = list(seqs)
    for test_i, test_name in enumerate(names):
        train_names = [n for n in names if n != test_name]
        report["loso"][test_name] = {"train": train_names, "targets": {}}
        print(f"\nLOSO held out {test_name}; train={'+'.join(train_names)}")
        for ti, target in enumerate(TARGETS):
            fold = loso_fold([seqs[n] for n in train_names], seqs[test_name], target, args.ridge_lambda)
            boot = bootstrap_loso_delta(
                fold, args.block_len, args.bootstrap,
                args.seed + 10000 + 1000 * test_i + 100 * ti,
            )
            clean = clean_fold_for_json(fold)
            clean["delta_rho_block_bootstrap"] = boot
            report["loso"][test_name]["targets"][target] = clean
            lo, hi = boot["ci95"]
            print(
                f"  {target:32s} FB={fold['rho_fb']:+.4f} FB+U={fold['rho_fb_plus_u']:+.4f} "
                f"delta={fold['delta_rho']:+.4f} CI95=[{lo:+.4f},{hi:+.4f}] "
                f"dRankMAE={fold['delta_rank_mae']:+.4f}"
            )

    # Macro summaries and a transparent directional count.  We deliberately do
    # not print an automatic scientific GO/STOP verdict; interpretation should
    # consider effect size, direction, and temporal-bootstrap uncertainty.
    macro = {"partial": {}, "loso_delta": {}}
    for target in TARGETS:
        partials = [
            report["within_sequence"][n]["targets"][target]["partial_u_error_given_fb"]["rho"]
            for n in names
        ]
        deltas = [report["loso"][n]["targets"][target]["delta_rho"] for n in names]
        macro["partial"][target] = {
            "mean": float(np.mean(partials)),
            "positive_folds": int(sum(v > 0 for v in partials)),
            "values": partials,
        }
        macro["loso_delta"][target] = {
            "mean": float(np.mean(deltas)),
            "positive_folds": int(sum(v > 0 for v in deltas)),
            "values": deltas,
        }
    report["macro"] = macro

    print("\n" + "-" * 96)
    print("Macro directional summary")
    for target in TARGETS:
        p = macro["partial"][target]
        d = macro["loso_delta"][target]
        print(
            f"  {target:32s} partial mean={p['mean']:+.4f} positive={p['positive_folds']}/3; "
            f"LOSO delta mean={d['mean']:+.4f} positive={d['positive_folds']}/3"
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump(report, f, indent=2, allow_nan=True)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
