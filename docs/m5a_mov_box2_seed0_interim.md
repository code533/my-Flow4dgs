# M5-A interim result: moving_nonobstructing_box2, seed 0

Status: **INTERIM — effect is comparable to run-to-run variation**

Date: 2026-10-07

Branch:

    feature/m5-flow-reliability-mapping

Sequence:

    rgbd_bonn_moving_nonobstructing_box2

Seed argument:

    0

## Reported metrics

| run | ATE | PSNR | SSIM | LPIPS | L1 depth |
|---|---:|---:|---:|---:|---:|
| baseline | 0.04871 | 29.7092 | 0.8951 | 0.2096 | 0.03504 |
| shadow | 0.05181 | 29.7402 | 0.8942 | 0.2121 | 0.03530 |
| weighted | 0.04806 | 29.4903 | 0.8957 | 0.2098 | 0.03455 |

## Primary weighted-vs-shadow comparison

ATE:

    shadow   = 0.05181
    weighted = 0.04806
    relative change ≈ -7.2%

Lower is better.

Compared with baseline, however:

    baseline = 0.04871
    weighted = 0.04806

which is only about a 1.3% improvement.

Rendering/depth metrics are mixed and small in magnitude.

## Interpretation

This run does not provide convincing evidence of a downstream M5-A benefit.

Together with balloon2 seed 0, where weighted degraded ATE relative to shadow,
the current pattern is consistent with an intervention effect that is small
relative to the system's execution variance.

Do not tune the ECDF transform or mapping-weight clip bounds based on this
result.

## Reproducibility caveat

The experiment accepts an explicit seed and calls seed_everything(), but the
current Gaussian point-cloud construction still contains stochastic operations
that are not fully controlled by that seed, including:

    np.random.default_rng()

without an explicit seed, and Open3D:

    random_down_sample(...)

Therefore repeated runs with the same --seed value are not guaranteed to share
identical point-sampling decisions.

This weakens single-run causal interpretation and motivates a reproducibility
audit before declaring M5-A success or failure.
