#!/usr/bin/env python3
"""Build a per-frame M4 regime-analysis table from existing M3-C + reliability outputs."""

import argparse
import csv
import math
from pathlib import Path

import torch


REQUIRED_RELIABILITY = [
    "frame",
    "fb_error_median_px",
    "valid_extent",
    "num_pixels",
    "log10_condition",
    "motion_scale_joint",
    "sigma_t",
    "sigma_r",
    "slam_final_rel_error_t_m",
    "slam_final_rel_error_r_rad",
]


def finite(x):
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def load_reliability_csv(path):
    rows = {}
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        missing = [k for k in REQUIRED_RELIABILITY if k not in reader.fieldnames]
        if missing:
            raise KeyError(f"{path}: missing columns {missing}")
        for row in reader:
            frame = int(float(row["frame"]))
            vals = {}
            ok = True
            for key in REQUIRED_RELIABILITY[1:]:
                try:
                    vals[key] = float(row[key])
                except (TypeError, ValueError):
                    ok = False
                    break
            if ok:
                rows[frame] = vals
    if not rows:
        raise RuntimeError(f"No usable reliability rows in {path}")
    return rows


def load_cycle_dir(path):
    rows = {}
    files = sorted(Path(path).glob("*.pt"))
    if not files:
        raise FileNotFoundError(f"No M3-C payloads in {path}")
    for p in files:
        try:
            d = torch.load(p, map_location="cpu", weights_only=False)
        except TypeError:
            d = torch.load(p, map_location="cpu")
        if d.get("method") != "m3c_temporal_cycle_inconsistency_v1":
            continue
        if not bool(d.get("valid", False)):
            continue
        frame = int(d.get("frame", int(p.stem)))
        rows[frame] = {
            "u_cycle_median_px": float(d["u_cycle_median_px"]),
            "u_cycle_mean_px": float(d["u_cycle_mean_px"]),
            "u_cycle_q90_px": float(d["u_cycle_q90_px"]),
            "u_cycle_q95_px": float(d["u_cycle_q95_px"]),
            "direct_flow_median_px": float(d["direct_flow_median_px"]),
            "composed_flow_median_px": float(d["composed_flow_median_px"]),
            "cycle_num_valid_pixels": int(d["num_valid_pixels"]),
        }
    if not rows:
        raise RuntimeError(f"No valid M3-C rows in {path}")
    return rows


def parse_sequence(value):
    if "=" not in value:
        raise ValueError(f"Expected NAME=CYCLE_DIR,CSV, got {value!r}")
    name, rest = value.split("=", 1)
    parts = rest.split(",")
    if len(parts) != 2:
        raise ValueError(f"Expected NAME=CYCLE_DIR,CSV, got {value!r}")
    return name.strip(), Path(parts[0]), Path(parts[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence", nargs="+", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    out_rows = []
    for spec in args.sequence:
        name, cycle_dir, rel_csv = parse_sequence(spec)
        cyc = load_cycle_dir(cycle_dir)
        rel = load_reliability_csv(rel_csv)
        frames = sorted(set(cyc) & set(rel))
        if len(frames) < 20:
            raise RuntimeError(f"{name}: only {len(frames)} joined frames")

        for frame in frames:
            r = {"sequence": name, "frame": frame}
            r.update(rel[frame])
            r.update(cyc[frame])

            eps = 1e-6
            direct = r["direct_flow_median_px"]
            comp = r["composed_flow_median_px"]
            cyc_med = r["u_cycle_median_px"]
            r["cycle_to_direct"] = cyc_med / (direct + eps)
            r["cycle_to_composed"] = cyc_med / (comp + eps)
            r["direct_composed_ratio"] = direct / (comp + eps)
            r["log_direct_flow"] = math.log1p(max(direct, 0.0))
            r["support_fraction_cycle"] = (
                r["cycle_num_valid_pixels"] / max(r["num_pixels"], 1.0)
            )
            out_rows.append(r)

    if not out_rows:
        raise RuntimeError("No joined M4 rows")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    keys = list(out_rows[0].keys())
    with args.output.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Saved {args.output}")
    by_seq = {}
    for r in out_rows:
        by_seq.setdefault(r["sequence"], 0)
        by_seq[r["sequence"]] += 1
    for name, n in sorted(by_seq.items()):
        print(f"  {name}: {n} rows")


if __name__ == "__main__":
    main()
