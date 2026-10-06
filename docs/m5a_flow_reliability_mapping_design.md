# M5-A: direct-flow reliability-aware mapping

Status: design freeze before runtime intervention results.

## 1. Motivation

M4-B confirmed on three fresh Bonn sequences that the runtime quantity

    direct_flow_median_px

contains substantial incremental information about local relative-pose
reliability beyond FB consistency and beyond the magnitude of the applied
camera-motion increment.

Fresh-sequence macro improvements from adding direct flow to the frozen
reliability predictor were:

    translation: +0.3273
    rotation:    +0.3667

with positive direction on 2/3 fresh sequences for both targets.

M5-A asks a separate downstream question:

> Can the confirmed reliability cue improve Gaussian mapping when used only to
> reweight per-keyframe RGB-D mapping supervision?

No other SLAM component is changed.

## 2. Why the M4-B rank model is not used directly online

M4-B used within-sequence percentile ranks.  Those ranks are non-causal because
the current frame cannot know future frames.

M5-A therefore does not deploy the M4-B regression coefficients directly.

Instead it preserves the confirmed ordering information with a training-only
empirical CDF of direct_flow_median_px.

The development set is:

    box1 + box2 + box3.

From those frames, store the sorted direct-flow values:

    D_train = sort({d_i}).

For a runtime frame k with direct flow d_k define the frozen training percentile

    q_k = ECDF_train(d_k).

Because larger direct flow predicts lower reliability, define

    c_k = max(1 - q_k, eps).

This score:
- is causal;
- uses no held-out/fresh GT;
- is monotonic in the confirmed cue;
- requires no sequence-level future statistics;
- introduces no learned error-label coefficients into runtime mapping.

The ECDF reference file is created once from the development table and frozen.

## 3. Exact direct-flow definition

M5-A preserves the exact signal definition confirmed in M4-B.

For frame t:

    F_10 = F(t -> t-1)
    F_21 = F(t-1 -> t-2)
    F_20 = F(t -> t-2).

The valid support is the M3-C support:
- baseline-static and FB-valid;
- p + F_10(p) inside frame t-1;
- composed target inside frame t-2;
- direct target inside frame t-2;
- finite flow values.

The runtime signal is

    d_k = median_{valid p} ||F_20(p)||.

Although cycle residual is no longer used, F_21 is retained in M5-A v1 solely
to preserve the exact support on which M4-B confirmed direct_flow_median_px.

This costs two extra RAFT calls on frames where the score is computed.
A later efficiency stage may simplify the support only after equivalence is
verified.

## 4. Mapping intervention

For each mapping viewpoint j, use confidence c_j from the frozen ECDF.

Within the actual RGB-D mapping viewpoint set W:

    w_j = c_j / mean_{i in W}(c_i).

Then clip only for stability:

    w_j <- clip(w_j, 0.25, 4.0)

and renormalize to mean one.

The mapping loss becomes

    L_map =
        sum_{j in W} w_j L_rgbd,j
        + L_regularization.

Exactly as in the earlier M1 mapping experiment:
- only per-view RGB-D mapping loss is weighted;
- flow loss is unchanged;
- mask loss is unchanged;
- regularizers are unchanged;
- pose optimization is unchanged;
- keyframe selection is unchanged;
- Gaussian insertion/pruning is unchanged.

## 5. Isolation groups

Every evaluation sequence must use three paired runs with the same seed.

### Baseline

No M5 score computation and no mapping weighting.

### Shadow

M5 score computation ON.
Mapping weighting OFF.

This measures overhead and checks that the extra diagnostic path is
behavior-neutral.

### Weighted

M5 score computation ON.
M5 RGB-D mapping weighting ON.

The causal comparison is primarily:

    weighted vs shadow

because both execute the same extra flow computations.

Baseline vs shadow is a behavior-neutrality / runtime check.

## 6. Missing-score rule

Frames t < 2 or frames with invalid M5 support receive neutral confidence:

    c = 1.

No previous/future score is copied forward.

## 7. Frozen weight mapping

First M5-A version fixes:

    confidence = max(1 - training_ECDF(direct_flow), 1e-3)

and mapping weight clipping:

    [0.25, 4.0].

Do not tune:
- exponent;
- temperature;
- alternative quantile transform;
- clip bounds

after viewing evaluation outcomes.

If this mapping fails, stop M5-A v1 rather than searching a large family of
weight transforms on the same evaluation sequences.

## 8. Evaluation set

The first downstream evaluation is frozen before M5-A outcomes are inspected.

Use three sequences that were not used to discover the direct-flow cue:

1. balloon2
2. moving_nonobstructing_box2
3. removing_nonobstructing_box

remove_box was used in M4-B reliability confirmation but not to choose the
runtime mapping transform.  It is deliberately retained because its M4-B
incremental reliability effect was near zero, providing a useful heterogeneity
test rather than selecting only favorable reliability sequences.

If a fully untouched downstream test set is required for a final paper claim,
run an additional benchmark after M5-A method choices are frozen.

## 9. Seeds and paired comparison

Initial stage:

    seed = 0

for all baseline/shadow/weighted runs.

If the first paired result is promising, repeat with pre-declared seeds:

    0, 1, 2

before making a downstream claim.

Do not choose seeds based on outcome.

## 10. Primary end-task metrics

Primary:
- ATE RMSE from the repository evaluation path.

Secondary:
- rendering metrics already produced by the repository when available;
- runtime;
- mapping-weight distribution;
- effective sample size of mapping windows;
- trajectory divergence weighted vs shadow.

A useful M5-A result must be consistent across multiple sequences.
One improved sequence is insufficient.

## 11. Stop rule

M5-A v1 is worth continuing only if weighted vs shadow shows:
- improvement on at least 2/3 predefined sequences for ATE RMSE; and
- no catastrophic degradation on the remaining sequence.

If the result is mixed or systematically worse, stop this intervention rather
than simultaneously changing keyframes, insertion, masks, or tracking.

## 12. Stage artifacts

Code:
- utils/m5_flow_reliability.py
- scripts/build_m5_flow_reference.py

Configs:
- baseline/shadow/weighted overlays for the frozen sequences.

Documentation:
- docs/m5a_stage_runbook.md
- docs/m5a_flow_reliability_mapping_results.md after execution.
