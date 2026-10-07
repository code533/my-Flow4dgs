# M5-A status at M5-B branch point

Status: **PAUSED / INCONCLUSIVE**

Date: 2026-10-07

M5-A tested whether the fresh-confirmed direct-flow reliability cue should
reweight per-view RGB-D mapping loss.

Observed seed-0 interim results:

- balloon2: weighted ATE worse than shadow;
- moving_nonobstructing_box2: weighted ATE better than shadow, but close to
  baseline and within the scale of run-to-run variation.

The repository still contains partially uncontrolled stochastic point sampling,
so these two single-run comparisons do not support either a positive or a
negative downstream claim.

M5-A is therefore paused rather than declared failed.

No M5-A transform parameter was retuned after observing these outcomes.

The current branch starts a different intervention:

    M5-B: reliability-aware Gaussian insertion admission

using the same frozen direct-flow reliability source.
