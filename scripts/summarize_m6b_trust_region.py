#!/usr/bin/env python3
"""Summarize Flow4DGS M6-B pose trust-region activation."""
import argparse, csv, math
from pathlib import Path
import numpy as np

def f(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else float("nan")
    except Exception:
        return float("nan")

def stats(rows,key):
    a=np.asarray([f(r[key]) for r in rows],dtype=np.float64)
    return float(np.nanmin(a)),float(np.nanmedian(a)),float(np.nanmax(a))

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
    print("trigger_fraction_valid:",0.0 if not valid else len(trig)/len(valid))
    if valid: print("confidence min/median/max:",*stats(valid,"confidence"))
    if trig:
        print("scale min/median/max:",*stats(trig,"applied_scale"))
        print("corr_t_before_m min/median/max:",*stats(trig,"corr_t_before_m"))
        print("corr_t_after_m min/median/max:",*stats(trig,"corr_t_after_m"))
        print("corr_r_before_rad min/median/max:",*stats(trig,"corr_r_before_rad"))
        print("corr_r_after_rad min/median/max:",*stats(trig,"corr_r_after_rad"))
        print("triggered_frames:",",".join(r["frame"] for r in trig))
if __name__=="__main__":
    main()
