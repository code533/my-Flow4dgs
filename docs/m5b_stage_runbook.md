# M5-B stage runbook

Status: ready for first screening run.

## Goal

Test whether suppressing Gaussian insertion on very low-reliability keyframes
improves downstream SLAM behavior.

M5-B changes only optional Gaussian insertion admission.

## Branch

    feature/m5b-reliability-insertion

## Frozen reliability rule

Reference:

    results/m5_direct_flow_reference.json

Runtime confidence:

    c = max(1 - ECDF_train(direct_flow_median_px), 1e-3)

Frozen rejection rule:

    reject insertion if c < 0.20

Mandatory guardrails:

- frame 0 is always admitted;
- dystart is always admitted;
- invalid/missing M5 scores are always admitted.

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m5b-reliability-insertion
    git pull

    python -m py_compile       utils/slam_backend.py       utils/slam_frontend.py       utils/m5_flow_reliability.py       scripts/summarize_m5b_insertion.py

Ensure the frozen reference already exists:

    ls -l results/m5_direct_flow_reference.json

Do not rebuild it from M5-B runs.

## Step 1: balloon2 shadow smoke run

    python slam.py       --config configs/rgbd/bonn/ballon2_m5b_shadow.yaml       --eval --dynamic       --exp_name m5b_balloon2_shadow       --save_results 0       --seed 0

Shadow computes the exact M5 reliability source but does not gate insertion.

The run should create:

    <RUN>/m5_flow_reliability/
    <RUN>/m5b_insertion_decisions.csv

The insertion CSV should show every original insertion request as admitted with
reason gating_off, except mandatory reasons such as dystart.

## Step 2: balloon2 gated run

    python slam.py       --config configs/rgbd/bonn/ballon2_m5b_gated.yaml       --eval --dynamic       --exp_name m5b_balloon2_gated       --save_results 0       --seed 0

Then summarize:

    python scripts/summarize_m5b_insertion.py       <GATED_RUN>/m5b_insertion_decisions.csv

Required mechanism sanity:
- at least one optional insertion request should usually be rejected;
- every rejected row must have reason=low_reliability;
- every rejected row must have confidence < 0.20;
- dystart must never be rejected;
- invalid_score must never be rejected.

If rejection_fraction is 0, the sequence is uninformative for M5-B but do not
change the threshold.

If almost all requests are rejected, record the result and do not retune the
threshold on this sequence.

## Step 3: balloon2 baseline

    python slam.py       --config configs/rgbd/bonn/ballon2_m5b_baseline.yaml       --eval --dynamic       --exp_name m5b_balloon2_baseline       --save_results 0       --seed 0

Primary comparison remains:

    gated vs shadow

Baseline vs shadow measures runtime/path variation.

## Step 4: moving_nonobstructing_box2 triplet

Use the empty-point-cloud safety fix already present on this branch.

Baseline:

    python slam.py       --config configs/rgbd/bonn/mov_box2_m5b_baseline.yaml       --eval --dynamic       --exp_name m5b_mov_box2_baseline       --save_results 0       --seed 0

Shadow:

    python slam.py       --config configs/rgbd/bonn/mov_box2_m5b_shadow.yaml       --eval --dynamic       --exp_name m5b_mov_box2_shadow       --save_results 0       --seed 0

Gated:

    python slam.py       --config configs/rgbd/bonn/mov_box2_m5b_gated.yaml       --eval --dynamic       --exp_name m5b_mov_box2_gated       --save_results 0       --seed 0

Summarize the gated decisions.

## Step 5: removing_nonobstructing_box triplet

Baseline:

    python slam.py       --config configs/rgbd/bonn/remove_box_m5b_baseline.yaml       --eval --dynamic       --exp_name m5b_remove_box_baseline       --save_results 0       --seed 0

Shadow:

    python slam.py       --config configs/rgbd/bonn/remove_box_m5b_shadow.yaml       --eval --dynamic       --exp_name m5b_remove_box_shadow       --save_results 0       --seed 0

Gated:

    python slam.py       --config configs/rgbd/bonn/remove_box_m5b_gated.yaml       --eval --dynamic       --exp_name m5b_remove_box_gated       --save_results 0       --seed 0

## Step 6: collect end-task metrics

For each of the nine runs record:
- ATE;
- PSNR;
- SSIM;
- LPIPS;
- L1 depth;
- exact run directory.

For each gated run also record:
- insertion requests;
- admitted;
- rejected;
- rejection fraction;
- rejected frame IDs;
- confidence min/median/max.

## Screening interpretation

Primary comparison:

    gated vs shadow

M5-B is promising if:
- ATE improves on at least 2/3 screening sequences;
- the third sequence does not catastrophically degrade;
- gating actually rejects a non-trivial fraction of optional insertion requests.

This is only mechanism screening because balloon2/mov_box2 outcomes from M5-A
were already observed before M5-B was proposed.

If promising:
- freeze M5-B;
- fix/audit remaining stochastic point sampling;
- run seeds 0,1,2;
- validate on an untouched external set, preferably TUM.

If not promising:
- stop M5-B v1;
- do not retune the 0.20 threshold on these same sequences.

## Stage-completion record

After all seed-0 screening runs, commit:

    docs/m5b_reliability_insertion_results.md

Include both end-task metrics and actual gating statistics.
