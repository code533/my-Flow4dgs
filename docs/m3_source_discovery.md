# M3: Independent uncertainty-source discovery

## Motivation

M1 produced a calibrated local relative-motion covariance, but two downstream
audits exposed a clear information bottleneck:

1. the frame-level M1 reliability scalar adds almost no held-out predictive
   value beyond forward/backward (FB) flow consistency;
2. projected pose covariance in motion-residual space did not show a stable
   advantage after spatial cross-fitting and scale/shape/source controls.

M3 therefore changes the question.  It does not search for another place to
inject the existing M1 covariance.  Instead it asks whether a new runtime
signal contains reliability information that is not already present in FB
consistency.

The first candidate is deliberately network-free and behavior-preserving.

## M3-A: spatial delete-block jackknife pose instability

For the same baseline static-pixel set used by the Flow4DGS second pose refit,
let

    xi_full = fit(static pixels).

Partition the image into B spatial blocks.  For block b, remove all candidate
pixels in that block and refit the *baseline* robust estimator:

    xi_(-b) = fit(static pixels \ block b).

The score therefore measures estimator sensitivity to the spatial observation
set.  It is not constructed from the M1 FB-derived covariance.

For n valid delete-block refits, define

    xi_bar = mean_b xi_(-b)

and the equal-block delete-one jackknife covariance

    P_JK = (n - 1) / n * sum_b
           (xi_(-b) - xi_bar)(xi_(-b) - xi_bar)^T.

Primary scalar diagnostics are

    sigma_JK,t = sqrt(trace(P_JK,tt) / 3)
    sigma_JK,r = sqrt(trace(P_JK,rr) / 3).

We additionally log maximum leave-block-out translation/rotation parameter
deviations from xi_full.  These are secondary diagnostics only.

This covariance is an estimator-stability diagnostic, not a calibrated
posterior covariance.  Spatial blocks are not iid samples and the baseline
robust fit is nonlinear.

## Behavior isolation

M3-A is shadow-only:

- no camera pose is changed;
- no motion mask is changed;
- no keyframe decision is changed;
- no Gaussian state, mapping loss, insertion, pruning, or deformation is changed;
- no global RNG state is touched.

The full baseline pose estimate xi_full remains the pose used by Flow4DGS.

## Runtime configuration

M3-A is disabled by default.

```yaml
Uncertainty:
  m3_jackknife_audit: false
  m3_jackknife_grid_rows: 4
  m3_jackknife_grid_cols: 4
  m3_jackknife_min_train_pixels: 1000
  m3_jackknife_min_removed_pixels: 50
  m3_jackknife_frame_range: null
```

For an initial transition-neighborhood audit, set for example

```yaml
  m3_jackknife_audit: true
  m3_jackknife_frame_range: [211, 271]
```

Diagnostics are saved under

    <Results.save_dir>/m3_pose_jackknife/*.pt

M3-A currently requires M1 diagnostics to be enabled as well so the same run
also records the FB signal and matched relative-pose quantities used by the
existing reliability audit.  The jackknife score itself does not use FB
variance or M1 covariance.

## Incremental-value gate

First run the existing relative-pose reliability audit to produce per-sequence
CSV files containing the final baseline relative-pose errors and FB signal.

Then run

```bash
python scripts/audit_m3_jackknife_incremental.py \
  --sequence box1=/run/box1/m3_pose_jackknife,/analysis/box1.csv \
             box2=/run/box2/m3_pose_jackknife,/analysis/box2.csv \
             box3=/run/box3/m3_pose_jackknife,/analysis/box3.csv \
  --output results/m3_jackknife_incremental.json
```

Primary tests are pre-specified:

- translation: sigma_JK,t vs final relative translation error;
- rotation: sigma_JK,r vs final relative rotation error.

For each sequence the script reports raw Spearman correlation, partial
Spearman after controlling FB rank, and a moving-block bootstrap interval.

It also performs leave-one-sequence-out rank prediction:

    M_FB    : error-rank ~ FB-rank
    M_FB+JK : error-rank ~ FB-rank + JK-rank.

The main incremental metric is

    delta-rho = rho(M_FB+JK, error) - rho(M_FB, error).

## Stop rule

Do not connect M3-A to SLAM behavior unless the held-out audit shows a
practically meaningful and reasonably consistent incremental signal.

The initial research gate is:

- macro LOSO delta-rho should be materially larger than the M1 result; as a
  resource-allocation rule, about +0.03 to +0.05 is the minimum effect worth
  pursuing;
- the direction should be positive on at least two of three Bonn box sequences
  and should not depend on one isolated sequence;
- no held-out sequence may be used to redefine the score.

If M3-A fails this gate, stop the jackknife route and move to an independent
flow-uncertainty source such as appearance-perturbation disagreement or a
three-frame temporal-cycle signal.
