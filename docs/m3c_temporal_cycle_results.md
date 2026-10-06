# M3-C result: three-frame temporal-cycle inconsistency

Status: **STOP — failed the pre-specified incremental-value gate**

Date: 2026-10-06

Branch:

    feature/m3c-temporal-cycle

Method:

    m3c_temporal_cycle_inconsistency_v1

Primary audit:

    scripts/audit_m3c_cycle_incremental.py

Primary signal:

    u_cycle = median_p ||F(t->t-2) - F_comp(t->t-2)||

where

    F_comp(p) =
        F(t->t-1)(p) +
        F(t-1->t-2)(p + F(t->t-1)(p)).

Each Bonn transition-neighborhood sequence contributed 61 joined frames.

## Within-sequence result

### box1, n=61

Translation:

    CYCLE raw rho      = +0.0125
    FB raw rho         = -0.0048
    CYCLE~FB rho       = +0.4193
    partial rho        = +0.0160
    partial CI95       = [-0.1155, +0.3372]

Rotation:

    CYCLE raw rho      = +0.1036
    FB raw rho         = +0.1051
    CYCLE~FB rho       = +0.4193
    partial rho        = +0.0659
    partial CI95       = [-0.1670, +0.4637]

### box2, n=61

Translation:

    CYCLE raw rho      = +0.2284
    FB raw rho         = +0.2995
    CYCLE~FB rho       = +0.6625
    partial rho        = +0.0419
    partial CI95       = [-0.1878, +0.1351]

Rotation:

    CYCLE raw rho      = +0.1741
    FB raw rho         = +0.2799
    CYCLE~FB rho       = +0.6625
    partial rho        = -0.0157
    partial CI95       = [-0.2749, +0.0996]

### box3, n=61

Translation:

    CYCLE raw rho      = +0.4520
    FB raw rho         = +0.1780
    CYCLE~FB rho       = +0.4479
    partial rho        = +0.4232
    partial CI95       = [+0.1389, +0.4931]

Rotation:

    CYCLE raw rho      = +0.6316
    FB raw rho         = +0.2716
    CYCLE~FB rho       = +0.4479
    partial rho        = +0.5927
    partial CI95       = [+0.3376, +0.6508]

## LOSO incremental-value result

Held out box1, train box2+box3:

    translation: FB=-0.0048, FB+CYCLE=-0.0068, delta=-0.0020
    rotation:    FB=+0.1051, FB+CYCLE=+0.0901, delta=-0.0151

Held out box2, train box1+box3:

    translation: FB=+0.2995, FB+CYCLE=+0.2299, delta=-0.0696
    rotation:    FB=+0.2799, FB+CYCLE=+0.1756, delta=-0.1043

Held out box3, train box1+box2:

    translation: FB=+0.1780, FB+CYCLE=+0.3098, delta=+0.1318
    rotation:    FB=+0.2716, FB+CYCLE=+0.3957, delta=+0.1241

Macro directional summary:

    translation:
        partial mean        = +0.1604
        partial positive    = 3/3
        LOSO delta mean     = +0.0201
        LOSO delta positive = 1/3

    rotation:
        partial mean        = +0.2143
        partial positive    = 2/3
        LOSO delta mean     = +0.0016
        LOSO delta positive = 1/3

Reported audit file:

    results/m3c_cycle_incremental.json

## Decision against the pre-specified gate

The M3-C design froze the following continuation gate before held-out evaluation:

- macro LOSO delta-rho approximately +0.03 to +0.05 or larger;
- positive direction on at least 2/3 held-out sequences;
- no temporal baseline, summary statistic, or threshold retuning after
  held-out inspection.

M3-C fails this gate.

Translation:
- macro LOSO delta-rho is +0.0201, below the practical continuation threshold;
- only 1/3 held-out folds are positive;
- box2 degrades by -0.0696.

Rotation:
- macro LOSO delta-rho is only +0.0016;
- only 1/3 held-out folds are positive;
- box2 degrades by -0.1043.

Therefore M3-C does not provide a sufficiently transferable incremental
reliability signal beyond FB under the fixed cross-sequence protocol.

## Important positive observation: box3

Box3 is qualitatively different from box1/box2.

After conditioning on FB:

    translation partial rho = +0.4232
    rotation partial rho    = +0.5927

with bootstrap intervals entirely above zero.

The held-out box3 fold also improves strongly:

    translation delta-rho = +0.1318
    rotation delta-rho    = +0.1241.

This is genuine evidence that temporal-cycle inconsistency can be useful in a
specific sequence regime.

However, it cannot be promoted to a general uncertainty source because the
same relation does not transfer to box1 or box2.  The correct conclusion is
therefore not "M3-C works", but:

> temporal-cycle reliability is strongly regime-dependent.

## Interpretation

Compared with M3-A and M3-B, M3-C is the first candidate to show a substantial
FB-conditioned signal in one sequence and a large held-out gain on that same
sequence family realization.

This suggests that the limiting issue may no longer be only the uncertainty
source itself.  A single globally fixed scalar reliability model may be
mis-specified across different dynamic-scene regimes.

Potential regime factors include:

- amount and type of non-rigid motion;
- temporal acceleration;
- occlusion/disocclusion frequency;
- camera-motion magnitude;
- dynamic-object image occupancy;
- flow magnitude / temporal baseline;
- scene depth and parallax structure.

These hypotheses require a new analysis stage and must not be tested by
retuning M3-C on the existing held-out box sequences.

## Stage conclusion

**Stop M3-C as a universal uncertainty source.**

Do not:
- tune the temporal baseline on box1/box2/box3;
- switch the primary statistic from median to q90/q95;
- inject cycle uncertainty into SLAM;
- select box3 as proof of a general method.

Retain M3-C as an important negative/diagnostic result showing strong
sequence-dependent temporal reliability.

## Recommended next stage

Preferred next step:

    M4: regime-conditioned reliability analysis

The purpose is not to invent another uncertainty scalar immediately.  Instead,
test why box3 behaves differently from box1/box2 using pre-existing runtime
scene descriptors that are independent of pose-error labels.

Candidate descriptors:

- median/quantiles of flow magnitude;
- dynamic-mask occupancy;
- valid static support;
- depth median/spread;
- camera-motion magnitude;
- temporal-cycle distribution shape;
- FB distribution shape;
- ratio of cycle to flow magnitude.

The first M4 stage should ask whether these descriptors explain the
cross-sequence change in the relationship between temporal-cycle inconsistency
and pose error.

Any regime rule must be learned/frozen on training sequences and evaluated on
held-out sequences; no rule may be selected from box3 because it is the sequence
that showed the strongest M3-C result.

## Environment note

The warning

    libgomp: Invalid value for environment variable OMP_NUM_THREADS

is unrelated to the M3-C statistical result.  Set OMP_NUM_THREADS to a valid
positive integer separately.
