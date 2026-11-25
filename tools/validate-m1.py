#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate a captured v1 inventory or workload report."""
import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/run-v1.schema.json"


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"invalid JSON number {value}")


def validate(path):
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    report = json.loads(path.read_bytes(), object_pairs_hook=unique_keys, parse_constant=reject_constant)
    Draft202012Validator(schema).validate(report)
    inventory = report["inventory"]
    if inventory and report["device_index"] != inventory["selected_device"]["index"]:
        raise ValueError("inventory device index differs from requested index")
    if report["enabled"]:
        enabled = report["enabled"]
        queue = enabled["queue_family"]
        queues = inventory["selected_device"]["queues"]
        if queue != inventory["queue_family"] or not any(
            q["index"] == queue and q["count"] >= enabled["queue_count"] and q["flags"] & 2 for q in queues
        ):
            raise ValueError("enabled queue differs from advertised compute queue")
        allocation = enabled.get("buffer_memory")
        if allocation:
            types = inventory["selected_device"]["memory"]["types"]
            if not any(t["index"] == allocation["memory_type_index"]
                       and t["property_flags"] == allocation["memory_property_flags"]
                       and t["property_flags"] & 2 for t in types):
                raise ValueError("allocation differs from advertised host-visible memory")
    timing = report["timing"]
    if timing and timing["cpu_submit_to_completion_ns"] < timing["cpu_queue_submit_ns"] + timing["cpu_fence_wait_ns"]:
        raise ValueError("CPU timing intervals exceed submit-to-completion interval")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        record = validate(args.report)
    except (OSError, ValueError, ValidationError) as exc:
        parser.exit(1, f"{args.report}: {exc}\n")
    print(f"{args.report}: schema v1, {record['target']}, {record['status']}")
