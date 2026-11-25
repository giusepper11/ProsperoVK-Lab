#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Check captured m0.radv.compute artifacts and preserve their original result."""

import argparse
import hashlib
import json
from pathlib import Path
import sys


CASE_ID = "m0.radv.compute"
START_RECORD = b'{"case_id":"m0.radv.compute","event":"start"}'
STATUSES = ("PASS", "FAIL", "UNSUPPORTED", "ERROR", "TIMEOUT")
WORD_COUNT = 4096


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate result field: {key}")
        result[key] = value
    return result


def invalid_constant(token):
    raise ValueError(f"invalid JSON constant: {token}")


def is_uint32(value):
    return type(value) is int and 0 <= value <= 0xFFFFFFFF


def verify(run_dir):
    payload = (run_dir / "result.json").read_bytes()
    start_log = (run_dir / "start.log").read_bytes()
    exit_log = (run_dir / "exit-code.txt").read_bytes()
    if not payload.endswith(b"\n") or len(payload.splitlines()) != 1:
        raise ValueError("expected one newline-terminated JSON result")
    result = json.loads(payload, object_pairs_hook=unique_fields, parse_constant=invalid_constant)
    if not isinstance(result, dict) or result.get("case_id") != CASE_ID:
        raise ValueError(f"expected one JSON result for {CASE_ID}")
    status = result.get("status")
    if status not in STATUSES:
        raise ValueError("unexpected compute result status")

    expected_exit = 0 if status == "PASS" else 1
    if exit_log.strip() != str(expected_exit).encode("ascii"):
        raise ValueError(f"{status} requires application exit code {expected_exit}")

    start_lines = start_log.splitlines(keepends=True)
    marker_count = start_lines.count(START_RECORD + b"\n") + start_lines.count(START_RECORD + b"\r\n")
    start_failed = status == "ERROR" and result.get("stage") == "start_marker"
    if marker_count != 1 and not (start_failed and marker_count == 0):
        raise ValueError("expected exactly one compute start marker in start.log")

    if status in ("PASS", "FAIL"):
        words = result.get("checked_words")
        if type(words) is not int or words != WORD_COUNT:
            raise ValueError(f"{status} requires exactly {WORD_COUNT} checked words as an integer")
    elif not isinstance(result.get("stage"), str) or not result["stage"]:
        raise ValueError(f"{status} requires a diagnostic stage")

    if status == "PASS":
        metadata = ("vendor_id", "device_id", "api_version", "queue_family")
        if not all(is_uint32(result.get(key)) for key in metadata) or type(result.get("host_coherent")) is not bool:
            raise ValueError("PASS requires the fixture's integer device fields and boolean host_coherent")

    return {
        "result": result,
        "application_exit_code": expected_exit,
        "start_marker_count": marker_count,
        "sha256": {
            "result.json": hashlib.sha256(payload).hexdigest(),
            "start.log": hashlib.sha256(start_log).hexdigest(),
            "exit-code.txt": hashlib.sha256(exit_log).hexdigest(),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="directory containing result.json, start.log and exit-code.txt")
    args = parser.parse_args()

    try:
        evidence = verify(args.run_dir)
        print(json.dumps(evidence, allow_nan=False))
    except (OSError, ValueError, RecursionError) as error:
        print(f"Compute verification failed: {error}", file=sys.stderr)
        return 2
    return 0 if evidence["result"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
