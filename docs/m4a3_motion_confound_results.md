# M4-A3 result: direct-flow motion-confound audit

Status: **DIRECT FLOW SURVIVES MOTION-MAGNITUDE CONTROL ON DEVELOPMENT SET**

Date: 2026-10-06

Branch:

    feature/m4-regime-analysis

Primary audit:

    scripts/audit_m4a3_motion_confound.py

Development set only:

    Bonn box1 / box2 / box3

These sequences were already used to motivate M4 and therefore remain
hypothesis-generation data, not confirmatory validation.

## Purpose

M4-A2 showed that the strong development-set gain came from the main effect of

    direct_flow_median_px

rather than temporal-cycle inconsistency or a cycle*flow interaction.

A major confound remained possible:

    larger flow
      -> larger inter-frame motion
      -> larger absolute translation/rotation error.

M4-A3 therefore controls the actually applied baseline relative-motion
magnitude recovered from M1 diagnostics:

    ||t_rel||
    angle(R_rel).

It asks whether direct flow still carries reliability information after
conditioning on FB consistency and pose-motion magnitude.

## Within-sequence results

### box1, n=61

Association with motion magnitude:

    flow ~ ||t_rel||        = +0.6472
    flow ~ rotation angle   = +0.1608

Partial association with absolute error after controlling FB + motion:

    translation error       = +0.4691
    rotation error          = +0.6347

Association with normalized error:

    flow ~ normalized t err = +0.3141
    flow ~ normalized r err = +0.4925

### box2, n=61

Association with motion magnitude:

    flow ~ ||t_rel||        = -0.0487
    flow ~ rotation angle   = +0.1433

Partial association with absolute error after controlling FB + motion:

    translation error       = +0.2052
    rotation error          = +0.2782

Association with normalized error:

    flow ~ normalized t err = +0.3194
    flow ~ normalized r err = +0.0629

### box3, n=61

Association with motion magnitude:

    flow ~ ||t_rel||        = -0.1605
    flow ~ rotation angle   = +0.4149

Partial association with absolute error after controlling FB + motion:

    translation error       = +0.4771
    rotation error          = +0.6763

Association with normalized error:

    flow ~ normalized t err = +0.5791
    flow ~ normalized r err = -0.0158

## LOSO incremental result after motion controls

### Translation

Held out box1:

    FB + motion             = -0.0687
    FB + motion + flow      = +0.3800
    delta                   = +0.4487

Held out box2:

    FB + motion             = +0.2107
    FB + motion + flow      = +0.3166
    delta                   = +0.1059

Held out box3:

    FB + motion             = +0.2480
    FB + motion + flow      = +0.5260
    delta                   = +0.2781

Macro:

    mean delta              = +0.2775
    positive folds          = 3/3

### Rotation

Held out box1:

    FB + motion             = +0.0955
    FB + motion + flow      = +0.6483
    delta                   = +0.5528

Held out box2:

    FB + motion             = +0.2595
    FB + motion + flow      = +0.3784
    delta                   = +0.1189

Held out box3:

    FB + motion             = +0.3188
    FB + motion + flow      = +0.6949
    delta                   = +0.3762

Macro:

    mean delta              = +0.3493
    positive folds          = 3/3

## Main conclusion

The development-set direct-flow reliability effect is not explained by a simple
inter-frame motion-magnitude confound.

Evidence:

1. direct flow remains positively associated with absolute pose error after
   conditioning on FB, applied translation magnitude, and applied rotation
   magnitude in all three sequences for both translation and rotation;

2. direct flow retains useful association with normalized error, especially
   translation error;

3. most importantly, LOSO rank prediction improves strongly when direct flow is
   added on top of FB + motion controls:

       translation macro delta = +0.2775, positive 3/3
       rotation macro delta    = +0.3493, positive 3/3.

This is substantially larger and more consistent than the M1/M3 uncertainty
signals tested earlier.

## What this does and does not establish

Supported on the development set:

> direct optical-flow magnitude is a strong runtime reliability cue beyond FB
> consistency and beyond the magnitude of the applied camera-motion increment.

Not yet supported:

> direct-flow magnitude generalizes as a reliability cue to unseen dynamic
> sequences.

Because box1/box2/box3 were used to discover this cue, the next stage must be a
strict confirmatory test on fresh sequences.

## Frozen confirmatory model

The simplest candidate to freeze is:

    error_rank ~
        FB_rank
        + translation-motion-rank
        + rotation-motion-rank
        + direct-flow-rank.

No cycle term and no interaction term should be included.

The comparator is:

    error_rank ~
        FB_rank
        + translation-motion-rank
        + rotation-motion-rank.

Primary confirmatory metric:

    delta-rho_flow =
        rho(FB+motion+flow, error)
        -
        rho(FB+motion, error).

The direct-flow signal remains:

    direct_flow_median_px

from the M3-C direct t->t-2 flow diagnostics.

## Next stage

Proceed to **M4-B: fresh-sequence confirmatory validation**.

Requirements:

- choose dynamic Bonn sequences not used in box1/box2/box3 discovery;
- freeze all model terms before seeing their pose-error outcomes;
- run M3-C only to obtain direct_flow_median_px (cycle is no longer a candidate);
- use the same seed and matched relative-pose target construction;
- do not tune thresholds or descriptors on fresh sequences.

A positive confirmatory result would justify promoting direct-flow magnitude
from a development observation to a genuine reliability cue for later runtime
SLAM use.
