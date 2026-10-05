# M3-C: three-frame temporal-cycle inconsistency

Status: design freeze before execution.

## 1. Motivation

M3-A spatial delete-block instability failed the held-out incremental-value
gate, and M3-B appearance-perturbation disagreement also failed to provide a
stable transferable signal beyond forward/backward (FB) consistency.

Both prior candidates remain pair-local: M3-A perturbs the estimator support
for the same pair, and M3-B perturbs the appearance of the same pair.

M3-C introduces a genuinely new temporal constraint using three consecutive
frames.

For frames t, t-1, t-2, define:

    F_10 = F(t -> t-1)
    F_21 = F(t-1 -> t-2)
    F_20 = F(t -> t-2)

where all flows are in pixel coordinates.

For a current-frame pixel p, map it first to frame t-1:

    q = p + F_10(p).

Sample F_21 at q and compose:

    F_comp(p) =
        F_10(p) + F_21(q).

The temporal-cycle inconsistency is

    e_cycle(p) =
        || F_20(p) - F_comp(p) ||_2.

This tests whether direct two-frame correspondence agrees with the temporal
composition of two adjacent correspondences.

## 2. Why this source is different from FB

FB consistency uses a reciprocal flow pair for the same two frames:

    t -> t-1
    t-1 -> t.

M3-C instead introduces:

    t-1 -> t-2
    t -> t-2.

It therefore probes temporal consistency across an additional frame and can
respond to:

- transient occlusion/disocclusion;
- non-rigid acceleration;
- temporal flow drift;
- correspondence instability that remains pairwise reciprocal;
- local changes in scene appearance/motion that only become visible over a
  longer temporal baseline.

M3-C is not statistically independent of FB because the same RAFT model and
one shared t->t-1 flow are used.  Its value must still be tested after
conditioning on FB.

## 3. Fixed first-stage signal

The first-stage primary signal is fixed before held-out evaluation:

    u_cycle =
        median_{p in valid baseline-static support} e_cycle(p).

Secondary diagnostics are saved but are not model-selection targets:

- mean cycle residual;
- q90 cycle residual;
- q95 cycle residual;
- maximum cycle residual;
- valid-pixel count;
- direct-flow magnitude median;
- composed-flow magnitude median.

Do not switch the primary signal after observing held-out results.

## 4. Valid support

A pixel is valid only if:

1. it belongs to the same baseline-static + FB-valid support used by M1;
2. q = p + F_10(p) lies inside frame t-1;
3. F_21(q) is finite;
4. q2 = q + F_21(q) lies inside frame t-2;
5. the direct target p + F_20(p) lies inside frame t-2;
6. all compared flow values are finite.

No dynamic/static label is used to tune the score.

## 5. Behavior isolation

M3-C is shadow-only.

It does not modify:

- F_10 used by Flow4DGS;
- the motion mask;
- the pose mean;
- M1 covariance;
- keyframe selection;
- mapping;
- Gaussian state.

M3-C adds two extra current-direction RAFT evaluations on audited frames:

    F_21 = F(t-1 -> t-2)
    F_20 = F(t -> t-2).

F_10 is reused from the ordinary M1/baseline path.

All extra calls are uncached and diagnostic-only.

## 6. First-stage scope

Use the same +/-30-frame Bonn transition neighborhoods as M3-A/M3-B:

    box1: [211,271]
    box2: [232,292]
    box3: [318,378].

M1 remains enabled solely to save the matched FB signal.
M2-A remains enabled only as a shadow logger for the matched final frontend
pose.  M2-A calibration and M2-A2 remain disabled.

## 7. Evaluation gate

Use the same fixed protocol as M1/M3-A/M3-B.

Within sequence:

    rho(u_cycle, final relative-pose error)

and

    rho(u_cycle, error | FB).

LOSO rank prediction:

    M_FB:
        error-rank ~ FB-rank

    M_FB+CYCLE:
        error-rank ~ FB-rank + cycle-rank.

Primary incremental metric:

    delta-rho =
        rho(M_FB+CYCLE, error) - rho(M_FB, error).

## 8. Stop rule

Proceed beyond source discovery only if:

- macro LOSO delta-rho is approximately +0.03 to +0.05 or larger;
- at least 2/3 held-out sequences are positive;
- the signal is not useful only for one target or one sequence;
- no temporal baseline, statistic, or threshold is changed after held-out
  inspection.

If M3-C fails, stop the temporal-cycle route rather than tuning it on the same
three held-out sequences.

## 9. Output

Diagnostics are saved under

    <Results.save_dir>/m3c_temporal_cycle/*.pt

The first-stage payload stores scalar summaries only.  Full pixelwise cycle
maps can be retained later only if the source passes the gate.
