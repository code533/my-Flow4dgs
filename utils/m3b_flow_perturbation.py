"""M3-B appearance-perturbation optical-flow disagreement diagnostics.

Shadow-only source-discovery module.  It consumes a small ensemble of
current->previous optical flows produced by the same RAFT model under matched
photometric transforms applied to both frames.
"""

from pathlib import Path
import torch


class M3BFlowPerturbationAudit:
    def __init__(self, min_pixels=500):
        self.min_pixels = max(int(min_pixels), 1)

    @torch.no_grad()
    def evaluate_and_save(
        self,
        *,
        frame,
        flow_ensemble_px,
        static_mask,
        save_dir,
    ):
        if "identity" not in flow_ensemble_px:
            raise KeyError("M3-B flow ensemble must contain 'identity'")

        names = list(flow_ensemble_px.keys())
        flows = [flow_ensemble_px[n] for n in names]
        ref_shape = tuple(flows[0].shape)
        if len(ref_shape) != 3 or ref_shape[0] != 2:
            raise ValueError("M3-B flows must have shape [2,H,W]")
        if any(tuple(f.shape) != ref_shape for f in flows):
            raise ValueError("All M3-B flow variants must share shape")

        stack = torch.stack(flows, dim=0).double()  # [M,2,H,W]
        mean = stack.mean(dim=0)
        centered = stack - mean
        cov00 = (centered[:, 0] * centered[:, 0]).sum(dim=0) / max(len(flows)-1, 1)
        cov11 = (centered[:, 1] * centered[:, 1]).sum(dim=0) / max(len(flows)-1, 1)
        cov01 = (centered[:, 0] * centered[:, 1]).sum(dim=0) / max(len(flows)-1, 1)
        trace = (cov00 + cov11).clamp_min(0.0)
        s = torch.sqrt(trace)

        identity = flow_ensemble_px["identity"].double()
        mean_shift = torch.linalg.norm(mean - identity, dim=0)

        mask = static_mask.bool()
        finite = (
            torch.isfinite(s)
            & torch.isfinite(mean_shift)
            & torch.isfinite(cov00)
            & torch.isfinite(cov11)
            & torch.isfinite(cov01)
        )
        valid = mask & finite
        n = int(valid.sum().item())

        payload = {
            "method": "m3b_flow_perturbation_disagreement_v1",
            "frame": int(frame),
            "variant_names": names,
            "num_variants": len(names),
            "num_valid_pixels": n,
            "valid": n >= self.min_pixels,
        }

        if n >= self.min_pixels:
            sv = s[valid].float()
            mv = mean_shift[valid].float()
            q = torch.quantile(
                sv,
                torch.tensor([0.50, 0.90, 0.95], device=sv.device)
            )
            payload.update({
                "u_tta_median_px": float(q[0].cpu()),
                "u_tta_mean_px": float(sv.mean().cpu()),
                "u_tta_q90_px": float(q[1].cpu()),
                "u_tta_q95_px": float(q[2].cpu()),
                "u_tta_max_px": float(sv.max().cpu()),
                "mean_shift_median_px": float(mv.median().cpu()),
                "mean_shift_mean_px": float(mv.mean().cpu()),
                "cov_trace_mean_px2": float(trace[valid].mean().cpu()),
                "cov_anisotropy_mean_abs_offdiag_px2": float(
                    cov01[valid].abs().mean().cpu()
                ),
            })

        out_dir = Path(save_dir) / "m3b_flow_perturbation"
        out_dir.mkdir(parents=True, exist_ok=True)
        torch.save(payload, out_dir / f"{int(frame):06d}.pt")
        return payload
