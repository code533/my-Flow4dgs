# M4-A stage runbook

Status: ready for offline execution.

## Goal

Build a per-frame development table from existing M3-C and matched reliability
outputs, then test whether simple runtime descriptors modulate the usefulness of
temporal-cycle inconsistency.

No SLAM rerun is required.

## Branch

    feature/m4-regime-analysis

## Step 0: checkout

    git fetch
    git checkout feature/m4-regime-analysis
    git pull

Syntax check:

    python -m py_compile       scripts/build_m4_regime_table.py       scripts/audit_m4_regime_interactions.py

## Step 1: build the regime table

Use the same three M3-C run directories and matched relative-reliability CSVs
that produced the M3-C result.

    python scripts/build_m4_regime_table.py       --sequence         box1=<BOX1_RUN>/m3c_temporal_cycle,results/m3c_box1_relative_reliability.csv         box2=<BOX2_RUN>/m3c_temporal_cycle,results/m3c_box2_relative_reliability.csv         box3=<BOX3_RUN>/m3c_temporal_cycle,results/m3c_box3_relative_reliability.csv       --output results/m4_regime_table.csv

Expected:

    box1: 61 rows
    box2: 61 rows
    box3: 61 rows

## Step 2: run the interaction audit

    python scripts/audit_m4_regime_interactions.py       results/m4_regime_table.csv       --ridge-lambda 0.001       --output results/m4_regime_interactions.json

Primary descriptors are frozen for this first pass:

    direct_flow_median_px
    valid_extent
    log10_condition
    motion_scale_joint

Secondary descriptors are printed separately and are exploratory only.

## Step 3: what to send back

Send the full terminal summary from the interaction audit.

Especially preserve, for every primary descriptor and both translation/rotation:

    dFB
    pos
    dCycle
    pos
    beta_int
    sign(+/-)

Do not tune descriptors or ridge lambda after seeing this output.

## Interpretation rules

This is a development/hypothesis-generation stage, not confirmatory evidence.

A descriptor becomes a candidate for fresh-sequence validation only if:
- interaction sign is reasonably stable across LOSO folds;
- regime model improves over FB on at least 2/3 development held-out sequences;
- improvement is not exclusively due to held-out box3;
- the pattern is coherent rather than a single-target accident.

If none of the four primary descriptors show such a pattern, do not mine the
secondary descriptors until a separate decision is made.

## Stage-completion document

After interpreting the audit, commit:

    docs/m4a_regime_interaction_results.md

The document must explicitly state that box1/box2/box3 were used for hypothesis
generation and cannot serve as final validation for a discovered regime rule.
