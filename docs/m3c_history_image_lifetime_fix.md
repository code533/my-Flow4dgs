# M3-C implementation fix: historical-frame image lifetime

Date: 2026-10-06

## Symptom

The first M3-C audited frame crashed with:

    AttributeError: 'NoneType' object has no attribute 'cuda'

at the access to frame t-2:

    prevprev.original_image.cuda()

## Root cause

Flow4DGS intentionally calls Camera.clean() on old non-keyframes to reduce
memory use.  Camera.clean() sets:

    original_image = None

Therefore, by the time frame t is processed, the Camera object for t-2 can
still exist in the frontend camera dictionary while its RGB tensor has already
been released.

M3-C originally assumed the historical Camera retained its original_image,
which is not a valid assumption under the baseline memory lifecycle.

## Fix

M3-C no longer changes or depends on historical Camera image lifetime.

When an audited frame requires RGB(t-2), it reloads that frame through:

    self.dataset[older_idx]

and uses the returned RGB tensor only for the two diagnostic RAFT calls.

The current Camera's RAFT model is reused for:

    F(t-1 -> t-2)
    F(t   -> t-2)

with tracking=True, so these diagnostic calls remain uncached.

## Behavior-preservation rationale

The fix does not:
- retain old Camera RGB tensors;
- change Camera.clean();
- alter the baseline flow cache;
- alter tracking, masks, keyframes, mapping, or Gaussian state.

It only reloads an already-existing dataset frame for the M3-C shadow audit.

## Action

Pull commit:

    73d91e5c6151734702db79649798e1c5dfedb75b

then rerun the box1 M3-C smoke test from the beginning.

The failed run should not be used for statistical analysis.
