#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exercise the QPA verifier using a passing Linux CTS artifact and derived copies."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


CASE_ID = b"dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation"
VERIFIER = Path(__file__).resolve().parents[3] / "tools" / "verify-m0-cts-qpa.py"


def replace(data, old, new):
    if data.count(old) != 1:
        raise ValueError(f"fixture must contain exactly one {old!r}")
    return data.replace(old, new, 1)


def mutations(data):
    case_start = b"#beginTestCaseResult " + CASE_ID + b"\n"
    case_end = b"#endTestCaseResult\n"
    session_end = b"#endSession\n"
    result = b'<Result StatusCode="Pass">Compute succeeded</Result>'
    yield "original", data, 0, "Pass", True
    yield "crlf", data.replace(b"\n", b"\r\n"), 0, "Pass", True
    yield "no-session-start", replace(data, b"#beginSession\n", b""), 2, None, None
    yield "no-case-end", replace(data, case_end, b""), 2, None, None
    yield "no-session-end", replace(data, session_end, b""), 2, None, None
    yield "incomplete-trailer", replace(data, session_end, b"#endSession"), 2, None, None
    yield "premature-trailer", replace(data, case_end, session_end + case_end), 2, None, None
    yield "duplicate-session", data + b"#beginSession\n" + session_end, 2, None, None
    yield "second-case-unfinished", replace(data, session_end, case_start + session_end), 2, None, None
    yield "extra-data", data + b"#beginTestCaseRes", 2, None, None
    yield "wrong-xml-case", replace(data, b'CasePath="' + CASE_ID, b'CasePath="wrong'), 2, None, None
    yield "nested-result", replace(data, result, b"<Section>" + result + b"</Section>"), 2, None, None
    yield "duplicate-result", replace(data, result, result + result), 2, None, None
    yield "invalid-status-bytes", replace(data, b'StatusCode="Pass"', b'StatusCode="Pa\xffss"'), 2, None, None
    yield "failure", replace(data, b'StatusCode="Pass"', b'StatusCode="Fail"'), 1, "Fail", True

    metadata, _, case_body = data.partition(case_start)
    _, _, session_tail = case_body.partition(case_end)
    for status in ("Pass", "Crash"):
        termination = b"#terminateTestCaseResult " + status.encode("ascii") + b"\n"
        yield "terminated-" + status, metadata + case_start + termination + session_tail, 1, status, False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cts_source", type=Path)
    parser.add_argument("passing_qpa", type=Path)
    args = parser.parse_args()
    data = args.passing_qpa.read_bytes()

    with TemporaryDirectory() as temp_dir:
        for name, payload, exit_code, status, completed in mutations(data):
            qpa = Path(temp_dir) / f"{name}.qpa"
            qpa.write_bytes(payload)
            result = subprocess.run(
                [sys.executable, "-B", str(VERIFIER), str(args.cts_source), str(qpa)],
                capture_output=True, text=True, check=False,
            )
            if result.returncode != exit_code:
                raise AssertionError(f"{name}: exit {result.returncode} instead of {exit_code}\n{result}")
            if exit_code == 2:
                if result.stdout or "QPA verification failed:" not in result.stderr:
                    raise AssertionError(f"{name}: missing malformed QPA diagnostic\n{result}")
            else:
                record = json.loads(result.stdout)
                expected_detail = "Compute succeeded" if completed else status
                if (record["case_id"].encode() != CASE_ID or record["qpa_status"] != status
                        or record["case_completed"] != completed
                        or record["detail"] != expected_detail
                        or record["qpa_sha256"] != hashlib.sha256(payload).hexdigest()):
                    raise AssertionError(f"{name}: unexpected QPA record {record!r}")
            print(f"PASS {name}")


if __name__ == "__main__":
    main()
