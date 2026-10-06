#!/usr/bin/env python3
"""Nested M4-A2 ablation for the frozen direct-flow regime descriptor."""

import argparse
import csv
import json
from pathlib import Path
import numpy as np

TARGETS=("slam_final_rel_error_t_m","slam_final_rel_error_r_rad")
DESCRIPTOR="direct_flow_median_px"


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
    X=np.asarray(X,dtype=np.float64)
    A=np.column_stack([np.ones(len(X)),X])
    return A@beta


def load_table(path):
    rows=[]
    with Path(path).open(newline="") as f:
        for r in csv.DictReader(f):
            row={"sequence":r["sequence"],"frame":int(float(r["frame"]))}
            for k,v in r.items():
                if k in ("sequence","frame"):
                    continue
                row[k]=float(v)
            rows.append(row)
    return rows


def fit_fold(train,target,lam):
    X={"M0":[],"M1":[],"MZ":[],"MA":[],"MI":[]}
    y=[]
    names=sorted(set(r["sequence"] for r in train))
    for name in names:
        rr=[r for r in train if r["sequence"]==name]
        fb=pct_rank([r["fb_error_median_px"] for r in rr])
        cy=pct_rank([r["u_cycle_median_px"] for r in rr])
        zz=pct_rank([r[DESCRIPTOR] for r in rr])
        ee=pct_rank([r[target] for r in rr])
        X["M0"].extend(fb[:,None].tolist())
        X["M1"].extend(np.column_stack([fb,cy]).tolist())
        X["MZ"].extend(np.column_stack([fb,zz]).tolist())
        X["MA"].extend(np.column_stack([fb,cy,zz]).tolist())
        X["MI"].extend(np.column_stack([fb,cy,zz,cy*zz]).tolist())
        y.extend(ee.tolist())
    return {k:ridge_fit(v,y,lam) for k,v in X.items()}


def eval_fold(test,target,betas):
    fb=pct_rank([r["fb_error_median_px"] for r in test])
    cy=pct_rank([r["u_cycle_median_px"] for r in test])
    zz=pct_rank([r[DESCRIPTOR] for r in test])
    ee=pct_rank([r[target] for r in test])
    X={
        "M0":fb[:,None],
        "M1":np.column_stack([fb,cy]),
        "MZ":np.column_stack([fb,zz]),
        "MA":np.column_stack([fb,cy,zz]),
        "MI":np.column_stack([fb,cy,zz,cy*zz]),
    }
    out={}
    for k in X:
        out[k]=spearman(ridge_predict(X[k],betas[k]),ee)
    out["delta_Z_vs_FB"]=out["MZ"]-out["M0"]
    out["delta_cycle_given_Z"]=out["MA"]-out["MZ"]
    out["delta_additive_vs_FB"]=out["MA"]-out["M0"]
    out["delta_interaction_vs_additive"]=out["MI"]-out["MA"]
    out["delta_interaction_vs_FB"]=out["MI"]-out["M0"]
    out["beta_interaction"]=float(betas["MI"][-1])
    return out


def summarize(folds):
    keys=[
        "delta_Z_vs_FB",
        "delta_cycle_given_Z",
        "delta_additive_vs_FB",
        "delta_interaction_vs_additive",
        "delta_interaction_vs_FB",
    ]
    out={}
    for k in keys:
        vals=np.asarray([f[k] for f in folds.values()],dtype=np.float64)
        out[k]={
            "mean":float(np.nanmean(vals)),
            "positive":int(np.sum(vals>0)),
            "total":len(vals),
        }
    b=np.asarray([f["beta_interaction"] for f in folds.values()],dtype=np.float64)
    out["beta_interaction"]={
        "mean":float(np.nanmean(b)),
        "positive":int(np.sum(b>0)),
        "negative":int(np.sum(b<0)),
    }
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("table",type=Path)
    ap.add_argument("--ridge-lambda",type=float,default=1e-3)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()

    rows=load_table(args.table)
    names=sorted(set(r["sequence"] for r in rows))
    report={
        "method":"m4a2_direct_flow_nested_ablation_v1",
        "development_only":True,
        "descriptor":DESCRIPTOR,
        "models":{
            "M0":"FB",
            "M1":"FB+CYCLE",
            "MZ":"FB+Z",
            "MA":"FB+CYCLE+Z",
            "MI":"FB+CYCLE+Z+CYCLE*Z",
        },
        "targets":{},
    }

    print("="*98)
    print("M4-A2 DIRECT-FLOW NESTED ABLATION — DEVELOPMENT SET ONLY")
    print("="*98)

    for target in TARGETS:
        folds={}
        for held in names:
            train=[r for r in rows if r["sequence"]!=held]
            test=[r for r in rows if r["sequence"]==held]
            betas=fit_fold(train,target,args.ridge_lambda)
            folds[held]=eval_fold(test,target,betas)
        summary=summarize(folds)
        report["targets"][target]={"folds":folds,"summary":summary}

        print(f"\n{target}")
        for held in names:
            x=folds[held]
            print(
                f"  held {held}: "
                f"M0={x['M0']:+.4f} M1={x['M1']:+.4f} "
                f"MZ={x['MZ']:+.4f} MA={x['MA']:+.4f} MI={x['MI']:+.4f} | "
                f"dZ={x['delta_Z_vs_FB']:+.4f} "
                f"dCycle|Z={x['delta_cycle_given_Z']:+.4f} "
                f"dInt|Add={x['delta_interaction_vs_additive']:+.4f} "
                f"betaInt={x['beta_interaction']:+.4f}"
            )
        print("  summary:")
        for k,v in summary.items():
            if k=="beta_interaction":
                print(
                    f"    {k:30s} mean={v['mean']:+.4f} "
                    f"sign(+/-)={v['positive']}/{v['negative']}"
                )
            else:
                print(
                    f"    {k:30s} mean={v['mean']:+.4f} "
                    f"positive={v['positive']}/{v['total']}"
                )

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=True))
    print(f"\nSaved {args.output}")


if __name__=="__main__":
    main()
