# M4-A2 result: nested direct-flow ablation

Status: **DIRECT FLOW MAIN EFFECT SUPPORTED ON DEVELOPMENT SET; REGIME-CONDITIONED CYCLE HYPOTHESIS REJECTED**

Date: 2026-10-06

Branch:

    feature/m4-regime-analysis

Primary audit:

    scripts/audit_m4a2_direct_flow_nested.py

Development set only:

    Bonn box1 / box2 / box3

These sequences were already used to motivate M4 and therefore cannot provide
confirmatory validation.

## Frozen nested models

    M0 = FB
    M1 = FB + CYCLE
    MZ = FB + Z
    MA = FB + CYCLE + Z
    MI = FB + CYCLE + Z + CYCLE*Z

with

    Z = direct_flow_median_px.

## Translation

Held out box1:

    M0 = -0.0048
    M1 = -0.0068
    MZ = +0.4837
    MA = +0.4687
    MI = +0.4341

    delta Z vs FB              = +0.4885
    delta cycle given Z        = -0.0149
    delta interaction vs add   = -0.0346
    beta interaction           = +0.2899

Held out box2:

    M0 = +0.2995
    M1 = +0.2299
    MZ = +0.3050
    MA = +0.3045
    MI = +0.3048

    delta Z vs FB              = +0.0054
    delta cycle given Z        = -0.0005
    delta interaction vs add   = +0.0003
    beta interaction           = -0.0877

Held out box3:

    M0 = +0.1780
    M1 = +0.3098
    MZ = +0.5057
    MA = +0.4749
    MI = +0.4728

    delta Z vs FB              = +0.3277
    delta cycle given Z        = -0.0308
    delta interaction vs add   = -0.0021
    beta interaction           = +0.0364

Summary:

    delta Z vs FB:
        mean     = +0.2739
        positive = 3/3

    delta cycle given Z:
        mean     = -0.0154
        positive = 0/3

    delta additive vs FB:
        mean     = +0.2585
        positive = 3/3

    delta interaction vs additive:
        mean     = -0.0122
        positive = 1/3

    delta interaction vs FB:
        mean     = +0.2463
        positive = 3/3

    interaction beta:
        mean     = +0.0795
        sign +/- = 2/1

## Rotation

Held out box1:

    M0 = +0.1051
    M1 = +0.0901
    MZ = +0.6628
    MA = +0.6566
    MI = +0.6525

    delta Z vs FB              = +0.5577
    delta cycle given Z        = -0.0062
    delta interaction vs add   = -0.0041
    beta interaction           = +0.2505

Held out box2:

    M0 = +0.2799
    M1 = +0.1756
    MZ = +0.3741
    MA = +0.3651
    MI = +0.3575

    delta Z vs FB              = +0.0943
    delta cycle given Z        = -0.0090
    delta interaction vs add   = -0.0076
    beta interaction           = +0.0577

Held out box3:

    M0 = +0.2716
    M1 = +0.3957
    MZ = +0.6888
    MA = +0.6215
    MI = +0.6238

    delta Z vs FB              = +0.4172
    delta cycle given Z        = -0.0673
    delta interaction vs add   = +0.0024
    beta interaction           = +0.0960

Summary:

    delta Z vs FB:
        mean     = +0.3564
        positive = 3/3

    delta cycle given Z:
        mean     = -0.0275
        positive = 0/3

    delta additive vs FB:
        mean     = +0.3289
        positive = 3/3

    delta interaction vs additive:
        mean     = -0.0031
        positive = 1/3

    delta interaction vs FB:
        mean     = +0.3258
        positive = 3/3

    interaction beta:
        mean     = +0.1347
        sign +/- = 3/0

## Main conclusion

The nested ablation rejects the initial regime-conditioned-cycle
interpretation.

The development-set improvement is almost entirely explained by the direct
flow magnitude main effect:

    FB + direct_flow_median_px

strongly outperforms FB alone.

Once direct flow magnitude is known, adding temporal-cycle inconsistency does
not help:

    translation:
        delta cycle given Z = -0.0154, positive 0/3

    rotation:
        delta cycle given Z = -0.0275, positive 0/3.

The explicit interaction term also provides no stable incremental value:

    translation:
        delta interaction vs additive = -0.0122

    rotation:
        delta interaction vs additive = -0.0031.

Therefore the correct development-set finding is:

> Direct optical-flow magnitude is a strong relative-pose reliability cue in
> these sequences; temporal-cycle inconsistency adds no incremental value once
> flow magnitude is included.

Do not describe this result as regime-conditioned cycle uncertainty.

## Important confound before fresh validation

The targets are absolute relative-pose errors in meters and radians.

Direct flow magnitude is strongly related to the magnitude of inter-frame
motion.  Larger true or estimated camera motion may mechanically produce larger
absolute errors even if relative estimation quality is unchanged.

Therefore the current result may reflect:

1. a genuine runtime difficulty/reliability cue;
2. a trivial motion-scale effect;
3. dynamic-object optical flow rather than camera-motion difficulty;
4. a mixture of the above.

Before treating direct_flow_median_px as an uncertainty/reliability signal, a
motion-magnitude confound audit is required.

## Required next audit

M4-A3 should test whether direct flow remains useful after controlling for the
magnitude of the baseline relative pose increment.

Suggested controls:

    ||t_rel||
    rotation_angle(T_rel)

and normalized error targets:

    error_t / (||t_rel|| + eps)
    error_r / (rotation_angle + eps).

Primary questions:

1. Does direct_flow_median_px retain partial rank association with absolute
   pose error after controlling baseline motion magnitude?

2. Does direct flow predict normalized relative error?

3. In LOSO models, does FB + pose-motion-magnitude + direct-flow still improve
   over FB + pose-motion-magnitude?

Only after passing this audit should the direct-flow cue be frozen for fresh
sequence validation.

## Development-only warning

box1/box2/box3 cannot confirm any resulting rule.  M4-A3 remains
hypothesis-generation / confound analysis.
