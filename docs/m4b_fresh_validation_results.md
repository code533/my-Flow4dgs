# M4-B result: fresh-sequence confirmatory validation

Status: **PASS — direct-flow reliability cue confirmed on fresh sequences**

Date: 2026-10-06

Branch:

    feature/m4b-fresh-validation

Primary audit:

    scripts/audit_m4b_fresh_confirmatory.py

Development fit:

    box1 + box2 + box3

Fresh evaluation:

    balloon + remove_box + synchronous2

The development sequences were used only to fit frozen model coefficients.
No coefficient was refit on the fresh sequences.

## Frozen models

Comparator:

    M0 =
        FB
        + translation motion magnitude
        + rotation motion magnitude

Candidate:

    M1 =
        FB
        + translation motion magnitude
        + rotation motion magnitude
        + direct_flow_median_px

Primary metric:

    delta-rho =
        rho(M1, error)
        -
        rho(M0, error).

Frozen ridge lambda:

    0.001

Frozen moving-block bootstrap:

    block length = 20
    bootstrap samples = 1000
    seed = 0

## Translation target

### balloon

    M0 rho      = +0.0335
    M1 rho      = +0.5261
    delta-rho   = +0.4926
    bootstrap CI95 = [+0.1346, +0.6627]

### remove_box

    M0 rho      = +0.4086
    M1 rho      = +0.4026
    delta-rho   = -0.0060
    bootstrap CI95 = [-0.3812, +0.0776]

### synchronous2

    M0 rho      = -0.3380
    M1 rho      = +0.1574
    delta-rho   = +0.4954
    bootstrap CI95 = [+0.1064, +0.6492]

### Translation macro

    macro delta-rho = +0.3273
    positive fresh sequences = 2/3

Frozen translation gate:

    PASS

## Rotation target

### balloon

    M0 rho      = +0.0270
    M1 rho      = +0.6289
    delta-rho   = +0.6019
    bootstrap CI95 = [+0.1628, +0.9465]

### remove_box

    M0 rho      = +0.4163
    M1 rho      = +0.3760
    delta-rho   = -0.0403
    bootstrap CI95 = [-0.4140, +0.1116]

### synchronous2

    M0 rho      = -0.1887
    M1 rho      = +0.3497
    delta-rho   = +0.5384
    bootstrap CI95 = [-0.0731, +0.6656]

### Rotation macro

    macro delta-rho = +0.3667
    positive fresh sequences = 2/3

Frozen rotation gate:

    PASS

## Frozen gate result

The pre-registered gate required:

- macro delta-rho >= +0.05 for at least one target;
- positive delta on at least 2/3 fresh sequences for that target;
- the other target must not have macro delta < -0.05;
- the conclusion must not rely on a single fresh sequence.

Observed:

    translation:
        macro = +0.3273
        positive = 2/3

    rotation:
        macro = +0.3667
        positive = 2/3

Therefore:

    translation PASS = True
    rotation PASS    = True
    OVERALL PASS     = True

M4-B passes substantially above the frozen practical-effect threshold.

## Interpretation

This is the first uncertainty/reliability-related signal in the project that
has survived both:

1. development-set confound analysis; and
2. strict fresh-sequence confirmation.

The confirmed signal is not the original M1 covariance, M3 jackknife,
appearance perturbation, or temporal-cycle residual.

It is the simple runtime quantity:

    direct_flow_median_px

measured from the direct t -> t-2 optical flow over the fixed valid support.

The fresh result supports the following statement:

> Direct optical-flow magnitude provides substantial incremental information
> about local relative-pose reliability beyond FB consistency and beyond the
> magnitude of the applied camera-motion increment.

This statement is supported on two of three fresh sequences and for both
translation and rotation.

## Sequence heterogeneity

The effect is not universal frame-for-frame.

remove_box does not benefit:

    translation delta = -0.0060
    rotation delta    = -0.0403.

Both bootstrap intervals include zero.

Therefore the confirmed claim must remain:

> direct flow is a useful cross-sequence reliability cue,

not:

> direct flow always improves reliability prediction on every sequence.

balloon shows a strong positive effect with bootstrap intervals excluding zero
for both translation and rotation.

synchronous2 also shows large positive point estimates; its translation
bootstrap interval excludes zero, while the rotation interval still overlaps
zero slightly.

The heterogeneity should be reported rather than hidden.

## Scientific consequence

The M4 development sequence changed the interpretation of the project.

Rejected or unsupported as general-purpose downstream signals:

- M1 frame-level covariance scalar beyond FB;
- M1 mapping weighting;
- projected M1 covariance for motion discrimination;
- M3-A spatial jackknife;
- M3-B appearance perturbation;
- M3-C temporal-cycle residual as a universal cue.

Confirmed on fresh data:

- direct two-frame optical-flow magnitude as an incremental local-pose
  reliability cue.

This quantity should currently be described as a **reliability cue**, not as a
calibrated probabilistic uncertainty or posterior covariance.

## What is not yet established

M4-B does not show that using direct flow inside SLAM improves:

- trajectory ATE;
- mapping quality;
- rendering;
- dynamic segmentation;
- keyframe selection.

It establishes predictive reliability value only.

A downstream runtime intervention must be tested separately with behavior
isolation and a pre-specified protocol.

## Recommended next stage

Proceed to M5: runtime use of the confirmed direct-flow reliability cue.

The next stage should first convert the frozen predictor into a scalar frame
reliability score without changing the feature definition.

Candidate training-only reliability model:

    q_k =
        f(
            FB_rank,
            translation_motion_rank,
            rotation_motion_rank,
            direct_flow_rank
        )

where model coefficients are learned only from development/training sequences.

The first downstream intervention should modify exactly one SLAM component.

Preferred first intervention:

    reliability-aware mapping frame weighting

because it allows a clean comparison against the earlier failed M1 covariance
mapping weight while holding the intervention location fixed and changing only
the reliability source.

Alternative second-stage interventions, only after mapping is understood:

- keyframe acceptance;
- tracking fallback / trust;
- dynamic-mask confidence.

Do not activate multiple interventions at once.

## Reproducibility note

The exact timestamped run-directory paths were not included in the terminal
summary available when this result document was committed. They can be appended
later for archival provenance if desired.

The statistical decision itself is fixed by the reported fresh-sequence output
and the pre-registered M4-B gate.
