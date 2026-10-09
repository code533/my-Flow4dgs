# M6-B: reliability-aware pose correction trust region

Status: development screening.

## Motivation

M6-A showed that giving low-reliability frames 20 additional photometric pose
iterations worsened balloon2 ATE from 0.04808 to 0.06166 (+28.25%).  The
mechanism audit showed 254/467 valid frames triggered and the extra stage
actually changed pose.

This suggests low-reliability frames are not merely under-optimized.  Their
photometric correction direction may itself be unreliable.

## Frozen M6-B v1

Reliability source and trigger are unchanged:

    confidence < 0.20

Baseline photometric tracking is executed completely unchanged.

Let T_init be the exact pose entering photometric tracking and T_tracked the
baseline output.  Define the tracking correction:

    T_corr = T_tracked @ inv(T_init)

For low-reliability frames only, apply:

    T_final = scale_SE3(T_corr, 0.50) @ T_init

For all other frames:

    T_final = T_tracked

Thus M6-B shrinks only the photometric correction.  It does NOT shrink the
physical inter-frame motion or the existing optical-flow initialization.

The correction scale 0.50 is frozen for this v1 screen.  Do not tune it on
balloon2.

## Experiment

Sequence:

    rgbd_bonn_balloon2

Groups:

    configs/rgbd/bonn/ballon2_m6b_shadow.yaml
    configs/rgbd/bonn/ballon2_m6b_trust.yaml

Run shadow:

    python slam.py \
      --config configs/rgbd/bonn/ballon2_m6b_shadow.yaml \
      --eval --dynamic \
      --exp_name m6b_balloon2_shadow \
      --save_results 0 \
      --seed 0

Run trust:

    python slam.py \
      --config configs/rgbd/bonn/ballon2_m6b_trust.yaml \
      --eval --dynamic \
      --exp_name m6b_balloon2_trust \
      --save_results 0 \
      --seed 0

Summarize mechanism:

    python scripts/summarize_m6b_trust_region.py \
      <RUN>/m6b_pose_trust_region.csv

Expected trust-run sanity:
- triggered_frames > 0;
- every trigger has confidence < 0.20;
- applied_scale = 0.50;
- correction translation/rotation after trust region is smaller than before.

Primary metric:

    ATE

Secondary:
- PSNR
- SSIM
- LPIPS
- L1 depth
- runtime

## Decision

If M6-B materially improves ATE relative to its shadow run, freeze v1 and move
to an untouched sequence.

If null or worse, stop v1.  Do not tune confidence threshold or correction
scale on balloon2.
