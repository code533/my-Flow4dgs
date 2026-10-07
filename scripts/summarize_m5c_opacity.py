#!/usr/bin/env python3
"""Summarize M5-C opacity initialization audit."""

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

    rows=[]
    with args.csv_path.open(newline="") as fp:
        rows=list(csv.DictReader(fp))
    if not rows:
        raise RuntimeError(f"No rows in {args.csv_path}")

    applied=[r for r in rows if int(r["m5c_applied"])==1]
    alphas=np.asarray([f(r["alpha_init"]) for r in rows],dtype=np.float64)
    conf=np.asarray([f(r["m5_confidence"]) for r in applied],dtype=np.float64)

    print("file:",args.csv_path)
    print("rows:",len(rows))
    print("m5c_applied_rows:",len(applied))
    print("m5c_applied_fraction:",len(applied)/len(rows))
    print(
        "alpha min/median/max:",
        float(np.nanmin(alphas)),
        float(np.nanmedian(alphas)),
        float(np.nanmax(alphas)),
    )
    if len(applied):
        aa=np.asarray([f(r["alpha_init"]) for r in applied],dtype=np.float64)
        print(
            "applied alpha min/median/max:",
            float(np.nanmin(aa)),
            float(np.nanmedian(aa)),
            float(np.nanmax(aa)),
        )
        print(
            "applied confidence min/median/max:",
            float(np.nanmin(conf)),
            float(np.nanmedian(conf)),
            float(np.nanmax(conf)),
        )
        low=sum(1 for r in applied if f(r["alpha_init"]) < 0.5)
        print("attenuated_rows:",low)


if __name__=="__main__":
    main()
