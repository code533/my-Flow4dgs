# M5-C balloon2 mechanism sanity: soft-opacity activation

Status: mechanism sanity passed; intervention is strong.

Date: 2026-10-07

Sequence:

    rgbd_bonn_balloon2

Frozen rule:

    alpha_0 = min(0.5, confidence)

for ordinary optional insertions with valid M5 reliability.

## Observed summary

    rows: 96
    m5c_applied_rows: 94
    m5c_applied_fraction: 0.9791666666666666

All insertion calls:

    alpha min    = 0.001
    alpha median = 0.19672131147540983
    alpha max    = 0.5

M5-C-applied insertion calls:

    alpha min    = 0.001
    alpha median = 0.18306010928961747
    alpha max    = 0.5

Applied reliability confidence:

    min    = 0.001
    median = 0.18306010928961747
    max    = 1.0

Rows with attenuated opacity (<0.5):

    78

## Mechanism verdict

The implementation behaves as designed.

- 94/96 insertion calls use the M5-C rule.
- The two non-applied calls are consistent with initialization/dynamic-init
  guardrails.
- No opacity exceeds the baseline alpha=0.5.
- The applied alpha exactly follows the frozen reliability confidence until the
  baseline cap at 0.5.
- 78/96 = 81.25% of all logged insertion calls are attenuated.
- 78/94 = 82.98% of M5-C-applied calls are attenuated.

## Important interpretation

M5-C is not a weak intervention on balloon2.

The median applied opacity is only:

    0.1831

compared with the baseline:

    0.5.

Thus the typical affected insertion starts with roughly 37% of the baseline
opacity.

As observed in M5-B, insertion-request frames are strongly biased toward low
direct-flow reliability relative to the full development-frame distribution.

This makes M5-C a strong but continuous map-trust intervention.

## Protocol consequence

Do not retune the mapping after inspecting this activation rate.

Proceed with the frozen soft-opacity run and compare against the paired shadow
run.

If downstream performance changes little despite this strong opacity
attenuation, that will be evidence that initial Gaussian opacity is not a
sensitive downstream lever for the confirmed frame-level reliability cue.

If performance improves clearly, M5-C can be frozen for a small external
validation.

If performance degrades, stop M5-C rather than adding an opacity floor or
changing the 0.5 pivot on balloon2.
