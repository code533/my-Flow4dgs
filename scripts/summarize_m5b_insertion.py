#!/usr/bin/env python3
"""Summarize one M5-B insertion-decision CSV."""

import argparse
import csv
import math
from pathlib import Path

import numpy as np


def to_float(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else float("nan")
    except Exception:
        return float("nan")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv_path",type=Path)
    args=ap.parse_args()

    rows=[]
    with args.csv_path.open(newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        raise RuntimeError(f"No rows in {args.csv_path}")

    requested=[r for r in rows if int(r["requested"]) == 1]
    rejected=[r for r in requested if int(r["admitted"]) == 0]
    admitted=[r for r in requested if int(r["admitted"]) == 1]

    conf=np.asarray(
        [to_float(r["confidence"]) for r in requested],dtype=np.float64
    )
    direct=np.asarray(
        [to_float(r["direct_flow_median_px"]) for r in requested],
        dtype=np.float64,
    )
    valid=np.isfinite(conf)

    print("file:",args.csv_path)
    print("requests:",len(requested))
    print("admitted:",len(admitted))
    print("rejected:",len(rejected))
    print(
        "rejection_fraction:",
        0.0 if not requested else len(rejected)/len(requested),
    )

    if np.any(valid):
        x=conf[valid]
        print(
            "confidence min/median/max:",
            float(np.min(x)),
            float(np.median(x)),
            float(np.max(x)),
        )
    good_direct=np.isfinite(direct)
    if np.any(good_direct):
        x=direct[good_direct]
        print(
            "direct_flow min/median/max:",
            float(np.min(x)),
            float(np.median(x)),
            float(np.max(x)),
        )

    reasons={}
    for r in requested:
        reasons[r["reason"]]=reasons.get(r["reason"],0)+1
    print("reasons:")
    for k in sorted(reasons):
        print(f"  {k}: {reasons[k]}")

    if rejected:
        frames=[int(r["frame"]) for r in rejected]
        print("rejected_frames:",",".join(map(str,frames)))


if __name__=="__main__":
    main()
