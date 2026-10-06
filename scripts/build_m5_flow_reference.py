#!/usr/bin/env python3
"""Build the frozen M5-A direct-flow ECDF reference from development rows."""

import argparse
import csv
import json
import math
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("development_table", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    values = []
    sequences = {}
    with args.development_table.open(newline="") as f:
        reader = csv.DictReader(f)
        required = {"sequence", "direct_flow_median_px"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise KeyError(
                f"{args.development_table} missing columns {sorted(required)}"
            )
        for row in reader:
            try:
                v = float(row["direct_flow_median_px"])
            except (TypeError, ValueError):
                continue
            if not math.isfinite(v) or v < 0:
                continue
            values.append(v)
            name = row["sequence"]
            sequences[name] = sequences.get(name, 0) + 1

    if len(values) < 20:
        raise RuntimeError("Need at least 20 valid development direct-flow values")

    values.sort()
    report = {
        "method": "m5_direct_flow_ecdf_reference_v1",
        "source_table": str(args.development_table),
        "development_sequences": sorted(sequences),
        "rows_per_sequence": sequences,
        "n": len(values),
        "min": values[0],
        "median": values[len(values)//2],
        "max": values[-1],
        "sorted_direct_flow_median_px": values,
        "guardrail": (
            "Frozen development-only ECDF reference. Do not rebuild from "
            "evaluation or weighted-run outcomes."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(f"Saved {args.output}")
    print("development sequences:", "+".join(sorted(sequences)))
    print("n:", len(values))
    print("min/median/max:", values[0], values[len(values)//2], values[-1])


if __name__ == "__main__":
    main()
