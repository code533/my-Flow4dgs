# M5-B balloon2 mechanism sanity: insertion gate activation

Status: mechanism sanity passed; gate activation is high.

Date: 2026-10-07

Sequence:

    rgbd_bonn_balloon2

Run type:

    gated

Frozen threshold:

    confidence < 0.20

## Observed insertion-decision summary

    requests: 94
    admitted: 47
    rejected: 47
    rejection fraction: 0.500

Confidence over insertion-request frames:

    min    = 0.001
    median = 0.18306010928961747
    max    = 1.0

Direct-flow magnitude over insertion-request frames:

    min    = 0.7676016385769969 px
    median = 8.140151034046639 px
    max    = 39.598089957082934 px

Decision reasons:

    dystart         = 1
    low_reliability = 47
    reliable        = 46

No rejected decision was caused by an invalid score.

The configured dystart frame was admitted by the mandatory-frame guardrail.

## Mechanism verdict

The implementation sanity check passes:

- all 47 rejections are due to the frozen low-reliability rule;
- no invalid-score frame is rejected;
- dystart is not rejected;
- the gate is non-trivially active.

## Important distribution-shift observation

The 0.20 confidence threshold corresponds to the least reliable 20% of the
development-frame ECDF distribution.

It does **not** imply that 20% of Gaussian insertion requests will be rejected.

On balloon2, the insertion-request subset is strongly shifted toward lower
reliability:

    median request confidence = 0.183 < 0.20.

Therefore 47/94 = 50% of insertion requests are rejected.

This means optional Gaussian insertion requests occur disproportionately on
frames with large direct flow / low predicted pose reliability.

That is scientifically interesting, but it also means M5-B v1 is a relatively
strong intervention on balloon2.

## Protocol consequence

Do not retune the threshold after observing this activation rate.

Proceed with the frozen 0.20 threshold and evaluate the downstream gated-vs-
shadow result.

Interpret any large performance change together with the 50% rejection rate.

If performance collapses, M5-B v1 should be considered too destructive under
its frozen rule; do not rescue it by threshold tuning on balloon2.

If performance improves, the result supports the hypothesis that insertion
requests are concentrated on structurally risky frames and that suppressing a
substantial subset can protect the map.

A later method revision, if justified on a new validation set, may distinguish
frame-level reliability percentiles from insertion-request-conditioned
percentiles. That is not part of M5-B v1.
