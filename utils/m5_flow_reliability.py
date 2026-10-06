"""Runtime direct-flow reliability signal for M5-A.

The reference distribution is built from development-sequence
direct_flow_median_px values only. Runtime scoring is causal and uses no
sequence-level future ranks or ground truth.
"""

import bisect
import json
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
    """Bilinearly sample [2,H,W] pixel flow at x,y pixel coordinates."""
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


def direct_flow_on_m3c_support(
    flow_t_to_tm1_px,
    flow_tm1_to_tm2_px,
    flow_t_to_tm2_px,
    static_mask,
):
    """Return direct-flow magnitude and exact M3-C valid-support mask."""
    f10 = flow_t_to_tm1_px.double()
    f21 = flow_tm1_to_tm2_px.double()
    f20 = flow_t_to_tm2_px.double()

    if f10.shape != f21.shape or f10.shape != f20.shape:
        raise ValueError("M5 flows must share shape [2,H,W]")
    if f10.ndim != 3 or f10.shape[0] != 2:
        raise ValueError("M5 flows must have shape [2,H,W]")

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

    finite = (
        torch.isfinite(f10).all(dim=0)
        & torch.isfinite(f21_at_q).all(dim=0)
        & torch.isfinite(f20).all(dim=0)
    )
    valid = (
        static_mask.bool()
        & q_in
        & comp_target_in
        & direct_target_in
        & finite
    )
    direct_mag = torch.linalg.norm(f20, dim=0)
    return direct_mag, valid


class M5FlowReliability:
    def __init__(self, reference_file, eps=1e-3, min_pixels=500):
        self.reference_file = Path(reference_file).expanduser()
        self.eps = float(eps)
        self.min_pixels = max(int(min_pixels), 1)
        if not (0.0 < self.eps <= 1.0):
            raise ValueError("m5 eps must be in (0,1]")

        with self.reference_file.open("r") as f:
            ref = json.load(f)
        if ref.get("method") != "m5_direct_flow_ecdf_reference_v1":
            raise ValueError(
                "Expected m5_direct_flow_ecdf_reference_v1, got "
                f"{ref.get('method')!r}"
            )
        values = [float(v) for v in ref.get("sorted_direct_flow_median_px", [])]
        if len(values) < 20:
            raise ValueError("M5 reference needs at least 20 development values")
        if any((not torch.isfinite(torch.tensor(v))) or v < 0 for v in values):
            raise ValueError("M5 reference values must be finite and non-negative")
        if values != sorted(values):
            raise ValueError("M5 reference values are not sorted")
        self.values = values
        self.n = len(values)

    def ecdf(self, direct_flow_median_px):
        d = float(direct_flow_median_px)
        idx = bisect.bisect_right(self.values, d)
        return float(idx / self.n)

    def confidence_from_direct_flow(self, direct_flow_median_px):
        q = self.ecdf(direct_flow_median_px)
        confidence = max(1.0 - q, self.eps)
        return q, confidence

    @torch.no_grad()
    def evaluate(
        self,
        *,
        flow_t_to_tm1_px,
        flow_tm1_to_tm2_px,
        flow_t_to_tm2_px,
        static_mask,
    ):
        direct_mag, valid = direct_flow_on_m3c_support(
            flow_t_to_tm1_px,
            flow_tm1_to_tm2_px,
            flow_t_to_tm2_px,
            static_mask,
        )
        n = int(valid.sum().item())
        out = {
            "valid": n >= self.min_pixels,
            "num_valid_pixels": n,
            "direct_flow_median_px": None,
            "training_ecdf": None,
            "confidence": 0.5,
        }
        if n < self.min_pixels:
            return out
        d = float(direct_mag[valid].median().cpu())
        q, c = self.confidence_from_direct_flow(d)
        out.update(
            {
                "direct_flow_median_px": d,
                "training_ecdf": q,
                "confidence": c,
            }
        )
        return out

    def save(self, payload, frame, save_dir):
        out_dir = Path(save_dir) / "m5_flow_reliability"
        out_dir.mkdir(parents=True, exist_ok=True)
        d = dict(payload)
        d.update(
            {
                "method": "m5_direct_flow_reliability_v1",
                "frame": int(frame),
                "reference_file": str(self.reference_file),
            }
        )
        torch.save(d, out_dir / f"{int(frame):06d}.pt")
