# M5-B interim result: balloon2, seed 0

Status: **INTERIM — weak negative downstream effect**

Date: 2026-10-07

Sequence:

    rgbd_bonn_balloon2

Primary comparison:

    gated vs shadow

The gated run used the frozen M5-B rule:

    reject optional Gaussian insertion if confidence < 0.20

Observed mechanism activation:

    insertion requests = 94
    rejected           = 47
    rejection fraction = 50%

## Reported end-task metrics

| run | ATE | PSNR | SSIM | LPIPS | L1 depth |
|---|---:|---:|---:|---:|---:|
| shadow | 0.05275 | 28.0558 | 0.8748 | 0.202 | 0.05196 |
| gated | 0.05498 | 27.8020 | 0.8708 | 0.212 | 0.05530 |

## Gated vs shadow

ATE:

    absolute change = +0.00223
    relative change ≈ +4.23%

Higher ATE is worse.

Other metrics:

    PSNR     = -0.2538 dB
    SSIM     = -0.0040
    LPIPS    = +0.010
    L1 depth = +0.00334

All reported directions are weakly worse for gated vs shadow.

## Interpretation

The effect is not catastrophic despite suppressing half of all optional
insertion requests.

This indicates substantial redundancy in the baseline map-growth path: many
optional insertion events can be removed without causing a dramatic failure.

However, the frozen hard-gating rule does not improve balloon2.  The available
metrics are directionally consistent with a small degradation.

Therefore balloon2 provides weak negative evidence for M5-B v1.

Do not retune the 0.20 threshold after this result.

## Mechanistic implication

M4-B showed that direct-flow magnitude predicts local relative-pose reliability.
M5-B asks a different question: whether low-predicted-reliability frames should
be prevented from inserting Gaussians.

The balloon2 result suggests these are not equivalent statements.

Possible explanations include:

- low-reliability frames still contain useful scene coverage;
- insertion is robust to moderate pose uncertainty;
- later mapping can correct or absorb imperfect insertions;
- frame-level reliability is too coarse for a binary insertion decision;
- only part of the newly inserted geometry may be risky, so all-or-nothing
  rejection discards useful information.

These are hypotheses, not conclusions from one sequence.

## Next action

Continue the frozen M5-B screening protocol on:

    moving_nonobstructing_box2
    removing_nonobstructing_box

without changing the threshold or admission rule.

If gated is not beneficial on at least 2/3 screening sequences, stop M5-B v1.

A failure of M5-B does not invalidate the M4-B direct-flow reliability cue; it
would indicate that hard Gaussian-insertion rejection is not the appropriate
downstream use of that cue.
