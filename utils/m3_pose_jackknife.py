"""M3-A spatial delete-block jackknife pose-instability diagnostics.

This module is diagnostic-only.  It never mutates camera pose, masks, keyframes,
Gaussian state, optimizer state, or global RNG state.

The score source is deliberately independent of the M1 covariance construction:
for each spatial block, it re-runs the baseline robust pose estimator after
removing candidate static pixels in that block.

The resulting delete-one-block covariance is an estimator-stability diagnostic,
not a calibrated Bayesian posterior covariance.
"""

from pathlib import Path

import torch


def _grid_masks(height, width, rows, cols, device):
    rows = max(int(rows), 1)
    cols = max(int(cols), 1)
    masks = []
    for ry in range(rows):
        y0 = (ry * height) // rows
        y1 = ((ry + 1) * height) // rows
        for cx in range(cols):
            x0 = (cx * width) // cols
            x1 = ((cx + 1) * width) // cols
            mask = torch.zeros((height, width), dtype=torch.bool, device=device)
            mask[y0:y1, x0:x1] = True
            masks.append(
                {
                    "index": len(masks),
                    "row": ry,
                    "col": cx,
                    "bounds": [int(y0), int(y1), int(x0), int(x1)],
                    "mask": mask,
                }
            )
    return masks


def _safe_rms_sigma(P, sl):
    diag = torch.diagonal(P)[sl].clamp_min(0.0)
    return torch.sqrt(diag.mean())


class M3PoseJackknifeAudit:
    """Spatial delete-block pose-refit audit.

    Args:
        grid_rows/grid_cols: image partition used for delete-block refits.
        min_train_pixels: minimum remaining static support for a valid refit.
        min_removed_pixels: minimum static pixels that the held-out block must
            actually remove; this prevents empty-background blocks from being
            counted as informative jackknife replicates.
        robust_iters: number of IRLS iterations for the baseline refit.
    """

    def __init__(
        self,
        grid_rows=4,
        grid_cols=4,
        min_train_pixels=1000,
        min_removed_pixels=50,
        robust_iters=30,
    ):
        self.grid_rows = max(int(grid_rows), 1)
        self.grid_cols = max(int(grid_cols), 1)
        self.min_train_pixels = max(int(min_train_pixels), 1)
        self.min_removed_pixels = max(int(min_removed_pixels), 1)
        self.robust_iters = max(int(robust_iters), 1)

    @torch.no_grad()
    def evaluate_and_save(
        self,
        *,
        frame,
        depth,
        flow_px,
        K,
        static_mask,
        xi_full,
        fit_fn,
        save_dir,
    ):
        """Run delete-block refits and save a behavior-neutral payload."""

        if depth.ndim != 2:
            raise ValueError("depth must have shape [H,W]")
        H, W = depth.shape
        if tuple(static_mask.shape) != (H, W):
            raise ValueError("static_mask must have shape [H,W]")
        if tuple(flow_px.shape) != (2, H, W):
            raise ValueError("flow_px must have shape [2,H,W]")

        static_mask = static_mask.bool()
        xi_full = xi_full.detach().to(device=depth.device, dtype=depth.dtype).reshape(6)

        blocks = _grid_masks(
            H, W, self.grid_rows, self.grid_cols, depth.device
        )

        replicates = []
        for block in blocks:
            removed_mask = static_mask & block["mask"]
            removed = int(removed_mask.sum().item())
            train_mask = static_mask & (~block["mask"])
            train_count = int(train_mask.sum().item())

            record = {
                "index": int(block["index"]),
                "row": int(block["row"]),
                "col": int(block["col"]),
                "bounds": list(block["bounds"]),
                "removed_pixels": removed,
                "train_pixels": train_count,
                "valid": False,
                "reason": None,
            }

            if removed < self.min_removed_pixels:
                record["reason"] = "too_few_removed_pixels"
                replicates.append(record)
                continue
            if train_count < self.min_train_pixels:
                record["reason"] = "too_few_train_pixels"
                replicates.append(record)
                continue

            xi_leave = fit_fn(
                depth,
                flow_px,
                K,
                train_mask,
                robust=True,
                iters=self.robust_iters,
            )
            xi_leave = xi_leave.detach().to(
                device=depth.device, dtype=depth.dtype
            ).reshape(6)
            if not bool(torch.isfinite(xi_leave).all()):
                record["reason"] = "nonfinite_refit"
                replicates.append(record)
                continue

            delta = xi_leave - xi_full
            record.update(
                {
                    "valid": True,
                    "reason": "ok",
                    "xi": xi_leave.detach().cpu(),
                    "delta": delta.detach().cpu(),
                    "delta_translation_norm": float(
                        torch.linalg.norm(delta[:3]).detach().cpu()
                    ),
                    "delta_rotation_norm": float(
                        torch.linalg.norm(delta[3:]).detach().cpu()
                    ),
                }
            )
            replicates.append(record)

        valid = [r for r in replicates if r["valid"]]
        n = len(valid)
        payload = {
            "method": "m3_pose_delete_block_jackknife_v1",
            "frame": int(frame),
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "num_blocks": len(blocks),
            "num_valid_blocks": n,
            "min_train_pixels": self.min_train_pixels,
            "min_removed_pixels": self.min_removed_pixels,
            "robust_iters": self.robust_iters,
            "static_pixels": int(static_mask.sum().item()),
            "xi_full": xi_full.detach().cpu(),
            "replicates": replicates,
            "valid": False,
        }

        if n >= 3:
            X = torch.stack(
                [r["xi"].to(dtype=torch.float64) for r in valid], dim=0
            )
            mean = X.mean(dim=0)
            centered = X - mean
            P = ((n - 1.0) / n) * (centered.T @ centered)
            P = 0.5 * (P + P.T)
            eig = torch.linalg.eigvalsh(P)

            sigma_t = _safe_rms_sigma(P, slice(0, 3))
            sigma_r = _safe_rms_sigma(P, slice(3, 6))
            max_t = max(r["delta_translation_norm"] for r in valid)
            max_r = max(r["delta_rotation_norm"] for r in valid)

            payload.update(
                {
                    "valid": True,
                    "xi_leaveout_mean": mean.cpu(),
                    "P_jackknife": P.cpu(),
                    "eig_jackknife": eig.cpu(),
                    "sigma_jk_translation": float(sigma_t.cpu()),
                    "sigma_jk_rotation": float(sigma_r.cpu()),
                    "max_leaveout_delta_translation": float(max_t),
                    "max_leaveout_delta_rotation": float(max_r),
                    "mean_leaveout_delta_translation": float(
                        sum(r["delta_translation_norm"] for r in valid) / n
                    ),
                    "mean_leaveout_delta_rotation": float(
                        sum(r["delta_rotation_norm"] for r in valid) / n
                    ),
                }
            )

        out_dir = Path(save_dir) / "m3_pose_jackknife"
        out_dir.mkdir(parents=True, exist_ok=True)
        torch.save(payload, out_dir / f"{int(frame):06d}.pt")
        return payload
