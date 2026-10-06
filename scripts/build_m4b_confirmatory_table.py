#!/usr/bin/env python3
"""Build an M4-B confirmatory table directly from shadow run directories.

This avoids any dependence on the placing-box M1 calibration-fold machinery.
It joins:
  m1_pose_uncertainty/
  m2a_pose_uncertainty/
  m3c_temporal_cycle/

and reconstructs the final frontend relative-pose target using the same
right-composed convention as audit_m1_relative_pose_reliability.py.
"""

import argparse
import csv
import math
from pathlib import Path

import torch

from utils.m2_uncertainty import SE3_log


def load_pt(path):
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(path, map_location="cpu")


def load_by_frame(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    out = {}
    for path in sorted(directory.glob("*.pt")):
        d = load_pt(path)
        out[int(d.get("frame", int(path.stem)))] = d
    return out


def as_T(x, name):
    if not isinstance(x, torch.Tensor) or tuple(x.shape) != (4, 4):
        raise ValueError(f"{name} must be a 4x4 tensor")
    T = x.detach().cpu().double()
    if not bool(torch.isfinite(T).all()):
        raise ValueError(f"{name} contains non-finite values")
    return T


def se3_error(T_est, T_gt):
    e = SE3_log(torch.linalg.inv(T_gt) @ T_est)
    return float(torch.linalg.norm(e[:3])), float(torch.linalg.norm(e[3:]))


def rotation_angle(T):
    R = T[:3, :3].double()
    c = torch.clamp((torch.trace(R) - 1.0) / 2.0, -1.0, 1.0)
    return float(torch.acos(c))


def parse_run(value):
    if "=" not in value:
        raise ValueError(f"Expected NAME=RUN_DIR, got {value!r}")
    name, path = value.split("=", 1)
    return name.strip(), Path(path)


def build_sequence(name, run_dir):
    m1 = load_by_frame(run_dir / "m1_pose_uncertainty")
    m2 = load_by_frame(run_dir / "m2a_pose_uncertainty")
    cyc = load_by_frame(run_dir / "m3c_temporal_cycle")

    frames = sorted(set(m1) & set(m2) & set(cyc))
    rows = []

    for frame in frames:
        a, b, c = m1[frame], m2[frame], cyc[frame]
        if not bool(c.get("valid", False)):
            continue
        if "T_rel_applied" not in a or "T_rel_gt" not in a:
            continue
        if "T_motion_prior" not in b or "T_final" not in b:
            continue

        T_applied = as_T(a["T_rel_applied"], "T_rel_applied")
        T_gt = as_T(a["T_rel_gt"], "T_rel_gt")
        T_prior = as_T(b["T_motion_prior"], "T_motion_prior")
        T_final = as_T(b["T_final"], "T_final")

        # Same algebra as the M1 relative-pose reliability audit:
        # T_prior = T_prev_used @ T_rel_applied
        T_prev_used = T_prior @ torch.linalg.inv(T_applied)
        T_rel_final = torch.linalg.inv(T_prev_used) @ T_final
        err_t, err_r = se3_error(T_rel_final, T_gt)

        fb = float(torch.as_tensor(a.get("fb_error_median_px", float("nan"))).reshape(()))
        flow = float(c["direct_flow_median_px"])
        motion_t = float(torch.linalg.norm(T_applied[:3, 3]))
        motion_r = rotation_angle(T_applied)

        vals = [fb, flow, motion_t, motion_r, err_t, err_r]
        if not all(math.isfinite(v) for v in vals):
            continue

        rows.append({
            "sequence": name,
            "frame": int(frame),
            "fb_error_median_px": fb,
            "direct_flow_median_px": flow,
            "applied_translation_norm_m": motion_t,
            "applied_rotation_angle_rad": motion_r,
            "slam_final_rel_error_t_m": err_t,
            "slam_final_rel_error_r_rad": err_r,
            "cycle_num_valid_pixels": int(c.get("num_valid_pixels", 0)),
            "u_cycle_median_px": float(c.get("u_cycle_median_px", float("nan"))),
        })

    if len(rows) < 20:
        raise RuntimeError(
            f"{name}: only {len(rows)} joined M4-B rows from {run_dir}"
        )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="+", required=True, help="NAME=RUN_DIR")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    all_rows = []
    seen = set()
    for spec in args.run:
        name, run_dir = parse_run(spec)
        if name in seen:
            raise ValueError(f"Duplicate sequence {name!r}")
        seen.add(name)
        rows = build_sequence(name, run_dir)
        all_rows.extend(rows)
        print(f"{name}: {len(rows)} rows")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    keys = list(all_rows[0].keys())
    with args.output.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
