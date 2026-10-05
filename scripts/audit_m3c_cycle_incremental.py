#!/usr/bin/env python3
"""Audit M3-C temporal-cycle incremental reliability value beyond FB."""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import torch

TARGETS = (
    "slam_final_rel_error_t_m",
    "slam_final_rel_error_r_rad",
)
SIGNAL = "u_cycle_median_px"


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
    A = np.column_stack([np.ones(len(x)), x])
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
        "ci95": [float(np.quantile(vals, .025)), float(np.quantile(vals, .975))],
        "n_boot": len(vals),
    }


def ridge_fit(X, y, lam):
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    A = np.column_stack([np.ones(len(X)), X])
    penalty = np.eye(A.shape[1]) * float(lam)
    penalty[0, 0] = 0.0
    return np.linalg.solve(A.T @ A + penalty, A.T @ y)


def ridge_predict(X, beta):
    X = np.asarray(X, dtype=np.float64)
    A = np.column_stack([np.ones(len(X)), X])
    return A @ beta


def load_m3c(directory):
    out = {}
    files = sorted(Path(directory).glob("*.pt"))
    if not files:
        raise FileNotFoundError(f"No M3-C payloads in {directory}")
    for path in files:
        try:
            d = torch.load(path, map_location="cpu", weights_only=False)
        except TypeError:
            d = torch.load(path, map_location="cpu")
        if d.get("method") != "m3c_temporal_cycle_inconsistency_v1":
            continue
        if not bool(d.get("valid", False)):
            continue
        frame = int(d.get("frame", int(path.stem)))
        out[frame] = {
            SIGNAL: float(d[SIGNAL]),
            "u_cycle_mean_px": float(d["u_cycle_mean_px"]),
            "u_cycle_q90_px": float(d["u_cycle_q90_px"]),
            "u_cycle_q95_px": float(d["u_cycle_q95_px"]),
            "direct_flow_median_px": float(d["direct_flow_median_px"]),
            "composed_flow_median_px": float(d["composed_flow_median_px"]),
            "num_valid_pixels": int(d["num_valid_pixels"]),
        }
    if not out:
        raise RuntimeError(f"No valid M3-C payloads in {directory}")
    return out


def load_csv(path):
    out = {}
    with Path(path).open(newline="") as f:
        for row in csv.DictReader(f):
            needed = ["frame", "fb_error_median_px", *TARGETS]
            if not all(k in row for k in needed):
                raise KeyError(f"{path}: missing required columns")
            vals = {k: float(row[k]) for k in needed}
            if not all(finite(vals[k]) for k in needed):
                continue
            out[int(float(row["frame"]))] = vals
    return out


def parse_sequence(value):
    if "=" not in value:
        raise ValueError(f"Expected NAME=M3C_DIR,CSV, got {value!r}")
    name, rest = value.split("=", 1)
    parts = rest.split(",")
    if len(parts) != 2:
        raise ValueError(f"Expected NAME=M3C_DIR,CSV, got {value!r}")
    return name.strip(), Path(parts[0]), Path(parts[1])


def join_sequence(name, m3c_dir, csv_path):
    a, b = load_m3c(m3c_dir), load_csv(csv_path)
    rows = []
    for frame in sorted(set(a) & set(b)):
        row = {"sequence": name, "frame": frame}
        row.update(a[frame])
        row.update(b[frame])
        rows.append(row)
    if len(rows) < 20:
        raise RuntimeError(f"{name}: only {len(rows)} joined rows")
    return rows


def summarize(rows, block_len, n_boot, seed):
    out = {"n": len(rows), "targets": {}}
    s = np.asarray([r[SIGNAL] for r in rows], dtype=np.float64)
    fb = np.asarray([r["fb_error_median_px"] for r in rows], dtype=np.float64)
    for target in TARGETS:
        e = np.asarray([r[target] for r in rows], dtype=np.float64)
        out["targets"][target] = {
            "raw_cycle_rho": spearman(s, e),
            "raw_fb_rho": spearman(fb, e),
            "cycle_fb_rho": spearman(s, fb),
            "partial_after_fb": bootstrap_partial(s, e, fb, block_len, n_boot, seed),
        }
    return out


