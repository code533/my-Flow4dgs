# M3-A result: spatial delete-block jackknife pose instability

Status: **STOP — failed the pre-specified incremental-value gate**

Date: 2026-10-05

Branch:

    feature/m3-source-discovery

Method:

    m3_pose_delete_block_jackknife_v1

Primary audit:

    scripts/audit_m3_jackknife_incremental.py

The experiment used the pre-specified 4x4 spatial delete-block jackknife and
evaluated only the +/-30-frame transition neighborhoods for Bonn box1/box2/box3.
Each sequence contributed 61 joined frames.

The purpose of this stage was not to improve SLAM directly.  It asked whether
pose-estimator instability supplies relative-pose reliability information beyond
the already-strong forward/backward (FB) flow-consistency signal.

## Reported result

### box1, n=61

Translation:

    JK raw rho      = -0.0838
    FB raw rho      = -0.0524
    partial rho     = -0.0681
    partial CI95    = [-0.1999, +0.4085]

Rotation:

    JK raw rho      = -0.1081
    FB raw rho      = +0.1014
    partial rho     = -0.1659
    partial CI95    = [-0.3211, +0.3407]

### box2, n=61

Translation:

    JK raw rho      = -0.0007
    FB raw rho      = +0.3112
    partial rho     = -0.0545
    partial CI95    = [-0.0781, +0.1873]

Rotation:

    JK raw rho      = -0.0964
    FB raw rho      = +0.2805
    partial rho     = -0.1449
    partial CI95    = [-0.1674, +0.0163]

### box3, n=61

Translation:

    JK raw rho      = +0.2025
    FB raw rho      = +0.1779
    partial rho     = +0.1554
    partial CI95    = [-0.2001, +0.2970]

Rotation:

    JK raw rho      = +0.3274
    FB raw rho      = +0.2864
    partial rho     = +0.2615
    partial CI95    = [-0.0777, +0.3657]

## LOSO incremental-value result

Held out box1, train box2+box3:

    translation: FB=-0.0524, FB+JK=-0.0627, delta=-0.0103
    rotation:    FB=+0.1014, FB+JK=+0.0714, delta=-0.0300

Held out box2, train box1+box3:

    translation: FB=+0.3112, FB+JK=+0.2267, delta=-0.0845
    rotation:    FB=+0.2805, FB+JK=+0.2396, delta=-0.0409

Held out box3, train box1+box2:

    translation: FB=+0.1779, FB+JK=+0.0779, delta=-0.0999
    rotation:    FB=+0.2864, FB+JK=+0.0512, delta=-0.2351

Macro directional summary:

    translation:
        partial mean       = -0.0109
        partial positive   = 1/3
        LOSO delta mean    = -0.0649
        LOSO delta positive= 0/3

    rotation:
        partial mean       = -0.0164
        partial positive   = 1/3
        LOSO delta mean    = -0.1020
        LOSO delta positive= 0/3

The reported audit file was:

    results/m3a_jackknife_incremental.json

## Decision against the pre-specified gate

The stage runbook required approximately +0.03 to +0.05 macro held-out
delta-rho, or larger, with positive direction on at least two of three
sequences before any runtime intervention would be considered.

M3-A fails this gate decisively:

- translation macro delta-rho is -0.0649;
- rotation macro delta-rho is -0.1020;
- all six target/fold LOSO deltas are negative;
- neither target is positive on any held-out fold;
- within-sequence partial correlations are inconsistent and their bootstrap
  intervals cross zero.

This is stronger evidence than merely "no measurable gain": under the fixed
LOSO rank-prediction protocol, adding the jackknife signal consistently worsens
held-out prediction relative to FB alone.

## Interpretation

The spatial delete-block estimator-instability signal is sequence dependent.
Box3 shows positive within-sequence association, but that structure does not
transfer from box1/box2 into box3, and the converse also fails.  Therefore the
box3 positive raw/partial correlations must not be interpreted as evidence for
a generally useful uncertainty source.

The result rejects the working hypothesis that simple spatial sensitivity of
the robust camera-motion estimator supplies a transferable reliability signal
beyond FB consistency in this setting.

No grid-size, threshold, score-definition, or held-out-specific tuning should
be performed after observing this result.  Such tuning would violate the
pre-specified source-discovery protocol.

## Stage conclusion

**Stop M3-A.**

Do not:
- connect jackknife uncertainty to mapping, motion masks, keyframes, or pose;
- tune the 4x4 partition on these held-out sequences;
- redefine a jackknife scalar using box3 because it happened to correlate
  positively there;
- present M3-A as a positive paper contribution.

Retain M3-A as a negative audit showing that estimator resampling instability
does not provide transferable incremental information beyond FB consistency.

## Next stage

Proceed to an uncertainty source whose information is genuinely different from
the current FB-derived M1 chain and from spatial estimator resampling.

Preferred next candidate:

    M3-B: appearance-perturbation optical-flow disagreement

For the same image pair, apply geometry-preserving photometric perturbations
(identity, gamma/brightness/contrast variants) to both frames, re-run the flow
network, and estimate per-pixel disagreement/covariance across predictions.

Before using it in any probabilistic pose solver, evaluate the new signal with
the same fixed gate:

    FB
    versus
    FB + M3-B

using within-sequence partial Spearman and held-out LOSO delta-rho.

A cheaper temporal-cycle candidate can be evaluated after or alongside M3-B,
but no downstream SLAM intervention should start until a source passes the
incremental-value gate.

## Reproducibility note

The stage used the M3-A configs:

- configs/rgbd/bonn/placing_box_m3_jackknife.yaml
- configs/rgbd/bonn/placing_box2_m3_jackknife.yaml
- configs/rgbd/bonn/placing_box3_m3_jackknife.yaml

with the pre-specified seed 0 protocol from docs/m3a_stage_runbook.md.

The exact timestamped run-directory paths were not included in the reported
terminal output available when this result note was committed.  They should be
added here later if archival provenance requires the precise local paths; this
does not affect the fixed numerical decision above.
