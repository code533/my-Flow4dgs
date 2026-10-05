# M3-B result: appearance-perturbation flow disagreement

Status: **STOP — failed the pre-specified incremental-value gate**

Date: 2026-10-05

Branch:

    feature/m3b-flow-perturbation

Method:

    m3b_flow_perturbation_disagreement_v1

Primary audit:

    scripts/audit_m3b_flow_incremental.py

The experiment used the fixed five-flow ensemble:

    identity
    gamma 0.80
    gamma 1.25
    contrast 0.80
    contrast 1.25

The primary frame-level source signal was fixed before evaluation as:

    u_TTA = median_p sqrt(trace(Sigma_F,p))

computed over baseline-static and FB-valid support.

Each Bonn transition-neighborhood sequence contributed 61 joined frames.

## Within-sequence result

### box1, n=61

Translation:

    TTA raw rho      = -0.1221
    FB raw rho       = -0.0854
    TTA~FB rho       = +0.3992
    partial rho      = -0.0963
    partial CI95     = [-0.3551, +0.0841]

Rotation:

    TTA raw rho      = -0.0504
    FB raw rho       = +0.0994
    TTA~FB rho       = +0.3992
    partial rho      = -0.0987
    partial CI95     = [-0.6532, +0.2206]

### box2, n=61

Translation:

    TTA raw rho      = +0.1148
    FB raw rho       = +0.3127
    TTA~FB rho       = +0.5850
    partial rho      = -0.0885
    partial CI95     = [-0.3015, +0.2246]

Rotation:

    TTA raw rho      = +0.0780
    FB raw rho       = +0.2979
    TTA~FB rho       = +0.5850
    partial rho      = -0.1243
    partial CI95     = [-0.3650, +0.1416]

### box3, n=61

Translation:

    TTA raw rho      = -0.0929
    FB raw rho       = +0.1831
    TTA~FB rho       = +0.0612
    partial rho      = -0.1061
    partial CI95     = [-0.2952, +0.1170]

Rotation:

    TTA raw rho      = +0.0287
    FB raw rho       = +0.2769
    TTA~FB rho       = +0.0612
    partial rho      = +0.0123
    partial CI95     = [-0.2046, +0.1991]

## LOSO incremental-value result

Held out box1, train box2+box3:

    translation: FB=-0.0854, FB+TTA=-0.0441, delta=+0.0413
    rotation:    FB=+0.0994, FB+TTA=+0.1241, delta=+0.0247

Held out box2, train box1+box3:

    translation: FB=+0.3127, FB+TTA=+0.1091, delta=-0.2036
    rotation:    FB=+0.2979, FB+TTA=+0.3148, delta=+0.0169

Held out box3, train box1+box2:

    translation: FB=+0.1831, FB+TTA=+0.1951, delta=+0.0120
    rotation:    FB=+0.2769, FB+TTA=+0.2550, delta=-0.0219

Macro directional summary:

    translation:
        partial mean        = -0.0969
        partial positive    = 0/3
        LOSO delta mean     = -0.0501
        LOSO delta positive = 2/3

    rotation:
        partial mean        = -0.0703
        partial positive    = 1/3
        LOSO delta mean     = +0.0066
        LOSO delta positive = 2/3

Reported audit file:

    results/m3b_flow_incremental.json

## Decision against the pre-specified gate

The M3-B design froze the following gate before held-out evaluation:

- target macro LOSO delta-rho approximately +0.03 to +0.05 or larger;
- positive direction on at least 2/3 held-out sequences;
- no perturbation or summary-statistic retuning after viewing held-out results.

M3-B fails this gate.

Translation:
- although 2/3 held-out folds have positive delta-rho, the macro delta is
  negative (-0.0501);
- the box2 held-out fold degrades strongly (delta=-0.2036);
- partial correlations are negative in all 3 sequences.

Rotation:
- 2/3 held-out folds are positive, but macro delta is only +0.0066, far below
  the practical continuation threshold;
- partial correlations are non-positive in 2/3 sequences and essentially zero
  in box3.

Therefore the appearance-perturbation flow-disagreement signal does not provide
a sufficiently strong or transferable incremental reliability signal beyond FB.

## Interpretation

The M3-B signal is not degenerate: earlier smoke diagnostics showed meaningful
frame-to-frame variation and valid support in all audited frames.

However, signal variation alone is insufficient.  The key question is whether
that variation tracks relative-pose reliability after conditioning on FB.

The answer is negative:

- box1/box2 show moderate TTA-FB association (+0.3992 / +0.5850), suggesting
  that appearance sensitivity partially follows the same difficult-image
  structure already visible to FB;
- box3 has almost no TTA-FB association (+0.0612), yet TTA still fails to
  produce useful partial reliability association;
- held-out prediction is unstable across sequences, with one severe
  translation failure on box2.

This indicates that global gamma/contrast sensitivity of the same RAFT model is
not a transferable pose-reliability source in the current setting.

## Stage conclusion

**Stop M3-B.**

Do not:
- tune gamma or contrast values on box1/box2/box3;
- switch the primary statistic from median to q90/q95/mean after seeing this
  result;
- inject M3-B into M1 covariance, mapping, masks, keyframes, or pose;
- present M3-B as a positive paper contribution.

Retain it as a negative source-discovery audit.

## Next stage

Preferred next candidate:

    M3-C: three-frame temporal-cycle inconsistency

Unlike M3-B, which repeatedly probes the same image pair with the same network,
M3-C introduces a genuinely new temporal constraint.

For frames t, t-1, t-2:

    F_direct = F(t -> t-2)

and

    F_comp = F(t -> t-1)
             + warp(F(t-1 -> t-2), F(t -> t-1)).

The temporal-cycle residual is

    e_cycle,p = ||F_direct,p - F_comp,p||.

The first-stage source-discovery signal should again remain shadow-only and be
evaluated against FB using the same partial-Spearman and LOSO incremental-value
gate before any SLAM intervention.

## Environment note

The terminal warning

    libgomp: Invalid value for environment variable OMP_NUM_THREADS

is an environment-configuration warning rather than an M3-B statistical result.
It should be fixed separately by setting OMP_NUM_THREADS to a valid positive
integer, but it does not change the pass/fail interpretation above.
