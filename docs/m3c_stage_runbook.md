# M3-C stage runbook

Status: ready for first execution.

## Goal

Test whether three-frame temporal-cycle inconsistency contains transferable
relative-pose reliability information beyond pairwise FB consistency.

M3-C is shadow-only and does not alter Flow4DGS behavior.

## Branch

    feature/m3c-temporal-cycle

Base:

    feature/m3b-flow-perturbation

## Fixed temporal signal

For frames t, t-1, t-2:

    F10 = F(t -> t-1)
    F21 = F(t-1 -> t-2)
    F20 = F(t -> t-2)

Compose:

    Fcomp(p) = F10(p) + F21(p + F10(p))

Primary signal:

    u_cycle = median ||F20 - Fcomp||

over baseline-static, FB-valid, and temporal-warp-valid pixels.

Do not change the temporal baseline or summary statistic after inspecting
held-out results.

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m3c-temporal-cycle
    git pull

    python -m py_compile       utils/m3c_temporal_cycle.py       scripts/audit_m3c_cycle_incremental.py       utils/slam_frontend.py

## Step 1: box1 smoke run

    python slam.py       --config configs/rgbd/bonn/placing_box_m3c_cycle.yaml       --eval --dynamic       --exp_name m3c_cycle_box1       --save_results 0       --seed 0

The M3-C directory appears at the first audited frame (211), not at startup:

    <BOX1_RUN>/m3c_temporal_cycle/

Expected file count for [211,271]: approximately 61.

Check:

    find <BOX1_RUN>/m3c_temporal_cycle -name '*.pt' | wc -l

Inspect one payload:

    python - <<'PY'
    import glob, torch
    p = sorted(glob.glob("<BOX1_RUN>/m3c_temporal_cycle/*.pt"))[0]
    d = torch.load(p, map_location="cpu", weights_only=False)
    for k in [
        "frame", "valid", "num_valid_pixels",
        "u_cycle_median_px", "u_cycle_mean_px",
        "u_cycle_q90_px", "u_cycle_q95_px",
        "direct_flow_median_px", "composed_flow_median_px",
    ]:
        print(k, d.get(k))
    PY

Required sanity:
- valid=True for most audited frames;
- num_valid_pixels comfortably above 500;
- cycle statistics finite and non-negative;
- direct/composed flow magnitudes are finite and plausibly similar in scale.

## Step 2: summarize box1 temporal variation

    python - <<'PY'
    import glob, torch, numpy as np
    files = sorted(glob.glob("<BOX1_RUN>/m3c_temporal_cycle/*.pt"))
    rows = []
    for p in files:
        d = torch.load(p, map_location="cpu", weights_only=False)
        if d.get("valid", False):
            rows.append(d)
    print("files:", len(files))
    print("valid:", len(rows))
    for key in [
        "num_valid_pixels",
        "u_cycle_median_px",
        "u_cycle_mean_px",
        "u_cycle_q90_px",
        "u_cycle_q95_px",
        "direct_flow_median_px",
        "composed_flow_median_px",
    ]:
        x = np.asarray([float(d[key]) for d in rows])
        print(
            key,
            "min", x.min(),
            "median", np.median(x),
            "max", x.max(),
            "std", x.std(),
        )
    PY

Do not continue if the signal is numerically degenerate or most frames are
invalid.

## Step 3: run box2 and box3

    python slam.py       --config configs/rgbd/bonn/placing_box2_m3c_cycle.yaml       --eval --dynamic       --exp_name m3c_cycle_box2       --save_results 0       --seed 0

    python slam.py       --config configs/rgbd/bonn/placing_box3_m3c_cycle.yaml       --eval --dynamic       --exp_name m3c_cycle_box3       --save_results 0       --seed 0

Record exact run directories.

## Step 4: generate matched relative-pose CSVs

Box1:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX1_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box       --dystart 241       --output results/m3c_box1_relative_reliability.json

Box2:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX2_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box2       --dystart 262       --output results/m3c_box2_relative_reliability.json

Box3:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX3_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box3       --dystart 348       --output results/m3c_box3_relative_reliability.json

## Step 5: beyond-FB incremental audit

    python scripts/audit_m3c_cycle_incremental.py       --sequence         box1=<BOX1_RUN>/m3c_temporal_cycle,results/m3c_box1_relative_reliability.csv         box2=<BOX2_RUN>/m3c_temporal_cycle,results/m3c_box2_relative_reliability.csv         box3=<BOX3_RUN>/m3c_temporal_cycle,results/m3c_box3_relative_reliability.csv       --block-len 20       --bootstrap 1000       --seed 0       --ridge-lambda 0.001       --output results/m3c_cycle_incremental.json

Primary outputs:
- cycle/error raw Spearman;
- FB/error raw Spearman;
- cycle-vs-FB Spearman;
- partial Spearman rho(cycle,error | FB);
- LOSO rho(FB,error);
- LOSO rho(FB+cycle,error);
- LOSO delta-rho;
- macro delta-rho.

## Decision rule

Continue only if:
- macro LOSO delta-rho is approximately +0.03 to +0.05 or larger;
- at least 2/3 held-out sequences have positive delta-rho;
- the effect is not isolated to one target or sequence.

If M3-C fails, stop this route without tuning the temporal baseline on these
held-out sequences.

## Stage-completion document

After the audit, commit:

    docs/m3c_temporal_cycle_results.md

Record exact run directories, seed, sanity checks, all per-sequence and LOSO
values, the fixed gate decision, and next action.
