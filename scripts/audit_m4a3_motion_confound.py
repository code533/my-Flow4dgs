#!/usr/bin/env python3
"""M4-A3: audit direct-flow reliability after controlling pose-motion magnitude.

Development-set confound analysis only.  Joins the existing M4 regime table
with M1 per-frame payloads to recover the actually applied baseline relative
motion T_rel_applied.
"""

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
FLOW = "direct_flow_median_px"


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


def corr(x,y):
    x=np.asarray(x,dtype=np.float64)
    y=np.asarray(y,dtype=np.float64)
    if len(x)<3 or np.std(x)==0 or np.std(y)==0:
        return float("nan")
    return float(np.corrcoef(x,y)[0,1])


def spearman(x,y):
    return corr(rankdata(x),rankdata(y))


def residualize(y, X):
    y=np.asarray(y,dtype=np.float64)
    X=np.asarray(X,dtype=np.float64)
    A=np.column_stack([np.ones(len(X)),X])
    beta,*_=np.linalg.lstsq(A,y,rcond=None)
    return y-A@beta


def partial_spearman(signal, target, controls):
    s=rankdata(signal)
    t=rankdata(target)
    C=np.column_stack([rankdata(c) for c in controls])
    return corr(residualize(s,C),residualize(t,C))


def ridge_fit(X,y,lam):
    X=np.asarray(X,dtype=np.float64)
    y=np.asarray(y,dtype=np.float64)
    A=np.column_stack([np.ones(len(X)),X])
    P=np.eye(A.shape[1])*float(lam)
    P[0,0]=0.0
    return np.linalg.solve(A.T@A+P,A.T@y)


def ridge_predict(X,beta):
    A=np.column_stack([np.ones(len(X)),np.asarray(X,dtype=np.float64)])
    return A@beta


def rotation_angle(T):
    R=T[:3,:3].double()
    x=torch.clamp((torch.trace(R)-1.0)/2.0,-1.0,1.0)
    return float(torch.acos(x))


def load_m1_motion(m1_dir):
    out={}
    for p in sorted(Path(m1_dir).glob("*.pt")):
        try:
            d=torch.load(p,map_location="cpu",weights_only=False)
        except TypeError:
            d=torch.load(p,map_location="cpu")
        if "T_rel_applied" not in d:
            continue
        frame=int(d.get("frame",int(p.stem)))
        T=torch.as_tensor(d["T_rel_applied"]).double()
        out[frame]={
            "applied_translation_norm_m":float(torch.linalg.norm(T[:3,3])),
            "applied_rotation_angle_rad":rotation_angle(T),
        }
    if not out:
        raise RuntimeError(f"No T_rel_applied payloads in {m1_dir}")
    return out


def load_table(path):
    byseq={}
    with Path(path).open(newline="") as f:
        for r in csv.DictReader(f):
            name=r["sequence"]
            row={"sequence":name,"frame":int(float(r["frame"]))}
            for k,v in r.items():
                if k in ("sequence","frame"):
                    continue
                row[k]=float(v)
            byseq.setdefault(name,[]).append(row)
    return byseq


def parse_motion(value):
    if "=" not in value:
        raise ValueError("Expected NAME=M1_DIR")
    n,p=value.split("=",1)
    return n.strip(),Path(p)


