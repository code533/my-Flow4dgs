# M3-B: appearance-perturbation optical-flow disagreement

Status: design freeze before execution.

## 1. Motivation

M3-A spatial delete-block jackknife failed the pre-specified incremental-value
gate.  Its macro held-out delta-rho was negative for both translation and
rotation, so estimator resampling will not be tuned further.

M3-B changes the uncertainty source itself.

The existing M1 chain derives optical-flow variance primarily from
forward/backward (FB) consistency.  This makes it difficult for any downstream
M1 scalar to carry substantial information beyond FB.  M3-B therefore measures
a different property:

> How stable is the optical-flow prediction under geometry-preserving changes
> of image appearance?

If two images undergo the same global photometric transform, their underlying
pixel correspondence does not change.  A flow estimator whose prediction
changes substantially under such transforms is appearance-sensitive on that
frame.

## 2. Primary experiment

For the current frame pair, let the ordinary current-to-previous RAFT flow be

    F^(0).

Apply the same deterministic photometric transform to both frames and re-run
RAFT.  The fixed first-stage ensemble is:

    identity
    gamma = 0.80
    gamma = 1.25
    contrast = 0.80
    contrast = 1.25

The two reciprocal gamma/contrast values are fixed before evaluation.  No value
is selected from held-out results.

For gamma:

    I' = clamp(I,0,1)^gamma.

For contrast:

    I' = clamp((I - 0.5) * c + 0.5, 0, 1).

The transforms are applied identically to both images, so the scene geometry is
unchanged.

## 3. Pixel-level disagreement

For M=5 current-to-previous flow predictions in pixel units,

    Fbar_p = (1/M) sum_m F_p^(m)

and

    Sigma_F,p =
        1/(M-1) sum_m
        (F_p^(m)-Fbar_p)(F_p^(m)-Fbar_p)^T.

The primary per-pixel magnitude is

    s_p = sqrt(trace(Sigma_F,p)).

The primary frame-level M3-B signal is fixed as

    u_TTA = median_{p in baseline-static support} s_p.

Secondary diagnostics are recorded but are not model-selection targets:

- mean s_p;
- q90/q95 s_p;
- median norm(Fbar_p - F_identity,p);
- maximum s_p;
- number of valid pixels.

M3-B does not use dynamic/static labels to define the perturbations.

## 4. Behavior isolation

M3-B is shadow-only.

It does not change:

- the identity RAFT flow used by Flow4DGS;
- the motion mask;
- the baseline pose estimate;
- M1 covariance;
- keyframe selection;
- mapping;
- Gaussian insertion/pruning/deformation.

The extra perturbed RAFT calls are diagnostic only.

M1 remains enabled in the experiment solely so that the same run records the
existing FB signal.  M2-A remains enabled only as a shadow logger for the final
frontend pose used by the matched relative-pose reliability audit.  M2-A
calibration and M2-A2 remain disabled.

## 5. Independence claim

M3-B is not statistically independent of FB because both are derived from the
same images and the same RAFT model.  The intended claim is narrower:

> M3-B is not a deterministic re-parameterization of the FB residual used by
> M1.  It probes appearance sensitivity through repeated same-direction flow
> predictions.

Its value must therefore be established empirically by conditioning on FB.

## 6. Evaluation gate

Use the same pre-specified protocol as M1/M3-A.

For each Bonn box sequence, report

    rho(u_TTA, final relative-pose error)

and

    rho(u_TTA, error | FB)

using partial Spearman rank correlation.

Then perform leave-one-sequence-out rank prediction:

    M_FB:
        error-rank ~ FB-rank

    M_FB+TTA:
        error-rank ~ FB-rank + TTA-rank.

Primary incremental metric:

    delta-rho =
        rho(M_FB+TTA, error) - rho(M_FB, error).

The same scalar u_TTA is used for both translation and rotation targets.

## 7. Stop rule

M3-B proceeds to a probabilistic pose model only if the held-out result is
practically meaningful and reasonably consistent.

Resource-allocation gate:

- target macro LOSO delta-rho approximately +0.03 to +0.05 or larger;
- positive direction on at least 2/3 held-out Bonn box sequences;
- no perturbation, summary statistic, or threshold may be redefined after
  viewing held-out results.

If M3-B again produces approximately zero or negative incremental value, stop
the appearance-perturbation route.  The next source candidate is three-frame
temporal-cycle inconsistency.

## 8. Runtime cost

The identity flow is reused from the ordinary Flow4DGS/M1 path.  M3-B adds four
current-to-previous RAFT evaluations on audited frames only.

The first stage uses the same +/-30-frame transition neighborhoods as M3-A, so
the cost is bounded before any full-sequence experiment is considered.

## 9. Output

Diagnostics are saved under

    <Results.save_dir>/m3b_flow_perturbation/*.pt

The result payload stores scalar summaries and covariance-summary statistics,
not full-resolution per-pixel covariance maps.  If M3-B passes the source gate,
a later stage may rerun the experiment and retain pixel-level covariance for
pose propagation.
