# M4-A result: exploratory regime interaction audit

Status: **PROMISING DEVELOPMENT HYPOTHESIS — not confirmatory**

Date: 2026-10-06

Branch:

    feature/m4-regime-analysis

Primary audit:

    scripts/audit_m4_regime_interactions.py

Development set only:

    Bonn box1 / box2 / box3

These sequences were already inspected during M3-C and therefore cannot serve
as final validation for any M4 regime rule.

## Primary descriptor summary

### direct_flow_median_px

Translation:

    mean delta vs FB       = +0.2463
    positive folds         = 3/3
    mean delta vs cycle    = +0.2262
    positive folds         = 3/3
    mean interaction beta  = +0.0795
    interaction sign (+/-) = 2/1

Rotation:

    mean delta vs FB       = +0.3258
    positive folds         = 3/3
    mean delta vs cycle    = +0.3242
    positive folds         = 3/3
    mean interaction beta  = +0.1347
    interaction sign (+/-) = 3/0

This is the strongest primary candidate by a wide margin.

### valid_extent

Translation:

    mean delta vs FB       = -0.0529
    positive folds         = 1/3
    mean delta vs cycle    = -0.0730
    positive folds         = 0/3
    mean interaction beta  = +0.0538
    interaction sign (+/-) = 1/2

Rotation:

    mean delta vs FB       = -0.0624
    positive folds         = 0/3
    mean delta vs cycle    = -0.0640
    positive folds         = 1/3
    mean interaction beta  = +0.0608
    interaction sign (+/-) = 1/2

Conclusion: reject as primary regime candidate.

### log10_condition

Translation:

    mean delta vs FB       = -0.1610
    positive folds         = 0/3
    mean delta vs cycle    = -0.1811
    positive folds         = 0/3
    mean interaction beta  = -0.0577
    interaction sign (+/-) = 1/2

Rotation:

    mean delta vs FB       = -0.1698
    positive folds         = 0/3
    mean delta vs cycle    = -0.1714
    positive folds         = 0/3
    mean interaction beta  = -0.3096
    interaction sign (+/-) = 1/2

Conclusion: reject as primary regime candidate.

### motion_scale_joint

Translation:

    mean delta vs FB       = -0.0996
    positive folds         = 0/3
    mean delta vs cycle    = -0.1197
    positive folds         = 0/3
    mean interaction beta  = -0.1018
    interaction sign (+/-) = 1/2

Rotation:

    mean delta vs FB       = -0.1256
    positive folds         = 0/3
    mean delta vs cycle    = -0.1272
    positive folds         = 1/3
    mean interaction beta  = -0.2962
    interaction sign (+/-) = 1/2

Conclusion: reject as primary regime candidate.

## Secondary exploratory descriptors

Reported mean delta vs FB:

    cycle_to_direct:
        translation +0.130
        rotation    +0.189

    cycle_to_composed:
        translation +0.133
        rotation    +0.191

    direct_composed_ratio:
        translation +0.033
        rotation    -0.055

    log_direct_flow:
        translation +0.246
        rotation    +0.326

    support_fraction_cycle:
        translation -0.010
        rotation    -0.071

The identical performance of log_direct_flow and direct_flow_median_px is
expected under percentile-rank modeling because log1p is monotonic.  It is not
an independent finding.

cycle_to_direct / cycle_to_composed are interesting but remain secondary
post-hoc descriptors and must not replace the pre-specified primary candidate
without a separate validation protocol.

## Interpretation

direct_flow_median_px is the first M4 candidate that shows a strong and
consistent development-set improvement:

- positive delta vs FB on 3/3 folds for both translation and rotation;
- positive delta vs the global cycle model on 3/3 folds for both targets;
- positive mean cycle*flow interaction coefficient;
- rotation interaction sign positive on all three LOSO training fits.

This supports the hypothesis that the relation between temporal-cycle
inconsistency and pose reliability depends on temporal motion magnitude.

However, the current M4 model is:

    error ~ FB + CYCLE + Z + CYCLE*Z.

Therefore the observed gain can arise from either:

1. the main effect of Z = direct_flow_median_px;
2. the additive combination FB+CYCLE+Z;
3. the actual interaction CYCLE*Z.

The current audit does not isolate these components.

## Required next step before fresh validation

Run a nested development-set ablation with the same frozen descriptor:

    M0 = FB
    M1 = FB + CYCLE
    MZ = FB + Z
    MA = FB + CYCLE + Z
    MI = FB + CYCLE + Z + CYCLE*Z

Primary decomposition questions:

    rho(MZ)-rho(M0)
        Does direct flow magnitude alone predict reliability?

    rho(MA)-rho(MZ)
        Does cycle add value once flow magnitude is known?

    rho(MI)-rho(MA)
        Does the interaction itself add value beyond additive effects?

Only if CYCLE retains incremental value after conditioning on direct-flow
magnitude, or the interaction term itself gives stable held-out improvement,
should M4 be described as regime-conditioned cycle reliability.

If nearly all gain comes from MZ, the correct finding is instead that flow
magnitude is a stronger reliability cue than cycle uncertainty.

## Development-only warning

No thresholds or runtime gates should be derived from box1/box2/box3 yet.

Any model selected after the nested ablation must be frozen and tested on fresh
dynamic sequences that were not used to motivate M4.
