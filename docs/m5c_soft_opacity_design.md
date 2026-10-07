# M5-C: reliability-aware soft Gaussian initialization

Status: rapid-development design frozen before M5-C outcomes.

## 1. Motivation

M4-B confirmed direct-flow magnitude as a local pose-reliability cue.

M5-A continuous RGB-D mapping weighting produced mixed single-sequence results.
M5-B hard Gaussian-insertion rejection on balloon2 rejected 50% of optional
insertions but only caused a modest downstream change, with a weakly negative
direction.

This suggests that low-reliability frames may still contain useful scene
coverage and should not necessarily be discarded wholesale.

M5-C therefore preserves every baseline insertion request and only changes the
initial trust assigned to newly inserted Gaussians.

## 2. Rapid-development protocol

To reduce experiment cost, M5-C development uses only:

    rgbd_bonn_balloon2

Groups:

    shadow
    soft_opacity

No baseline rerun is required for rapid development because the primary causal
comparison is soft_opacity vs shadow; both compute the same M5 reliability
source.

If M5-C shows a practically meaningful improvement on balloon2, freeze it and
validate on a small external set:

    1 unseen Bonn sequence
    1 TUM sequence.

If balloon2 shows no meaningful benefit, stop M5-C without a multi-sequence
sweep.

## 3. Frozen reliability source

Use the already frozen development-only ECDF:

    results/m5_direct_flow_reference.json

Runtime confidence:

    c_k = max(1 - ECDF_train(direct_flow_median_px), 1e-3).

No M5-C run may rebuild this reference.

## 4. Frozen soft-opacity rule

The baseline Gaussian initial opacity is:

    alpha_base = 0.5.

For an ordinary optional insertion with a valid M5 score:

    alpha_0,k =
        0.5 * min(1, c_k / 0.5)

which simplifies to:

    alpha_0,k = min(0.5, c_k).

Examples:

    c >= 0.5 -> alpha_0 = 0.5
    c = 0.4  -> alpha_0 = 0.4
    c = 0.2  -> alpha_0 = 0.2
    c = 0.05 -> alpha_0 = 0.05

The rule has no tuned exponent or temperature.

High-reliability frames are never initialized with opacity above baseline.

## 5. Guardrails

Baseline opacity 0.5 is retained for:

- initialization calls (init=True);
- dynamic-object initialization (add_dygs=True);
- invalid or missing M5 score;
- any run with m5_soft_opacity=false.

M5-C does not reject an insertion.

## 6. Intervention isolation

M5-C does not change:

- tracking;
- pose estimation;
- keyframe selection;
- add_new_gaussian decisions;
- Gaussian point locations;
- Gaussian scales;
- Gaussian rotations;
- colors/features;
- motion masks;
- mapping loss coefficients;
- densification/pruning logic.

Only the initial opacity of newly inserted Gaussians is changed.

## 7. Development comparison

Primary:

    soft_opacity vs shadow

Metrics:

- ATE;
- PSNR;
- SSIM;
- LPIPS;
- L1 depth.

Also record the actual opacity initialization distribution.

## 8. Rapid-development decision

M5-C is worth external validation only if balloon2 shows a clear practically
useful benefit, not a tiny fluctuation at the scale already seen between runs.

A reasonable screening signal is:
- ATE improves by roughly 5% or more vs shadow, or
- a coherent rendering/depth improvement appears without ATE degradation.

This is a development heuristic, not a final statistical claim.

If the change is near zero or directionally negative, stop M5-C.

Do not tune:
- opacity floor;
- exponent;
- 0.5 pivot;
- nonlinear mapping

on balloon2 after seeing the result.
