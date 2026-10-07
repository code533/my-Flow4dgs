# M5-C result: reliability-aware soft Gaussian initialization

Status: **STOP — no meaningful downstream effect on rapid-development sequence**

Date: 2026-10-07

Branch:

    feature/m5c-soft-opacity

Development sequence:

    rgbd_bonn_balloon2

Primary comparison:

    soft_opacity vs shadow

## Frozen intervention

For ordinary optional insertions with a valid M5 reliability score:

    alpha_0 = min(0.5, confidence)

Baseline opacity remained 0.5 for initialization, dynamic initialization, and
invalid/missing M5 scores.

## Mechanism activation

The intervention was strong:

    logged insertion calls = 96
    M5-C applied calls     = 94
    attenuated calls       = 78

Therefore:

    78/96 = 81.25%

of all logged insertion calls were initialized below the baseline opacity.

The median applied opacity was approximately:

    0.183

versus baseline:

    0.5.

Thus the absence of an end-task effect cannot be explained by an intervention
that was too weak to change Gaussian initialization.

## End-task outcome

The paired shadow and soft-opacity runs produced essentially unchanged final
performance according to the reported ATE / rendering / depth metrics.

Exact numeric values were not included in the stage report available when this
document was committed, so no numbers are invented here.

The correct conclusion is qualitative:

> despite strong reliability-dependent attenuation of newly inserted Gaussian
> opacity, downstream SLAM performance remained essentially unchanged.

## Interpretation

M5-C provides evidence that initial Gaussian opacity is not a sensitive
downstream lever for the confirmed frame-level direct-flow reliability cue.

Together with M5-A and M5-B screening, three different map-side uses have now
been explored:

1. continuous RGB-D mapping-loss weighting;
2. hard Gaussian insertion rejection;
3. soft Gaussian initialization confidence.

None has produced a clear, robust downstream benefit.

This does not invalidate the M4-B finding that direct-flow magnitude predicts
local relative-pose error on fresh sequences.

Instead it suggests:

> the map construction stage is relatively robust to the local pose-error
> variation captured by the direct-flow reliability cue.

In particular, the Gaussian map appears able to absorb or later compensate for
substantial changes in:
- per-frame mapping weight;
- insertion frequency;
- initial opacity.

## Decision

Stop M5-C.

Do not tune on balloon2:
- opacity floor;
- exponent;
- nonlinear transfer;
- pivot;
- frame-specific thresholds.

## Research direction after M5-C

The next intervention should move from the map side toward the source of the
confirmed error signal: camera tracking.

A promising next question is:

> Can the confirmed reliability cue identify frames that need stronger or
> alternative pose refinement?

A minimal next-stage intervention should modify only tracking effort/trust,
rather than map structure.

Examples to evaluate in a new design:
- extra pose-refinement iterations on low-reliability frames;
- fallback from flow-derived motion initialization to a safer prior;
- reliability-aware blend between flow motion and rendering-based pose
  refinement.

Only one mechanism should be tested at a time.

The first tracking-side stage should again use low-cost balloon2-only rapid
development, followed by a small external validation only if the mechanism is
clearly beneficial.
