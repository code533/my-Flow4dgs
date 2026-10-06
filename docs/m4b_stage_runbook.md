# M4-B stage runbook

Status: ready for confirmatory execution.

## Goal

Validate the frozen direct-flow reliability cue on fresh Bonn sequences that were
not used in box1/box2/box3 discovery.

## Branch

    feature/m4b-fresh-validation

## Frozen fresh sequences and windows

    balloon:
        config  configs/rgbd/bonn/ballon_m4b_fresh.yaml
        window  [2,62]

    remove_box:
        config  configs/rgbd/bonn/remove_box_m4b_fresh.yaml
        window  [140,200]

    synchronous2:
        config  configs/rgbd/bonn/synchronous2_m4b_fresh.yaml
        window  [90,150]

Do not change these after seeing results.

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m4b-fresh-validation
    git pull

    python -m py_compile       scripts/build_m4b_confirmatory_table.py       scripts/audit_m4b_fresh_confirmatory.py       utils/m3c_temporal_cycle.py       utils/slam_frontend.py

## Step 1: run balloon

    python slam.py       --config configs/rgbd/bonn/ballon_m4b_fresh.yaml       --eval --dynamic       --exp_name m4b_fresh_balloon       --save_results 0       --seed 0

Expected diagnostic directories:

    m1_pose_uncertainty/
    m2a_pose_uncertainty/
    m3c_temporal_cycle/

M3-C is used only to preserve the exact direct_flow_median_px definition.

## Step 2: run remove_box

    python slam.py       --config configs/rgbd/bonn/remove_box_m4b_fresh.yaml       --eval --dynamic       --exp_name m4b_fresh_remove_box       --save_results 0       --seed 0

## Step 3: run synchronous2

    python slam.py       --config configs/rgbd/bonn/synchronous2_m4b_fresh.yaml       --eval --dynamic       --exp_name m4b_fresh_synchronous2       --save_results 0       --seed 0

Record the exact three timestamped run directories.

Do not select alternative runs based on outcome.

## Step 4: sanity checks

For each fresh run:

    find <RUN>/m3c_temporal_cycle -name '*.pt' | wc -l

Approximately 61 valid diagnostic files are expected.

A simple payload check:

    python - <<'PY'
    import glob, torch
    p=sorted(glob.glob("<RUN>/m3c_temporal_cycle/*.pt"))[0]
    d=torch.load(p,map_location="cpu",weights_only=False)
    print("frame",d["frame"])
    print("valid",d["valid"])
    print("num_valid_pixels",d["num_valid_pixels"])
    print("direct_flow_median_px",d["direct_flow_median_px"])
    PY

Do not inspect pose-error correlations yet.

## Step 5: build the development confirmatory table

Use the exact three M3-C development runs already used for M4 discovery:

    python scripts/build_m4b_confirmatory_table.py       --run         box1=<BOX1_M3C_RUN>         box2=<BOX2_M3C_RUN>         box3=<BOX3_M3C_RUN>       --output results/m4b_development_table.csv

Expected: approximately 61 rows per sequence.

This table defines the coefficient-fitting set only.

## Step 6: build the fresh confirmatory table

    python scripts/build_m4b_confirmatory_table.py       --run         balloon=<BALLOON_RUN>         remove_box=<REMOVE_BOX_RUN>         synchronous2=<SYNCHRONOUS2_RUN>       --output results/m4b_fresh_table.csv

Expected: approximately 61 rows per sequence.

## Step 7: run the frozen confirmatory audit

    python scripts/audit_m4b_fresh_confirmatory.py       --development results/m4b_development_table.csv       --fresh results/m4b_fresh_table.csv       --ridge-lambda 0.001       --block-len 20       --bootstrap 1000       --seed 0       --output results/m4b_fresh_confirmatory.json

The script fits model coefficients only on box1/box2/box3 and applies them to
fresh sequences without refitting.

Comparator:

    M0 = FB + translation motion + rotation motion

Candidate:

    M1 = FB + translation motion + rotation motion + direct flow

Primary quantity:

    delta = rho(M1,error) - rho(M0,error)

## Frozen pass/fail gate

Pass if:

- macro delta >= +0.05 for at least one target;
- positive delta on at least 2/3 fresh sequences for that target;
- the other target does not have macro delta < -0.05;
- success does not depend on a single fresh sequence.

Do not alter the sequence set, windows, signal definition, ridge lambda,
bootstrap settings, or gate after inspecting fresh outcomes.

## Step 8: stage-completion document

After the final audit, commit:

    docs/m4b_fresh_validation_results.md

Record:
- exact run directories;
- seed;
- row counts;
- per-sequence delta and bootstrap intervals;
- macro translation/rotation delta;
- frozen gate result;
- final decision.

Commit the document whether M4-B passes or fails.
