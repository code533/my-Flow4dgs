# M3-B stage runbook

Status: ready for first execution.

## Goal

Test whether RAFT flow instability under matched photometric perturbations
contains held-out relative-pose reliability information beyond FB consistency.

M3-B is diagnostic only.  It does not modify Flow4DGS behavior.

## Branch

    feature/m3b-flow-perturbation

Base:

    feature/m3-source-discovery

## Fixed perturbation ensemble

The ordinary identity current->previous flow is reused from the baseline path.

Four extra RAFT evaluations are added on audited frames:

    gamma 0.80
    gamma 1.25
    contrast 0.80
    contrast 1.25

The same transform is applied to both frames.

Primary signal:

    u_TTA = median sqrt(trace(Sigma_F,p))

over the baseline-static and FB-valid support.

Do not alter this ensemble or summary statistic after inspecting held-out
results.

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m3b-flow-perturbation
    git pull

    python -m py_compile       utils/camera_utils.py       utils/m3b_flow_perturbation.py       scripts/audit_m3b_flow_incremental.py       utils/slam_frontend.py

## Step 1: box1 smoke run

    python slam.py       --config configs/rgbd/bonn/placing_box_m3b_flow.yaml       --eval --dynamic       --exp_name m3b_flow_box1       --save_results 0       --seed 0

Expected output directory contains:

    m1_pose_uncertainty/
    m2a_pose_uncertainty/
    m3b_flow_perturbation/

The M3-B directory appears when the first audited frame reaches frame 211, not
at process startup.

Expected diagnostic count for [211,271]: approximately 61 files.

Check:

    find <BOX1_RUN>/m3b_flow_perturbation -name '*.pt' | wc -l

Inspect one payload:

    python - <<'PY'
    import glob, torch
    p = sorted(glob.glob("<BOX1_RUN>/m3b_flow_perturbation/*.pt"))[0]
    d = torch.load(p, map_location="cpu", weights_only=False)
    for k in [
        "frame", "valid", "num_variants", "num_valid_pixels",
        "u_tta_median_px", "u_tta_mean_px", "u_tta_q90_px",
        "u_tta_q95_px", "mean_shift_median_px",
    ]:
        print(k, d.get(k))
    PY

Required sanity:
- valid=True for most frames;
- num_variants=5;
- num_valid_pixels is comfortably above 500;
- u_TTA statistics are finite and non-negative;
- no change is made to the identity flow used by baseline tracking.

## Step 2: run box2 and box3

    python slam.py       --config configs/rgbd/bonn/placing_box2_m3b_flow.yaml       --eval --dynamic       --exp_name m3b_flow_box2       --save_results 0       --seed 0

    python slam.py       --config configs/rgbd/bonn/placing_box3_m3b_flow.yaml       --eval --dynamic       --exp_name m3b_flow_box3       --save_results 0       --seed 0

Record the exact three run directories.

## Step 3: generate matched relative-pose CSVs

Box1:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX1_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box       --dystart 241       --output results/m3b_box1_relative_reliability.json

Box2:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX2_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box2       --dystart 262       --output results/m3b_box2_relative_reliability.json

Box3:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX3_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box3       --dystart 348       --output results/m3b_box3_relative_reliability.json

## Step 4: beyond-FB incremental audit

    python scripts/audit_m3b_flow_incremental.py       --sequence         box1=<BOX1_RUN>/m3b_flow_perturbation,results/m3b_box1_relative_reliability.csv         box2=<BOX2_RUN>/m3b_flow_perturbation,results/m3b_box2_relative_reliability.csv         box3=<BOX3_RUN>/m3b_flow_perturbation,results/m3b_box3_relative_reliability.csv       --block-len 20       --bootstrap 1000       --seed 0       --ridge-lambda 0.001       --output results/m3b_flow_incremental.json

Primary outputs:
- TTA/error raw Spearman;
- FB/error raw Spearman;
- TTA-vs-FB Spearman;
- partial Spearman rho(TTA,error | FB);
- LOSO rho(FB,error);
- LOSO rho(FB+TTA,error);
- LOSO delta-rho;
- macro delta-rho.

## Decision rule

Continue only if:
- macro LOSO delta-rho is approximately +0.03 to +0.05 or larger;
- at least 2/3 held-out sequences have positive delta-rho;
- the effect is not isolated to one target or one sequence.

If the result is approximately zero or negative, stop M3-B without tuning the
photometric transforms on these held-out sequences.

## Stage-completion document

After the audit, commit:

    docs/m3b_flow_perturbation_results.md

Record all per-sequence and LOSO values, pass/fail decision, exact run
directories, seed, and next action.  Commit the result even if negative.
