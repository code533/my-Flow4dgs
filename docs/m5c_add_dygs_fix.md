# M5-C implementation fix: add_dygs parameter propagation

Date: 2026-10-07

Branch:

    feature/m5c-soft-opacity

Fix commit:

    47f2d0f044084884fa84b2509b90c2f06a6daece

## Symptom

The first M5-C run crashed in Gaussian point-cloud construction with:

    NameError: name 'add_dygs' is not defined

inside:

    create_pcd_from_image_and_depth(...)

## Root cause

M5-C uses add_dygs to preserve baseline opacity=0.5 for dynamic-object
initialization.

The outer function:

    create_pcd_from_image(..., add_dygs=False)

already had this flag, but the inner helper:

    create_pcd_from_image_and_depth(...)

did not receive it.

M5-C therefore referenced a variable that was out of scope.

## Fix

The add_dygs flag is now explicitly passed from:

    create_pcd_from_image()

to:

    create_pcd_from_image_and_depth(..., add_dygs=add_dygs)

with a default:

    add_dygs=False.

This preserves backward compatibility for any direct helper call.

## Experimental consequence

The failed run must be discarded and restarted from the beginning.

The M5-C frozen rule is unchanged:

    alpha_0 = min(0.5, confidence)

for ordinary optional insertions only.

Initialization and dynamic-object initialization continue to use baseline
opacity 0.5.
