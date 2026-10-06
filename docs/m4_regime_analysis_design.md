# M4: regime-conditioned reliability analysis

Status: exploratory mechanism-analysis stage.

## 1. Motivation

M3-C temporal-cycle inconsistency did not pass the universal held-out gate, but
it showed a striking sequence-dependent pattern.

On Bonn box3, after conditioning on FB consistency:

    translation partial rho = +0.4232
    rotation partial rho    = +0.5927

and the held-out box3 fold improved by:

    translation delta-rho = +0.1318
    rotation delta-rho    = +0.1241.

The same cycle signal did not generalize to box1/box2.

The M4 question is therefore not:

> Can we invent another uncertainty scalar?

It is:

> Which runtime scene/motion regime makes temporal-cycle inconsistency useful?

M4 is an analysis stage.  It does not alter SLAM behavior.

## 2. Development-set warning

box1/box2/box3 are no longer valid confirmatory test sequences for any
regime-conditioned rule because the M4 hypothesis was motivated by inspecting
their M3-C outcomes, especially the unusually strong box3 result.

Therefore:

- box1/box2/box3 are used only for hypothesis generation;
- any regime descriptor, interaction form, or gate discovered here must later
  be frozen;
- final evidence must come from fresh sequences that were not used to define
  the M4 rule.

Do not present development-set interaction gains as final generalization.

## 3. First-stage data

M4-A uses only existing diagnostics.  No SLAM rerun is required.

Per-frame inputs:

From M3-C payloads:
- u_cycle_median_px
- u_cycle_mean_px
- u_cycle_q90_px
- u_cycle_q95_px
- direct_flow_median_px
- composed_flow_median_px
- num_valid_pixels

From the matched relative-reliability CSV:
- fb_error_median_px
- valid_extent
- num_pixels
- log10_condition
- motion_scale_joint
- sigma_t
- sigma_r
- final relative translation error
- final relative rotation error

Derived development descriptors:
- cycle_to_direct = u_cycle_median_px / (direct_flow_median_px + eps)
- cycle_to_composed = u_cycle_median_px / (composed_flow_median_px + eps)
- direct_composed_ratio = direct_flow_median_px / (composed_flow_median_px + eps)
- log_direct_flow = log1p(direct_flow_median_px)
- log_condition = log10_condition as already saved
- support = valid_extent

The primary regime candidates for the first audit are deliberately limited to
runtime quantities that do not use pose-error labels:

1. direct_flow_median_px
2. valid_extent
3. log10_condition
4. motion_scale_joint

cycle-derived ratios are retained as secondary exploratory descriptors only.
They must not become a runtime gate unless a later fresh-sequence validation
supports them.

## 4. Interaction model

Within each sequence, convert variables to percentile ranks.

Baseline:

    M0:
      error_rank ~ FB_rank

Global cycle model:

    M1:
      error_rank ~ FB_rank + CYCLE_rank

Regime interaction model for descriptor z:

    M2(z):
      error_rank ~
        FB_rank
        + CYCLE_rank
        + Z_rank
        + CYCLE_rank * Z_rank.

The coefficient on the interaction term asks whether the usefulness of cycle
changes with the runtime regime.

Because only three development sequences are available, coefficients are not
treated as asymptotic statistical estimates.  The main exploratory quantities
are:

- sign of the interaction coefficient across LOSO folds;
- held-out rho(M2, error) - rho(M0, error);
- held-out rho(M2, error) - rho(M1, error);
- whether a candidate helps both translation and rotation;
- whether an apparent effect is driven only by box3.

Ridge regularization is used only for numerical stability.

## 5. What would count as an interesting M4-A finding?

M4-A is hypothesis-generating, so it does not have the same confirmatory gate as
M3.  A descriptor is worth fresh-sequence testing only if:

- its cycle*descriptor interaction coefficient has the same sign in at least
  two LOSO training fits;
- M2 improves over M0 on at least two development held-out sequences;
- the gain is not exclusively box3;
- the pattern is coherent for translation and/or rotation rather than appearing
  as one isolated number.

A descriptor that merely separates sequence identity is not sufficient.

## 6. Fresh validation requirement

If M4-A identifies a plausible regime descriptor, the next stage is M4-B:

1. freeze the descriptor and model form;
2. choose fresh Bonn dynamic sequences not used in box1/box2/box3 development;
3. run the same M3-C diagnostics on those sequences without changing the rule;
4. evaluate whether regime conditioning improves held-out reliability there.

Only fresh validation can support a paper claim.

## 7. First-stage outputs

The first-stage scripts are:

    scripts/build_m4_regime_table.py
    scripts/audit_m4_regime_interactions.py

Expected outputs:

    results/m4_regime_table.csv
    results/m4_regime_interactions.json

After running the exploratory audit, commit:

    docs/m4a_regime_interaction_results.md

whether the result is positive or negative.
