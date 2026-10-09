# M6-A rapid Flow4DGS screening

Status: ready for balloon2-only screening.

## Goal

Use Flow4DGS as the fast development platform for M6-A because it is
substantially cheaper to run than my-4DGS-SLAM.

M6-A tests whether the already confirmed direct-flow reliability cue is useful
when applied directly to pose tracking rather than map construction.

## Frozen intervention

Low reliability:

    confidence < 0.20

receives:

    20 extra pose-only photometric tracking iterations

after the unchanged baseline tracking loop.

Exposure is frozen in the extra stage.

No map-side M5 intervention is active.

## Groups

Only two runs:

    shadow
    refine

Both compute the same M5 reliability path.

Primary comparison:

    refine vs shadow

No baseline rerun is required for this rapid screen.

## Sequence

    rgbd_bonn_balloon2

This is a development sequence.  It is not an untouched confirmation set for
M6-A.

## Run

Shadow:

    python slam.py \
      --config configs/rgbd/bonn/ballon2_m6a_shadow.yaml \
      --eval --dynamic \
      --exp_name m6a_balloon2_shadow \
      --save_results 0 \
      --seed 0

Refine:

    python slam.py \
      --config configs/rgbd/bonn/ballon2_m6a_refine.yaml \
      --eval --dynamic \
      --exp_name m6a_balloon2_refine \
      --save_results 0 \
      --seed 0

Mechanism summary:

    python scripts/summarize_m6a_refinement.py \
      <RUN>/m6a_pose_refinement.csv

## Mechanism checks

Shadow:
- triggered_frames = 0.

Refine:
- triggered_frames > 0;
- every trigger has confidence < 0.20;
- every trigger has extra_iters = 20;
- at least some triggered frames have non-zero extra pose change.

## Decision

Primary metric:

    ATE

Secondary:
- PSNR;
- SSIM;
- LPIPS;
- L1 depth;
- runtime.

If refine does not produce a practically meaningful ATE improvement over
shadow, stop M6-A v1 without tuning the threshold or iteration count on
balloon2.

If promising, freeze M6-A and move to an untouched confirmation sequence.
