#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exercise the captured result verifier against real Linux runs and derived copies."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


FILES = ("result.json", "start.log", "exit-code.txt")
VERIFIER = Path(__file__).resolve().parents[3] / "tools" / "verify-m0-radv-compute.py"


def read_capture(directory):
    return tuple((directory / name).read_bytes() for name in FILES)


def variants(passing, failing):
    payload, start, exit_code = passing
    record = json.loads(payload)

    def result(**changes):
        return (json.dumps(record | changes) + "\n").encode()

    yield "llvmpipe", passing, 0
    yield "missing-icd", failing, 1
    yield "loader-diagnostics", (payload, b"loader info\n" + start + b"loader info\n", exit_code), 0
    yield "crlf", (payload.replace(b"\n", b"\r\n"), start.replace(b"\n", b"\r\n"), b"0\r\n"), 0
    yield "noncoherent-memory", (result(host_coherent=False), start, exit_code), 0
    yield "missing-marker", (payload, b"", exit_code), 2
    yield "partial-marker", (payload, start.rstrip(b"\n"), exit_code), 2
    yield "duplicate-marker", (payload, start + start, exit_code), 2
    yield "truncated-result", (payload.rstrip(b"\n"), start, exit_code), 2
    yield "duplicate-result", (payload + failing[0], start, exit_code), 2
    yield "duplicate-field", (b'{"status":"ERROR",' + payload[1:], start, exit_code), 2
    yield "wrong-case", (result(case_id="m0.other"), start, exit_code), 2
    yield "wrong-word-count", (result(checked_words=4095), start, exit_code), 2
    yield "word-count-wrong-type", (result(checked_words=4096.0), start, exit_code), 2
    yield "invalid-device-id", (result(device_id=True), start, exit_code), 2
    yield "pass-with-crash-exit", (payload, start, b"139\n"), 2
    yield "nonpass-with-zero-exit", (failing[0], failing[1], b"0\n"), 2
    failure = b'{"case_id":"m0.radv.compute","status":"ERROR","stage":"start_marker"}\n'
    yield "start-marker-write-failed", (failure, b"", b"1\n"), 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("passing_run", type=Path)
    parser.add_argument("missing_icd_run", type=Path)
    args = parser.parse_args()

    with TemporaryDirectory() as root:
        for name, capture, exit_code in variants(read_capture(args.passing_run), read_capture(args.missing_icd_run)):
            directory = Path(root) / name
            directory.mkdir()
            for filename, data in zip(FILES, capture):
                (directory / filename).write_bytes(data)

            result = subprocess.run(
                [sys.executable, "-B", str(VERIFIER), str(directory)],
                capture_output=True, text=True, check=False,
            )
            if result.returncode != exit_code:
                raise AssertionError(f"{name}: exit {result.returncode} instead of {exit_code}\n{result}")
            if exit_code == 2:
                if result.stdout or "Compute verification failed:" not in result.stderr:
                    raise AssertionError(f"{name}: missing invalid evidence diagnostic\n{result}")
            else:
                evidence = json.loads(result.stdout)
                hashes = {filename: hashlib.sha256(raw).hexdigest() for filename, raw in zip(FILES, capture)}
                if (evidence["result"] != json.loads(capture[0]) or evidence["sha256"] != hashes
                        or evidence["application_exit_code"] != exit_code):
                    raise AssertionError(f"{name}: unexpected result or hashes {evidence!r}")
            print(f"PASS {name}")


if __name__ == "__main__":
    main()
