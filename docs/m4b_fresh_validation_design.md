# M4-B: fresh-sequence confirmatory validation of direct-flow reliability

Status: design frozen before fresh-sequence outcomes are inspected.

## 1. Background

M4-A2 showed that the strong development-set gain previously attributed to a
cycle/flow regime interaction is actually explained by the main effect of

    direct_flow_median_px.

Once direct flow magnitude is included, temporal-cycle inconsistency and the
cycle*flow interaction add no stable value.

M4-A3 then showed that direct-flow reliability survives controls for:

    FB consistency
    ||t_rel||
    relative rotation angle.

Development-set macro LOSO improvements after adding direct flow were:

    translation: +0.2775, positive 3/3
    rotation:    +0.3493, positive 3/3.

However box1/box2/box3 were used to discover this cue and therefore cannot
serve as confirmatory validation.

M4-B is the first strict fresh-sequence test.

## 2. Frozen fresh sequences

Fresh validation sequences are selected before their M4-B pose-error results are
inspected.

They are:

1. balloon

       dataset: rgbd_bonn_balloon
       dystart: 32
       audit window: [2,62]

2. remove_box

       dataset: rgbd_bonn_removing_nonobstructing_box
       dystart: 170
       audit window: [140,200]

3. synchronous2

       dataset: rgbd_bonn_synchronous2
       dystart: 120
       audit window: [90,150]

The same deterministic rule used in development is applied:

    [dystart-30, dystart+30].

Each sequence therefore contributes up to 61 audited frames.

These sequences were not used in M1/M3/M4 direct-flow discovery.

## 3. Frozen signal

The candidate signal remains exactly:

    direct_flow_median_px

from the M3-C diagnostic definition.

To preserve the development definition exactly, M4-B reuses the M3-C
three-frame diagnostic pipeline and reads the direct t->t-2 flow magnitude over
the same valid support used by M3-C.

Temporal-cycle residual itself is not part of the candidate model.

No alternative flow summary (mean, q90, q95, normalized flow) may replace the
primary signal after fresh outcomes are observed.

## 4. Frozen models

Development sequences:

    box1
    box2
    box3

are used once to fit model coefficients.

For each target separately, percentile ranks are computed within sequence before
development rows are pooled.

Comparator model:

    M0:
        error_rank ~
            FB_rank
            + translation_motion_rank
            + rotation_motion_rank

Candidate model:

    M1:
        error_rank ~
            FB_rank
            + translation_motion_rank
            + rotation_motion_rank
            + direct_flow_rank

Ridge lambda is frozen at:

    0.001.

No coefficients are fitted on fresh validation sequences.

Fresh-sequence feature ranks are computed within each fresh sequence and passed
through the development-trained models unchanged.

## 5. Targets

Primary targets are unchanged:

    slam_final_rel_error_t_m
    slam_final_rel_error_r_rad

The primary fresh-sequence metric is:

    delta-rho_flow =
        Spearman(pred_M1, error)
        -
        Spearman(pred_M0, error).

This is reported separately for translation and rotation.

## 6. Confirmatory gate

M4-B passes only if the fresh validation result is both directionally consistent
and practically meaningful.

Frozen gate:

- macro mean delta-rho_flow >= +0.05 for at least one primary target;
- positive delta-rho on at least 2/3 fresh sequences for that target;
- the other target must not show a large systematic degradation
  (macro delta < -0.05);
- a positive conclusion may not rely on a single fresh sequence.

A stronger result is positive 2/3 or 3/3 for both translation and rotation.

If the gate fails, the direct-flow cue remains a development-set observation and
must not be promoted to a general reliability signal.

## 7. Statistical uncertainty

For each fresh sequence, use a moving-block bootstrap over frames to estimate a
95% interval for:

    delta-rho_flow.

Frozen bootstrap settings:

    block length = 20
    bootstrap samples = 1000
    seed = 0.

Bootstrap intervals are descriptive because only three fresh sequences are
available; the pass/fail gate is based on the pre-specified directional and
macro criteria above.

## 8. Behavior isolation

Fresh M4-B runs are shadow-only.

They do not modify:

- baseline optical flow;
- camera pose;
- motion masks;
- keyframes;
- mapping;
- Gaussian state.

M1 is enabled to log FB consistency and T_rel_applied.
M2-A is enabled only as a shadow logger for the matched final frontend pose.
M2-A calibration and M2-A2 are disabled.
M3-C is enabled only to preserve the exact direct_flow_median_px definition.

## 9. No-retuning rule

After any fresh result is inspected, do not change:

- sequence set;
- audit windows;
- direct-flow statistic;
- motion controls;
- ridge lambda;
- bootstrap settings;
- pass/fail gate.

Any subsequent modification would require a new independent validation set.

## 10. Stage outputs

Fresh runs should produce:

    m1_pose_uncertainty/
    m2a_pose_uncertainty/
    m3c_temporal_cycle/

Offline outputs:

    results/m4b_fresh_regime_table.csv
    results/m4b_fresh_confirmatory.json

Final stage record:

    docs/m4b_fresh_validation_results.md

must be committed whether the result is positive or negative.