def loso(sequences, lam):
    names = list(sequences)
    out = {}
    for held in names:
        train_names = [n for n in names if n != held]
        fold = {"train": train_names, "targets": {}}
        test = sequences[held]
        for target in TARGETS:
            X0, X1, y = [], [], []
            for name in train_names:
                rows = sequences[name]
                fb = percentile_rank([r["fb_error_median_px"] for r in rows])
                s = percentile_rank([r[SIGNAL] for r in rows])
                e = percentile_rank([r[target] for r in rows])
                X0.extend(fb[:, None].tolist())
                X1.extend(np.column_stack([fb, s]).tolist())
                y.extend(e.tolist())
            b0 = ridge_fit(X0, y, lam)
            b1 = ridge_fit(X1, y, lam)
            fb = percentile_rank([r["fb_error_median_px"] for r in test])
            s = percentile_rank([r[SIGNAL] for r in test])
            e = percentile_rank([r[target] for r in test])
            p0 = ridge_predict(fb[:, None], b0)
            p1 = ridge_predict(np.column_stack([fb, s]), b1)
            r0, r1 = spearman(p0, e), spearman(p1, e)
            fold["targets"][target] = {
                "rho_fb": r0,
                "rho_fb_plus_cycle": r1,
                "delta_rho": r1 - r0,
            }
        out[held] = fold
    return out


def macro(per_sequence, loso_report):
    out = {}
    for target in TARGETS:
        partial = [
            per_sequence[n]["targets"][target]["partial_after_fb"]["rho"]
            for n in per_sequence
        ]
        delta = [
            loso_report[n]["targets"][target]["delta_rho"]
            for n in loso_report
        ]
        out[target] = {
            "partial_mean": float(np.nanmean(partial)),
            "partial_positive": int(np.sum(np.asarray(partial) > 0)),
            "partial_total": len(partial),
            "loso_delta_mean": float(np.nanmean(delta)),
            "loso_delta_positive": int(np.sum(np.asarray(delta) > 0)),
            "loso_delta_total": len(delta),
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

    seqs = {}
    specs = {}
    for value in args.sequence:
        name, d, c = parse_sequence(value)
        seqs[name] = join_sequence(name, d, c)
        specs[name] = {"m3c_dir": str(d), "csv": str(c)}

    per = {
        n: summarize(r, args.block_len, args.bootstrap, args.seed)
        for n, r in seqs.items()
    }
    lr = loso(seqs, args.ridge_lambda)
    mc = macro(per, lr)

    print("=" * 94)
    print("M3-C TEMPORAL-CYCLE INCREMENTAL-VALUE AUDIT — conditioned on FB consistency")
    print("=" * 94)
    for name, s in per.items():
        print(f"\n{name}: n={s['n']}")
        for target, x in s["targets"].items():
            p = x["partial_after_fb"]
            print(
                f"  {target:30s} CYCLE={x['raw_cycle_rho']:+.4f} "
                f"FB={x['raw_fb_rho']:+.4f} CYCLE~FB={x['cycle_fb_rho']:+.4f} "
                f"partial={p['rho']:+.4f} "
                f"CI95=[{p['ci95'][0]:+.4f},{p['ci95'][1]:+.4f}]"
            )

    print("\nLOSO:")
    for held, f in lr.items():
        print(f"  held out {held}; train={'+'.join(f['train'])}")
        for target, x in f["targets"].items():
            print(
                f"    {target:28s} FB={x['rho_fb']:+.4f} "
                f"FB+CYCLE={x['rho_fb_plus_cycle']:+.4f} "
                f"delta={x['delta_rho']:+.4f}"
            )

    print("\nMacro directional summary")
    for target, x in mc.items():
        print(
            f"  {target:30s} partial mean={x['partial_mean']:+.4f} "
            f"positive={x['partial_positive']}/{x['partial_total']}; "
            f"LOSO delta mean={x['loso_delta_mean']:+.4f} "
            f"positive={x['loso_delta_positive']}/{x['loso_delta_total']}"
        )

    report = {
        "method": "m3c_temporal_cycle_incremental_value_v1",
        "primary_signal": SIGNAL,
        "sequence_inputs": specs,
        "per_sequence": per,
        "loso": lr,
        "macro": mc,
        "block_len": args.block_len,
        "bootstrap": args.bootstrap,
        "seed": args.seed,
        "ridge_lambda": args.ridge_lambda,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=True))
    print(f"\nSaved {args.output}")


if __name__ == "__main__":
    main()
