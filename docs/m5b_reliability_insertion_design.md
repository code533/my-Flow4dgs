# M5-B: reliability-aware Gaussian insertion admission

Status: design freeze before M5-B outcomes.

## 1. Motivation

M4-B established that direct two-frame optical-flow magnitude is a useful
runtime cue for local relative-pose reliability.

M5-A applied the cue only as a continuous RGB-D mapping-loss weight.  Its first
two seed-0 sequence results are mixed and comparable with execution variance.

M5-B moves the intervention closer to map contamination:

> keep tracking, keyframe selection, pose optimization, motion masks, and
> mapping unchanged, but prevent a very low-reliability keyframe from adding
> new Gaussians to the map.

This stage tests whether reliability is more useful as an admission decision
than as a small continuous loss weight.

## 2. Frozen reliability source

Use the same M5 causal runtime score:

    d_k = direct_flow_median_px

with the same development-only ECDF reference:

    results/m5_direct_flow_reference.json

and

    q_k = ECDF_train(d_k)
    c_k = max(1 - q_k, 1e-3).

No M5-B sequence is used to rebuild the reference distribution.

## 3. Frozen admission rule

The training distribution's least reliable 20% is rejected:

    c_k < 0.20

equivalently:

    q_k > 0.80.

If the frame has no valid M5 reliability estimate, it is admitted.

The threshold 0.20 is frozen before M5-B outcomes are observed.

Do not tune it to 0.10 / 0.30 / 0.50 on the same evaluation sequences.

## 4. Exact intervention location

The backend already receives a frontend keyframe message containing:

    add_new_gaussian

from the original Flow4DGS logic.

M5-B defines:

    effective_add_new_gaussian =
        add_new_gaussian
        AND m5_admit.

Only this boolean is changed.

If M5-B rejects insertion:
- the frame is still a keyframe;
- tracking is unchanged;
- its pose is unchanged;
- it remains in the mapping window;
- RGB-D mapping loss is unchanged;
- deformation logic is unchanged;
- motion masks are unchanged.

No M5 mapping-loss weighting is active in M5-B.

## 5. Mandatory-system guardrails

The following frames are never rejected by M5-B:

- initialization frame 0;
- the configured dynamic-start frame dystart;
- frames with invalid/missing M5 score.

This avoids suppressing mandatory map/dynamic initialization.

Therefore M5-B gates only ordinary optional Gaussian insertion events.

## 6. Experimental groups

For every sequence use three paired groups.

### Baseline

M5 score computation OFF.
Insertion gating OFF.

### Shadow

M5 score computation ON.
Insertion gating OFF.

### Gated

M5 score computation ON.
Insertion gating ON with frozen threshold 0.20.

Primary causal comparison:

    gated vs shadow

because both perform the same M5 reliability computation.

Baseline vs shadow remains a runtime/behavior-neutrality check.

## 7. Evaluation role

The first M5-B experiment is **intervention screening**, not a fresh
confirmation of the direct-flow cue.

The cue itself was already fresh-confirmed in M4-B.

For efficient screening, retain the same Bonn downstream sequences used/planned
for M5-A:

1. balloon2
2. moving_nonobstructing_box2
3. removing_nonobstructing_box

Because M5-B was proposed after observing M5-A outcomes on balloon2 and
moving_nonobstructing_box2, these runs must not be presented as an untouched
confirmatory test of the intervention.

If screening is promising, freeze M5-B and validate it on an untouched external
set, preferably TUM.

## 8. Primary metrics

Primary:
- ATE RMSE.

Secondary:
- PSNR;
- SSIM;
- LPIPS;
- L1 depth;
- number of original insertion requests;
- number rejected by M5-B;
- rejection fraction;
- confidence distribution of rejected/admitted frames;
- runtime.

## 9. Screening criterion

M5-B is promising if gated vs shadow:
- improves ATE on at least 2/3 screening sequences;
- does not catastrophically degrade the third;
- actually rejects a non-trivial but not dominant fraction of insertion
  requests.

If essentially no insertion is rejected, the test is uninformative.

If a very large fraction is rejected and performance collapses, stop v1 rather
than retuning the threshold on the same sequences.

## 10. Reproducibility

The repository still has partially uncontrolled stochastic point sampling.
Therefore seed-0 screening is only a mechanism screen.

If M5-B looks promising:
1. fix/audit stochastic point sampling;
2. repeat paired shadow/gated runs with seeds 0,1,2;
3. then run a fresh external validation, preferably TUM.

## 11. No-retuning rule

After outcomes are viewed, do not change:
- reliability feature;
- ECDF reference;
- 0.20 threshold;
- mandatory-frame guardrails;
- screening sequence set.

Any revised admission policy requires a new evaluation set.
