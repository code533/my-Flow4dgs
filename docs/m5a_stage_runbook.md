# M5-A stage runbook

Status: ready for first runtime execution.

## Goal

Test whether the fresh-confirmed direct-flow reliability cue improves Gaussian
mapping when used only to reweight per-view RGB-D mapping loss.

## Branch

    feature/m5-flow-reliability-mapping

## Frozen runtime score

Development-only direct-flow ECDF:

    q = ECDF_train(direct_flow_median_px)

Reliability confidence:

    c = max(1 - q, 1e-3)

Invalid / t<2 neutral confidence:

    c = 0.5

Mapping-window weights:

    w = c / mean(c)

then clip to:

    [0.25, 4.0]

and renormalize to mean one.

Do not change these values after seeing M5-A outcomes.

## Frozen sequences

1. balloon2
2. moving_nonobstructing_box2
3. removing_nonobstructing_box

Initial seed:

    0

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m5-flow-reliability-mapping
    git pull

    python -m py_compile       utils/m5_flow_reliability.py       scripts/build_m5_flow_reference.py       utils/slam_frontend.py       utils/slam_backend.py       utils/camera_utils.py

## Step 1: build the frozen development ECDF reference

Use the already frozen M4-B development table:

    results/m4b_development_table.csv

Run:

    python scripts/build_m5_flow_reference.py       results/m4b_development_table.csv       --output results/m5_direct_flow_reference.json

Expected development sequences:

    box1 + box2 + box3

Do not rebuild this file from any M5 evaluation sequence.

## Step 2: first smoke test — balloon2 shadow

Run shadow first because it computes exactly the M5 score but does not alter
mapping weights:

    python slam.py       --config configs/rgbd/bonn/ballon2_m5a_shadow.yaml       --eval --dynamic       --exp_name m5a_balloon2_shadow       --save_results 0       --seed 0

The run should create:

    <RUN>/m5_flow_reliability/

Starting from frame 2.

Check count:

    find <RUN>/m5_flow_reliability -name '*.pt' | wc -l

Inspect one payload:

    python - <<'PY'
    import glob, torch
    p = sorted(glob.glob("<RUN>/m5_flow_reliability/*.pt"))[0]
    d = torch.load(p, map_location="cpu", weights_only=False)
    for k in [
        "frame",
        "valid",
        "num_valid_pixels",
        "direct_flow_median_px",
        "training_ecdf",
        "confidence",
        "reference_file",
    ]:
        print(k, d.get(k))
    PY

Required sanity:
- valid=True for most frames;
- direct_flow_median_px finite and non-negative;
- training_ecdf in [0,1];
- confidence in [0.001,1];
- confidence decreases when direct_flow_median_px increases.

## Step 3: paired balloon2 baseline and weighted runs

Baseline:

    python slam.py       --config configs/rgbd/bonn/ballon2_m5a_baseline.yaml       --eval --dynamic       --exp_name m5a_balloon2_baseline       --save_results 0       --seed 0

Weighted:

    python slam.py       --config configs/rgbd/bonn/ballon2_m5a_weighted.yaml       --eval --dynamic       --exp_name m5a_balloon2_weighted       --save_results 0       --seed 0 2>&1 | tee results/m5a_balloon2_weighted.log

The weighted log should contain lines:

    M5 RGB-D weights frame:weight, ...

The weights should not all equal 1, but their per-window mean should remain
approximately one.

Do not interpret one sequence as a final result.

## Step 4: run moving_nonobstructing_box2 triplet

Baseline:

    python slam.py       --config configs/rgbd/bonn/mov_box2_m5a_baseline.yaml       --eval --dynamic       --exp_name m5a_mov_box2_baseline       --save_results 0       --seed 0

Shadow:

    python slam.py       --config configs/rgbd/bonn/mov_box2_m5a_shadow.yaml       --eval --dynamic       --exp_name m5a_mov_box2_shadow       --save_results 0       --seed 0

Weighted:

    python slam.py       --config configs/rgbd/bonn/mov_box2_m5a_weighted.yaml       --eval --dynamic       --exp_name m5a_mov_box2_weighted       --save_results 0       --seed 0 2>&1 | tee results/m5a_mov_box2_weighted.log

## Step 5: run removing_nonobstructing_box triplet

Baseline:

    python slam.py       --config configs/rgbd/bonn/remove_box_m5a_baseline.yaml       --eval --dynamic       --exp_name m5a_remove_box_baseline       --save_results 0       --seed 0

Shadow:

    python slam.py       --config configs/rgbd/bonn/remove_box_m5a_shadow.yaml       --eval --dynamic       --exp_name m5a_remove_box_shadow       --save_results 0       --seed 0

Weighted:

    python slam.py       --config configs/rgbd/bonn/remove_box_m5a_weighted.yaml       --eval --dynamic       --exp_name m5a_remove_box_weighted       --save_results 0       --seed 0 2>&1 | tee results/m5a_remove_box_weighted.log

## Step 6: primary causal comparison

Primary comparison:

    weighted vs shadow

because both compute the same M5 score and incur the same extra flow calls.

Baseline vs shadow is used to verify that score computation itself is
behavior-neutral and to quantify runtime overhead.

Record for all nine runs:
- exact timestamped run directory;
- ATE RMSE printed/saved by repository evaluation;
- rendering metrics if available;
- total runtime;
- M5 score directory count;
- weighted-run log path.

## Frozen first-pass decision

M5-A v1 is promising only if weighted vs shadow improves ATE RMSE on at least
2/3 predefined sequences and does not catastrophically degrade the third.

If promising, repeat the paired experiment with frozen seeds:

    0, 1, 2

before making a downstream claim.

If not promising, stop M5-A v1. Do not tune ECDF temperature, exponent, or clip
bounds on these same outcomes.

## Stage-completion record

After the first seed-0 triplets finish, commit:

    docs/m5a_flow_reliability_mapping_results.md

Include:
- reference-file provenance;
- exact run directories;
- ATE for baseline/shadow/weighted;
- weighted-vs-shadow relative changes;
- runtime;
- representative M5 weight statistics;
- pass/fail decision.
