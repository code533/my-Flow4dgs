#!/usr/bin/env python3
"""Exploratory LOSO interaction audit for M4 regime-conditioned reliability."""

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

PRIMARY_DESCRIPTORS = (
    "direct_flow_median_px",
    "valid_extent",
    "log10_condition",
    "motion_scale_joint",
)

SECONDARY_DESCRIPTORS = (
    "cycle_to_direct",
    "cycle_to_composed",
    "direct_composed_ratio",
    "log_direct_flow",
    "support_fraction_cycle",
)


def rankdata(values):
    x=np.asarray(values,dtype=np.float64)
    order=np.argsort(x,kind="mergesort")
    ranks=np.empty_like(x)
    i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[order[j]]==x[order[i]]:
            j+=1
        ranks[order[i:j]]=0.5*((i+1)+j)
        i=j
    return ranks


def pct_rank(values):
    x=np.asarray(values,dtype=np.float64)
    return (rankdata(x)-0.5)/float(len(x))


def spearman(x,y):
    x=np.asarray(x,dtype=np.float64)
    y=np.asarray(y,dtype=np.float64)
    if len(x)<3 or np.std(x)==0 or np.std(y)==0:
        return float("nan")
    return float(np.corrcoef(rankdata(x),rankdata(y))[0,1])


def ridge_fit(X,y,lam):
    X=np.asarray(X,dtype=np.float64)
    y=np.asarray(y,dtype=np.float64)
    A=np.column_stack([np.ones(len(X)),X])
    P=np.eye(A.shape[1],dtype=np.float64)*float(lam)
    P[0,0]=0.0
    return np.linalg.solve(A.T@A+P,A.T@y)


def ridge_predict(X,beta):
    A=np.column_stack([np.ones(len(X)),np.asarray(X,dtype=np.float64)])
    return A@beta


def load_table(path):
    rows=[]
    with Path(path).open(newline="") as f:
        for r in csv.DictReader(f):
            row={"sequence":r["sequence"],"frame":int(float(r["frame"]))}
            for k,v in r.items():
                if k in ("sequence","frame"):
                    continue
                try:
                    row[k]=float(v)
                except Exception:
                    row[k]=float("nan")
            rows.append(row)
    if not rows:
        raise RuntimeError("Empty M4 table")
    return rows


def per_sequence_summary(rows, descriptors):
    out={}
    names=sorted(set(r["sequence"] for r in rows))
    for name in names:
        rr=[r for r in rows if r["sequence"]==name]
        s={"n":len(rr),"descriptor_ranges":{},"cycle_error_spearman":{}}
        for d in descriptors:
            vals=np.asarray([r[d] for r in rr],dtype=np.float64)
            s["descriptor_ranges"][d]={
                "median":float(np.nanmedian(vals)),
                "q10":float(np.nanquantile(vals,.1)),
                "q90":float(np.nanquantile(vals,.9)),
            }
        for t in TARGETS:
            s["cycle_error_spearman"][t]=spearman(
                [r["u_cycle_median_px"] for r in rr],
                [r[t] for r in rr],
            )
        out[name]=s
    return out


def loso_descriptor(rows, descriptor, target, lam):
    names=sorted(set(r["sequence"] for r in rows))
    folds={}
    for held in names:
        train=[r for r in rows if r["sequence"]!=held]
        test=[r for r in rows if r["sequence"]==held]

        # rank within each sequence before pooling training rows
        X0=[]; X1=[]; X2=[]; y=[]
        for name in sorted(set(r["sequence"] for r in train)):
            rr=[r for r in train if r["sequence"]==name]
            fb=pct_rank([r["fb_error_median_px"] for r in rr])
            cy=pct_rank([r["u_cycle_median_px"] for r in rr])
            zz=pct_rank([r[descriptor] for r in rr])
            ee=pct_rank([r[target] for r in rr])
            X0.extend(fb[:,None].tolist())
            X1.extend(np.column_stack([fb,cy]).tolist())
            X2.extend(np.column_stack([fb,cy,zz,cy*zz]).tolist())
            y.extend(ee.tolist())

        b0=ridge_fit(X0,y,lam)
        b1=ridge_fit(X1,y,lam)
        b2=ridge_fit(X2,y,lam)

        fb=pct_rank([r["fb_error_median_px"] for r in test])
        cy=pct_rank([r["u_cycle_median_px"] for r in test])
        zz=pct_rank([r[descriptor] for r in test])
        ee=pct_rank([r[target] for r in test])

        p0=ridge_predict(fb[:,None],b0)
        p1=ridge_predict(np.column_stack([fb,cy]),b1)
        p2=ridge_predict(np.column_stack([fb,cy,zz,cy*zz]),b2)

        rho0=spearman(p0,ee)
        rho1=spearman(p1,ee)
        rho2=spearman(p2,ee)
        folds[held]={
            "train_sequences":[n for n in names if n!=held],
            "rho_fb":rho0,
            "rho_fb_cycle":rho1,
            "rho_regime":rho2,
            "delta_regime_vs_fb":rho2-rho0,
            "delta_regime_vs_cycle":rho2-rho1,
            "interaction_beta":float(b2[-1]),
        }
    return folds


