# M5-A implementation fix: empty dynamic-init point cloud on mov_box2

Date: 2026-10-07

Branch:

    feature/m5-flow-reliability-mapping

Fix commit:

    3ce5f3781bc62fa46b4045dbfe516e13a41257d9

## Symptom

On Bonn moving_nonobstructing_box2 at frame 262 (the configured dystart), the
backend crashed inside simple_knn distCUDA2 with:

    RuntimeError: CUDA error: invalid configuration argument

Immediately before the crash the diagnostic output showed:

    valid_dynamic_depth=20
    empty point cloud before CUDA KNN
    downsample_factor=32

## Root cause

At dystart the backend performs a second Gaussian insertion for dynamic
initialization.

For this frame only a very small dynamic-depth support was available.  After the
existing random downsampling policy, zero points remained.

The code already detected and logged the empty point cloud, but then continued
into:

    distCUDA2(empty [0,3] tensor)

The CUDA KNN kernel cannot operate on an empty input and failed during kernel
launch.

This is a baseline point-cloud construction edge case.  It is not caused by the
M5 reliability confidence or mapping weights.

## Fix

If point-cloud construction retains zero points, create correctly shaped empty
return tensors and return before the CUDA KNN call.

The existing caller already contains:

    if fused_point_cloud.shape[0] > 0:
        self.extend_from_pcd(...)

so the result is a clean no-op Gaussian insertion for that frame.

The fix does not:
- lower the downsample factor;
- fabricate a Gaussian;
- copy a neighboring point;
- change motion masks;
- change tracking;
- change M5 confidence;
- change mapping weights.

It only converts an invalid CUDA call into the behavior already implied by the
caller's N>0 guard.

## Experimental protocol

The fix must be used identically for:

    baseline
    shadow
    weighted

on moving_nonobstructing_box2.

The previously crashed run is invalid and must not be included in any metric
comparison.

Restart all mov_box2 runs used in the paired M5-A comparison from the beginning
on this commit or later.

## Expected behavior

At frame 262, if zero points remain after downsampling, the log should now say:

    empty point cloud before CUDA KNN; skipping this Gaussian insertion

and execution should continue without calling distCUDA2 on the empty cloud.

If a non-empty point cloud is produced on another run, the original insertion
path is unchanged.
