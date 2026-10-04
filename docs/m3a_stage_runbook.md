# M3-A stage runbook

Status: ready for first execution.

This document records the exact execution order for the first M3-A experiment.
Every later stage should add a new stage note rather than silently changing this
protocol.

## Goal of this stage

Test whether spatial delete-block pose instability contains held-out reliability
information beyond forward/backward flow consistency.

This stage is diagnostic only.  It must not modify tracking, motion masks,
keyframes, mapping, Gaussian insertion/pruning, or deformation.

## Branch

    feature/m3-source-discovery

Base:

    feature/m1-uncertainty-aware-mapping

## Experiment configs

- configs/rgbd/bonn/placing_box_m3_jackknife.yaml
- configs/rgbd/bonn/placing_box2_m3_jackknife.yaml
- configs/rgbd/bonn/placing_box3_m3_jackknife.yaml

Each config audits only a +/-30-frame transition neighborhood around dystart.

M2-A is enabled only as a shadow logger so that the matched final frontend pose
can be reconstructed by the existing relative-pose reliability audit.
M2-A calibration is disabled and M2-A2 is disabled.

## Step 0: environment and branch check

    git fetch
    git checkout feature/m3-source-discovery
    git pull

Confirm:

    git status
    python -m py_compile       utils/m3_pose_jackknife.py       scripts/audit_m3_jackknife_incremental.py       utils/slam_frontend.py

Expected: clean tree and no Python syntax error.

## Step 1: single-sequence smoke run

Run box1 first:

    python slam.py       --config configs/rgbd/bonn/placing_box_m3_jackknife.yaml       --eval --dynamic       --exp_name m3a_jk_box1       --save_results 0       --seed 0

After the run, locate the newly created run directory under:

    results/bonn/m3a_jk_box1/

The run directory must contain at least:

    config.yml
    outputs.txt
    m1_pose_uncertainty/
    m2a_pose_uncertainty/
    m3_pose_jackknife/

Check the M3 diagnostic count:

    find <BOX1_RUN>/m3_pose_jackknife -name '*.pt' | wc -l

For the current [211,271] range, approximately 61 frame files are expected if
all frames enter the flow-camera path.

Do not continue if the directory is missing, payloads are invalid, or baseline
tracking crashes.

## Step 2: inspect one M3 payload

Use Python:

    python - <<'PY'
    import glob, torch
    p = sorted(glob.glob("<BOX1_RUN>/m3_pose_jackknife/*.pt"))[0]
    d = torch.load(p, map_location="cpu", weights_only=False)
    print("file:", p)
    print("frame:", d["frame"])
    print("valid:", d["valid"])
    print("valid blocks:", d["num_valid_blocks"], "/", d["num_blocks"])
    print("sigma_t:", d.get("sigma_jk_translation"))
    print("sigma_r:", d.get("sigma_jk_rotation"))
    print("eig:", d.get("eig_jackknife"))
    PY

Required sanity:
- valid is True for most audited frames;
- num_valid_blocks is normally close to 16;
- sigma values are finite and non-negative;
- P_jackknife is finite/symmetric/PSD up to numerical tolerance.

If many blocks are rejected because too few static pixels remain, stop and
inspect support before changing thresholds.

## Step 3: complete the three transition-neighborhood runs

Box2:

    python slam.py       --config configs/rgbd/bonn/placing_box2_m3_jackknife.yaml       --eval --dynamic       --exp_name m3a_jk_box2       --save_results 0       --seed 0

Box3:

    python slam.py       --config configs/rgbd/bonn/placing_box3_m3_jackknife.yaml       --eval --dynamic       --exp_name m3a_jk_box3       --save_results 0       --seed 0

Record the exact three generated run directories.  Do not select runs by ATE or
by jackknife result.

## Step 4: generate matched relative-pose reliability CSVs

For each run, use the existing M1 signal/calibration report and the matching
fold.  Example for box1:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX1_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box       --dystart 241       --output results/m3a_box1_relative_reliability.json

Box2:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX2_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box2       --dystart 262       --output results/m3a_box2_relative_reliability.json

Box3:

    python scripts/audit_m1_relative_pose_reliability.py       <BOX3_RUN>       --signal-file results/m1_mapping_signal_bonn_loso.json       --fold placing_box3       --dystart 348       --output results/m3a_box3_relative_reliability.json

Each command also creates a CSV with the same basename.

## Step 5: run the M3 beyond-FB incremental audit

    python scripts/audit_m3_jackknife_incremental.py       --sequence         box1=<BOX1_RUN>/m3_pose_jackknife,results/m3a_box1_relative_reliability.csv         box2=<BOX2_RUN>/m3_pose_jackknife,results/m3a_box2_relative_reliability.csv         box3=<BOX3_RUN>/m3_pose_jackknife,results/m3a_box3_relative_reliability.csv       --block-len 20       --bootstrap 1000       --seed 0       --ridge-lambda 0.001       --output results/m3a_jackknife_incremental.json

Primary values to record:
- raw JK/error Spearman;
- raw FB/error Spearman;
- partial Spearman rho(JK,error | FB) and CI;
- LOSO rho(FB,error);
- LOSO rho(FB+JK,error);
- LOSO delta-rho;
- macro delta-rho for translation and rotation.

## Decision rule

Proceed only if M3-A gives a materially larger held-out increment than M1.

Resource-allocation gate:
- target macro LOSO delta-rho around +0.03 to +0.05 or larger;
- positive direction on at least 2/3 sequences;
- no result may depend on redefining the signal after viewing a held-out fold.

If the signal is again approximately +0.00x, stop M3-A and move to the next
independent source candidate (appearance-perturbation flow disagreement or
three-frame temporal-cycle inconsistency).

## Stage-completion record

After the audit finishes, add a new document:

    docs/m3a_jackknife_results.md

It must contain:
- date and branch/commit;
- exact run directories and seeds;
- configs used;
- sanity checks;
- per-sequence partial correlations;
- per-fold LOSO delta-rho;
- macro summary;
- pass/fail decision under the pre-specified gate;
- next action.

Commit the result document even if the result is negative.
