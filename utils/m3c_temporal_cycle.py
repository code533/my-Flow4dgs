"""M3-C three-frame temporal-cycle inconsistency diagnostics.

Shadow-only source-discovery module.  Given current->previous, previous->older,
and current->older flow in pixel units, compare the direct two-frame flow with
the composition of the two adjacent flows.
"""

from pathlib import Path
import torch
import torch.nn.functional as F


def _mesh(height, width, device, dtype):
    y, x = torch.meshgrid(
        torch.arange(height, device=device, dtype=dtype),
        torch.arange(width, device=device, dtype=dtype),
        indexing="ij",
    )
    return x, y


def _sample_flow(flow_px, x, y):
    """Bilinearly sample [2,H,W] flow at pixel coordinates x,y."""
    _, H, W = flow_px.shape
    gx = 2.0 * x / max(W - 1, 1) - 1.0
    gy = 2.0 * y / max(H - 1, 1) - 1.0
    grid = torch.stack([gx, gy], dim=-1)[None]
    return F.grid_sample(
        flow_px[None],
        grid,
        mode="bilinear",
        padding_mode="zeros",
        align_corners=True,
    )[0]


class M3CTemporalCycleAudit:
    def __init__(self, min_pixels=500):
        self.min_pixels = max(int(min_pixels), 1)

    @torch.no_grad()
    def evaluate_and_save(
        self,
        *,
        frame,
        flow_t_to_tm1_px,
        flow_tm1_to_tm2_px,
        flow_t_to_tm2_px,
        static_mask,
        save_dir,
    ):
        f10 = flow_t_to_tm1_px.double()
        f21 = flow_tm1_to_tm2_px.double()
        f20 = flow_t_to_tm2_px.double()

        if f10.shape != f21.shape or f10.shape != f20.shape:
            raise ValueError("M3-C flows must share shape [2,H,W]")
        if f10.ndim != 3 or f10.shape[0] != 2:
            raise ValueError("M3-C flows must have shape [2,H,W]")

        _, H, W = f10.shape
        if tuple(static_mask.shape) != (H, W):
            raise ValueError("static_mask must have shape [H,W]")

        x, y = _mesh(H, W, f10.device, f10.dtype)

        qx = x + f10[0]
        qy = y + f10[1]
        q_in = (
            (qx >= 0.0) & (qx <= W - 1)
            & (qy >= 0.0) & (qy <= H - 1)
        )

        f21_at_q = _sample_flow(f21, qx, qy)
        comp = f10 + f21_at_q

        q2x = qx + f21_at_q[0]
        q2y = qy + f21_at_q[1]
        comp_target_in = (
            (q2x >= 0.0) & (q2x <= W - 1)
            & (q2y >= 0.0) & (q2y <= H - 1)
        )

        direct_x = x + f20[0]
        direct_y = y + f20[1]
        direct_target_in = (
            (direct_x >= 0.0) & (direct_x <= W - 1)
            & (direct_y >= 0.0) & (direct_y <= H - 1)
        )

        residual = f20 - comp
        cycle = torch.linalg.norm(residual, dim=0)

        finite = (
            torch.isfinite(f10).all(dim=0)
            & torch.isfinite(f21_at_q).all(dim=0)
            & torch.isfinite(f20).all(dim=0)
            & torch.isfinite(cycle)
        )
        valid = (
            static_mask.bool()
            & q_in
            & comp_target_in
            & direct_target_in
            & finite
        )
        n = int(valid.sum().item())

        payload = {
            "method": "m3c_temporal_cycle_inconsistency_v1",
            "frame": int(frame),
            "num_valid_pixels": n,
            "valid": n >= self.min_pixels,
        }

        if n >= self.min_pixels:
            cv = cycle[valid].float()
            q = torch.quantile(
                cv,
                torch.tensor([0.50, 0.90, 0.95], device=cv.device),
            )
            direct_mag = torch.linalg.norm(f20, dim=0)[valid].float()
            comp_mag = torch.linalg.norm(comp, dim=0)[valid].float()
            payload.update(
                {
                    "u_cycle_median_px": float(q[0].cpu()),
                    "u_cycle_mean_px": float(cv.mean().cpu()),
                    "u_cycle_q90_px": float(q[1].cpu()),
                    "u_cycle_q95_px": float(q[2].cpu()),
                    "u_cycle_max_px": float(cv.max().cpu()),
                    "direct_flow_median_px": float(direct_mag.median().cpu()),
                    "composed_flow_median_px": float(comp_mag.median().cpu()),
                }
            )

        out_dir = Path(save_dir) / "m3c_temporal_cycle"
        out_dir.mkdir(parents=True, exist_ok=True)
        torch.save(payload, out_dir / f"{int(frame):06d}.pt")
        return payload
