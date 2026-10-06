# M5-A interim result: balloon2, seed 0

Status: **INTERIM — do not make a stage-level pass/fail decision yet**

Date: 2026-10-07

Branch:

    feature/m5-flow-reliability-mapping

Sequence:

    rgbd_bonn_balloon2

Seed:

    0

Compared runs:

    baseline
    shadow
    weighted

The M5-A design pre-specified weighted vs shadow as the primary causal
comparison because shadow and weighted both execute the same extra direct-flow
reliability computation.

## Reported metrics

| run | ATE | PSNR | SSIM | LPIPS | L1 depth |
|---|---:|---:|---:|---:|---:|
| baseline | 0.04837 | 28.1573 | 0.8763 | 0.2017 | 0.05318 |
| shadow | 0.04355 | 28.1591 | 0.8762 | 0.2015 | 0.05295 |
| weighted | 0.05262 | 28.0282 | 0.8758 | 0.2017 | 0.05319 |

## Primary comparison: weighted vs shadow

ATE:

    absolute change = +0.00907
    relative change = +20.83%

Higher ATE is worse, so M5-A weighting degrades balloon2 trajectory accuracy
at seed 0.

Rendering/depth differences are smaller:

    PSNR       = -0.1309 dB
    SSIM       = -0.0004
    LPIPS      = +0.0002
    L1 depth   = +0.00024

All directions are weakly worse for weighted vs shadow.

## Baseline vs shadow sanity

ATE:

    baseline = 0.04837
    shadow   = 0.04355
    relative change = -9.96%

Rendering/depth metrics are nearly identical.

This means the baseline and shadow trajectories are not numerically identical
at seed 0 even though the M5 score path is intended to be behavior-neutral.

Possible reasons include multiprocessing / execution-schedule sensitivity and
GPU numerical nondeterminism introduced by the extra diagnostic computation.
This does not invalidate the pre-specified weighted-vs-shadow comparison, but it
does mean that a single seed should not be over-interpreted.

## Interim interpretation

For balloon2 seed 0:

    weighted vs shadow = negative

and the ATE degradation is not negligible in relative terms.

However, the frozen M5-A first-pass stop rule is sequence-level:

- improve ATE on at least 2/3 predefined sequences;
- no catastrophic degradation on the remaining sequence.

Therefore balloon2 alone cannot decide the M5-A stage.

Do not tune:
- ECDF transform;
- confidence exponent;
- clip bounds;
- sequence selection

after this result.

Proceed unchanged to:

    moving_nonobstructing_box2
    removing_nonobstructing_box

with the same seed and frozen configs.

## Follow-up guardrail

If the three-sequence seed-0 result is mixed or borderline, repeat the paired
shadow/weighted experiment with the already pre-declared seeds 0,1,2 before
making a downstream claim.

If weighted is worse on at least 2/3 predefined sequences at seed 0, M5-A v1
fails the frozen first-pass criterion and should stop without transform tuning
on these sequences.