def summarize_descriptor(folds):
    vals=list(folds.values())
    d0=np.asarray([v["delta_regime_vs_fb"] for v in vals],dtype=np.float64)
    d1=np.asarray([v["delta_regime_vs_cycle"] for v in vals],dtype=np.float64)
    ib=np.asarray([v["interaction_beta"] for v in vals],dtype=np.float64)
    return {
        "mean_delta_vs_fb":float(np.nanmean(d0)),
        "positive_delta_vs_fb":int(np.sum(d0>0)),
        "mean_delta_vs_cycle":float(np.nanmean(d1)),
        "positive_delta_vs_cycle":int(np.sum(d1>0)),
        "interaction_beta_mean":float(np.nanmean(ib)),
        "interaction_beta_positive":int(np.sum(ib>0)),
        "interaction_beta_negative":int(np.sum(ib<0)),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("table",type=Path)
    ap.add_argument("--ridge-lambda",type=float,default=1e-3)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()

    rows=load_table(args.table)
    descriptors=PRIMARY_DESCRIPTORS+SECONDARY_DESCRIPTORS

    report={
        "method":"m4_regime_interaction_audit_v1",
        "development_only":True,
        "table":str(args.table),
        "ridge_lambda":args.ridge_lambda,
        "primary_descriptors":list(PRIMARY_DESCRIPTORS),
        "secondary_descriptors":list(SECONDARY_DESCRIPTORS),
        "per_sequence":per_sequence_summary(rows,descriptors),
        "descriptors":{},
    }

    for d in descriptors:
        report["descriptors"][d]={}
        for t in TARGETS:
            folds=loso_descriptor(rows,d,t,args.ridge_lambda)
            report["descriptors"][d][t]={
                "folds":folds,
                "summary":summarize_descriptor(folds),
            }

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=True))

    print("="*98)
    print("M4-A REGIME INTERACTION AUDIT — DEVELOPMENT SET ONLY")
    print("="*98)
    print("Do not interpret box1/box2/box3 as confirmatory validation.")
    for d in PRIMARY_DESCRIPTORS:
        print(f"\nPRIMARY descriptor: {d}")
        for t in TARGETS:
            x=report["descriptors"][d][t]["summary"]
            print(
                f"  {t:30s} "
                f"dFB={x['mean_delta_vs_fb']:+.4f} "
                f"pos={x['positive_delta_vs_fb']}/3 "
                f"dCycle={x['mean_delta_vs_cycle']:+.4f} "
                f"pos={x['positive_delta_vs_cycle']}/3 "
                f"beta_int={x['interaction_beta_mean']:+.4f} "
                f"sign(+/-)={x['interaction_beta_positive']}/{x['interaction_beta_negative']}"
            )

    print("\nSecondary exploratory descriptors")
    for d in SECONDARY_DESCRIPTORS:
        vals=[]
        for t in TARGETS:
            x=report["descriptors"][d][t]["summary"]
            vals.append(
                f"{t.split('_')[-2]} dFB={x['mean_delta_vs_fb']:+.3f}"
            )
        print(f"  {d:28s} " + " | ".join(vals))

    print(f"\nSaved {args.output}")


if __name__=="__main__":
    main()
