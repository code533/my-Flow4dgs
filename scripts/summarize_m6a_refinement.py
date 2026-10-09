#!/usr/bin/env python3
"""Summarize Flow4DGS M6-A pose refinement."""

import argparse
import csv
import math
from pathlib import Path
import numpy as np

def f(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else float("nan")
    except Exception:
        return float("nan")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv_path",type=Path)
    args=ap.parse_args()

    with args.csv_path.open(newline="") as fp:
        rows=list(csv.DictReader(fp))
    if not rows:
        raise RuntimeError(f"No rows in {args.csv_path}")

    valid=[r for r in rows if int(r["m5_valid"])==1]
    trig=[r for r in rows if int(r["triggered"])==1]

    print("file:",args.csv_path)
    print("frames:",len(rows))
    print("valid_reliability_frames:",len(valid))
    print("triggered_frames:",len(trig))
    print("trigger_fraction_all:",0.0 if not rows else len(trig)/len(rows))
    print("trigger_fraction_valid:",0.0 if not valid else len(trig)/len(valid))

    if valid:
        c=np.asarray([f(r["confidence"]) for r in valid],dtype=np.float64)
        print("confidence min/median/max:",float(np.nanmin(c)),float(np.nanmedian(c)),float(np.nanmax(c)))
    if trig:
        dt=np.asarray([f(r["extra_delta_t_m"]) for r in trig],dtype=np.float64)
        dr=np.asarray([f(r["extra_delta_r_rad"]) for r in trig],dtype=np.float64)
        its=np.asarray([int(r["extra_iters"]) for r in trig],dtype=np.int64)
        print("extra_iters min/median/max:",int(np.min(its)),float(np.median(its)),int(np.max(its)))
        print("extra_delta_t_m min/median/max:",float(np.nanmin(dt)),float(np.nanmedian(dt)),float(np.nanmax(dt)))
        print("extra_delta_r_rad min/median/max:",float(np.nanmin(dr)),float(np.nanmedian(dr)),float(np.nanmax(dr)))
        print("triggered_frames:",",".join(r["frame"] for r in trig))

if __name__=="__main__":
    main()
