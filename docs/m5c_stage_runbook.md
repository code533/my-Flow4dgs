# M5-C rapid-development runbook

Status: ready for balloon2-only screening.

## Branch

    feature/m5c-soft-opacity

## Goal

Test whether reducing the initial opacity of Gaussians inserted from
low-reliability frames is more useful than M5-B hard insertion rejection.

Only balloon2 is used for rapid development.

## Frozen soft-opacity rule

    alpha_0 = min(0.5, confidence)

for ordinary optional insertions with a valid M5 score.

Baseline alpha 0.5 remains for:
- init=True;
- add_dygs=True;
- invalid/missing M5 score.

No insertion is rejected.

## Step 0: checkout and syntax check

    git fetch
    git checkout feature/m5c-soft-opacity
    git pull

    python -m py_compile       gaussian_splatting/scene/gaussian_model.py       utils/slam_backend.py       scripts/summarize_m5c_opacity.py

Ensure the frozen reference exists:

    ls -l results/m5_direct_flow_reference.json

## Step 1: shadow run

    python slam.py       --config configs/rgbd/bonn/ballon2_m5c_shadow.yaml       --eval --dynamic       --exp_name m5c_balloon2_shadow       --save_results 0       --seed 0

## Step 2: soft-opacity run

    python slam.py       --config configs/rgbd/bonn/ballon2_m5c_soft_opacity.yaml       --eval --dynamic       --exp_name m5c_balloon2_soft_opacity       --save_results 0       --seed 0

The soft run should create:

    <RUN>/m5c_opacity_initialization.csv

Summarize it with:

    python scripts/summarize_m5c_opacity.py       <SOFT_RUN>/m5c_opacity_initialization.csv

Mechanism sanity:
- m5c_applied_rows > 0;
- applied alpha values are <= 0.5;
- at least some applied alpha values are < 0.5;
- init/dynamic-init rows retain 0.5.

## Step 3: rapid-development comparison

Primary:

    soft_opacity vs shadow

Record:
- ATE;
- PSNR;
- SSIM;
- LPIPS;
- L1 depth.

No baseline rerun is required.

## Screening decision

M5-C is worth external validation only if balloon2 shows a practically useful
benefit, such as roughly >=5% ATE improvement without rendering/depth
degradation, or a coherent rendering/depth gain without ATE degradation.

If the change is near zero or negative:
- stop M5-C;
- do not tune opacity floor, exponent, pivot, or nonlinear mapping on balloon2.

If promising:
- freeze the rule;
- validate on one untouched Bonn sequence and one TUM sequence.

## Stage result document

After the two runs, commit:

    docs/m5c_soft_opacity_results.md