def loso(rows_by_seq,target,lam):
    names=sorted(rows_by_seq)
    folds={}
    for held in names:
        X0=[]; X1=[]; y=[]
        for name in names:
            if name==held: continue
            rr=rows_by_seq[name]
            fb=pct_rank([r["fb_error_median_px"] for r in rr])
            fl=pct_rank([r[FLOW] for r in rr])
            mt=pct_rank([r["applied_translation_norm_m"] for r in rr])
            mr=pct_rank([r["applied_rotation_angle_rad"] for r in rr])
            ee=pct_rank([r[target] for r in rr])
            X0.extend(np.column_stack([fb,mt,mr]).tolist())
            X1.extend(np.column_stack([fb,mt,mr,fl]).tolist())
            y.extend(ee.tolist())
        b0=ridge_fit(X0,y,lam); b1=ridge_fit(X1,y,lam)
        rr=rows_by_seq[held]
        fb=pct_rank([r["fb_error_median_px"] for r in rr])
        fl=pct_rank([r[FLOW] for r in rr])
        mt=pct_rank([r["applied_translation_norm_m"] for r in rr])
        mr=pct_rank([r["applied_rotation_angle_rad"] for r in rr])
        ee=pct_rank([r[target] for r in rr])
        p0=ridge_predict(np.column_stack([fb,mt,mr]),b0)
        p1=ridge_predict(np.column_stack([fb,mt,mr,fl]),b1)
        r0=spearman(p0,ee); r1=spearman(p1,ee)
        folds[held]={
            "rho_fb_motion":r0,
            "rho_fb_motion_flow":r1,
            "delta_flow_given_motion":r1-r0,
        }
    return folds


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("table",type=Path)
    ap.add_argument("--m1",nargs="+",required=True,help="NAME=M1_POSE_UNCERTAINTY_DIR")
    ap.add_argument("--ridge-lambda",type=float,default=1e-3)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()

    rows_by_seq=load_table(args.table)
    motion_dirs=dict(parse_motion(v) for v in args.m1)

    for name,rr in rows_by_seq.items():
        if name not in motion_dirs:
            raise KeyError(f"Missing --m1 entry for {name}")
        mm=load_m1_motion(motion_dirs[name])
        kept=[]
        for r in rr:
            if r["frame"] in mm:
                r.update(mm[r["frame"]])
                eps=1e-6
                r["normalized_t_error"]=r["slam_final_rel_error_t_m"]/(r["applied_translation_norm_m"]+eps)
                r["normalized_r_error"]=r["slam_final_rel_error_r_rad"]/(r["applied_rotation_angle_rad"]+eps)
                kept.append(r)
        rows_by_seq[name]=kept
        if len(kept)<20:
            raise RuntimeError(f"{name}: only {len(kept)} joined rows")

    report={"method":"m4a3_motion_confound_v1","development_only":True,"sequences":{},"targets":{}}

    print("="*98)
    print("M4-A3 DIRECT-FLOW MOTION-CONFOUND AUDIT — DEVELOPMENT SET ONLY")
    print("="*98)

    for name,rr in rows_by_seq.items():
        controls=[
            [r["fb_error_median_px"] for r in rr],
            [r["applied_translation_norm_m"] for r in rr],
            [r["applied_rotation_angle_rad"] for r in rr],
        ]
        report["sequences"][name]={
            "n":len(rr),
            "flow_vs_translation_motion_rho":spearman(
                [r[FLOW] for r in rr],[r["applied_translation_norm_m"] for r in rr]
            ),
            "flow_vs_rotation_motion_rho":spearman(
                [r[FLOW] for r in rr],[r["applied_rotation_angle_rad"] for r in rr]
            ),
            "partial_flow_vs_abs_t_error_given_fb_motion":partial_spearman(
                [r[FLOW] for r in rr],[r["slam_final_rel_error_t_m"] for r in rr],controls
            ),
            "partial_flow_vs_abs_r_error_given_fb_motion":partial_spearman(
                [r[FLOW] for r in rr],[r["slam_final_rel_error_r_rad"] for r in rr],controls
            ),
            "flow_vs_normalized_t_error_rho":spearman(
                [r[FLOW] for r in rr],[r["normalized_t_error"] for r in rr]
            ),
            "flow_vs_normalized_r_error_rho":spearman(
                [r[FLOW] for r in rr],[r["normalized_r_error"] for r in rr]
            ),
        }
        x=report["sequences"][name]
        print(
            f"\n{name}: n={len(rr)} "
            f"flow~|t|={x['flow_vs_translation_motion_rho']:+.4f} "
            f"flow~|r|={x['flow_vs_rotation_motion_rho']:+.4f}"
        )
        print(
            f"  partial flow~absErr | FB,motion: "
            f"t={x['partial_flow_vs_abs_t_error_given_fb_motion']:+.4f} "
            f"r={x['partial_flow_vs_abs_r_error_given_fb_motion']:+.4f}"
        )
        print(
            f"  flow~normalizedErr: "
            f"t={x['flow_vs_normalized_t_error_rho']:+.4f} "
            f"r={x['flow_vs_normalized_r_error_rho']:+.4f}"
        )

    for target in TARGETS:
        folds=loso(rows_by_seq,target,args.ridge_lambda)
        ds=np.asarray([v["delta_flow_given_motion"] for v in folds.values()])
        report["targets"][target]={
            "folds":folds,
            "summary":{
                "mean_delta_flow_given_motion":float(np.mean(ds)),
                "positive":int(np.sum(ds>0)),
                "total":len(ds),
            }
        }
        print(f"\nLOSO {target}")
        for held,x in folds.items():
            print(
                f"  held {held}: FB+motion={x['rho_fb_motion']:+.4f} "
                f"+flow={x['rho_fb_motion_flow']:+.4f} "
                f"delta={x['delta_flow_given_motion']:+.4f}"
            )
        s=report["targets"][target]["summary"]
        print(
            f"  macro delta={s['mean_delta_flow_given_motion']:+.4f} "
            f"positive={s['positive']}/{s['total']}"
        )

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=True))
    print(f"\nSaved {args.output}")


if __name__=="__main__":
    main()
