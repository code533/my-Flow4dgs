# M5-A next step: variance and intervention-alignment audit

Status: planned before changing the M5 reliability transform.

## Why this audit is needed

The first two M5-A sequence results have opposite weighted-vs-shadow ATE
directions:

- balloon2: weighted worse than shadow;
- moving_nonobstructing_box2: weighted better than shadow, but almost identical
  to baseline.

At the same time baseline and shadow themselves differ noticeably.

The repository contains stochastic point-sampling paths that are not completely
controlled by the experiment seed.  Therefore method effect and execution
variance must be separated before changing the intervention.

## Step 1: finish the frozen third sequence

Complete removing_nonobstructing_box baseline/shadow/weighted at seed 0.

Do not change any M5 parameters before this result is collected.

## Step 2: quantify M5 intervention strength

For weighted runs record:
- distribution of m5_mapping_confidence;
- actual per-window RGB-D weights;
- weight standard deviation;
- min/max weight;
- effective sample size
      ESS = (sum w)^2 / sum(w^2).

If weights stay close to one, a small end-task effect may simply mean the
intervention is weak after window normalization.

## Step 3: reproducibility audit

Before a downstream claim, remove or explicitly control stochastic point
sampling so paired shadow/weighted runs can share the same random decisions.

At minimum audit:
- Open3D random_down_sample;
- np.random.default_rng() created without an explicit seed;
- multiprocessing/CUDA nondeterminism.

Then repeat paired shadow/weighted runs with predeclared seeds 0,1,2.

Primary statistic should be paired per-seed ATE difference:

    Delta ATE_s = ATE_weighted,s - ATE_shadow,s.

Report mean, standard deviation, and all individual seed differences.

## Step 4: M5-A decision

If the paired effect is smaller than or inconsistent relative to run variance,
declare M5-A mapping weighting unsupported.

Do not rescue M5-A by tuning:
- ECDF exponent;
- confidence temperature;
- clip bounds;
- sequence-specific transforms.

## Step 5: next intervention if M5-A fails

A failure of mapping weighting does not invalidate the M4-B reliability cue.

The cue predicts local pose reliability, while M5-A acts only on the RGB-D
mapping loss after a frame has already been tracked, accepted as a keyframe,
and may already have inserted Gaussians.

Therefore the next intervention should move closer to the failure mechanism.

Preferred candidate:

    M5-B: reliability-aware keyframe / Gaussian-insertion admission

Keep tracking unchanged. Use the frozen direct-flow reliability cue only to
prevent very low-reliability frames from contaminating map structure.

A second candidate, after admission gating:

    reliability-aware tracking fallback / motion-prior trust

Do not activate both at once.
