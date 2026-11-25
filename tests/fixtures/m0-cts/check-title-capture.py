#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Check the CTS report and transfer contracts with synthetic offline captures."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import URLError


TOOLS = Path(__file__).resolve().parents[3] / "tools"
TRANSFER = runpy.run_path(str(TOOLS / "m0-transfer.py"))
REPORT = runpy.run_path(str(TOOLS / "m0-cts-report.py"))
CASE = REPORT["CASE"]
REVISION = REPORT["REVISION"]
TITLE_ID = "PPSA99744"
BUILD_ID = "a" * 64
RUN = "run-000012"
REMOTE = f"/data/homebrew/{TITLE_ID}/{RUN}"
JOURNAL = f"build {BUILD_ID}\ntitle {TITLE_ID}\ncase {CASE}\n"


class FakeManager:
    def __init__(self, *, titles=(), destination_entries=(), files=None, logs=None):
        self.titles = titles
        self.destination_entries = destination_entries
        self.files = {} if files is None else files
        self.logs = {} if logs is None else logs
        self.operations = []

    def entries(self, path):
        self.operations.append(("entries", path))
        if path == "/data/homebrew":
            return [{"name": name, "is_dir": True} for name in self.destination_entries]
        assert path == REMOTE, path
        return [{"name": name, "is_dir": False} for name in self.files]

    def download(self, path):
        self.operations.append(("download", path))
        assert path.startswith(REMOTE + "/"), path
        return self.files[Path(path).name]

    def request(self, route):
        self.operations.append((route, None))
        if route == "titles":
            return {"titles": self.titles}
        if route in self.logs:
            return self.logs[route]
        raise URLError("synthetic log endpoint unavailable")


def rejects(operation, diagnostic, *args):
    try:
        operation(*args)
    except ValueError as error:
        assert diagnostic in str(error), str(error)
    else:
        raise AssertionError(f"expected rejection containing {diagnostic!r}")


def make_qpa(status="Pass", *, terminated=False, vendor="0x1002", run=RUN, case=CASE):
    command = f"--deqp-case={case} --deqp-log-filename=/app0/{run}/TestResults.qpa"
    if terminated:
        result = f"#terminateTestCaseResult {status}\n"
    else:
        result = (f'<TestCaseResult CasePath="{CASE}">\n'
                  f'<Result StatusCode="{status}">synthetic fixture</Result>\n'
                  "</TestCaseResult>\n#endTestCaseResult\n")
    return (f"#sessionInfo releaseName {REVISION}\n"
            f"#sessionInfo vendorID {vendor}\n"
            f'#sessionInfo commandLineParameters "{command}"\n'
            f"#beginSession\n#beginTestCaseResult {CASE}\n{result}#endSession\n").encode()


def check_transfer(root, app):
    deploy = TRANSFER["deploy"]
    retrieve = TRANSFER["retrieve"]
    # Replace only package inspection here. The package checks have their own fixtures.
    with patch.dict(deploy.__globals__["accept"], package=lambda path: {"workload": "cts"}):
        catalog = FakeManager(titles=[{"titleId": TITLE_ID.lower()}])
        rejects(deploy, "already in use", catalog, app)
        assert catalog.operations == [("titles", None)], catalog.operations

        destination = FakeManager(destination_entries=[TITLE_ID.lower()])
        rejects(deploy, "already in use", destination, app)
        assert destination.operations == [("titles", None), ("entries", "/data/homebrew")]

        raw_qpa = make_qpa()
        manager = FakeManager(
            files={"start.log": JOURNAL.encode(), "TestResults.qpa": raw_qpa, "result.json": b"ignore"},
            logs={"logs": {"connected": True, "lines": ["unrelated", "ProsperoVK Lab",
                                                       f"{TITLE_ID} synthetic log"]}},
        )
        out = root / "partial"
        retrieve(manager, RUN, out, app)
        assert (out / "start.log").read_text() == JOURNAL
        assert (out / "TestResults.qpa").read_bytes() == raw_qpa
        assert (out / "manager-title.log").read_text() == f"{TITLE_ID} synthetic log\n"
        assert sorted(path.name for path in out.iterdir()) == [
            "TestResults.qpa", "manager-title.log", "retrieval.json", "start.log",
        ]
        assert json.loads((out / "retrieval.json").read_text()) == {
            "title_id": TITLE_ID, "run": RUN,
            "klogs": {"error": "URLError"}, "logs": {"connected": True, "matched_lines": 1},
        }
        try:
            REPORT["cts_run_report"](out, app, BUILD_ID)
        except FileNotFoundError as error:
            assert Path(error.filename).name == "exit-code.txt", error
        else:
            raise AssertionError("partial capture passed without a runner return record")


def check_reports(root, app):
    report = REPORT["cts_run_report"]
    capture = root / "capture"
    capture.mkdir()
    journal = capture / "start.log"
    qpa = capture / "TestResults.qpa"
    code = capture / "exit-code.txt"
    receipt = capture / "retrieval.json"
    journal.write_text(JOURNAL)
    receipt.write_text(json.dumps({"title_id": TITLE_ID, "run": RUN}))

    for status, terminated, return_code, correctness in (
        ("Pass", False, 0, "PASS"),
        ("Fail", False, 1, "FAIL"),
        ("NotSupported", False, 0, "UNSUPPORTED"),
        ("Crash", True, 1, "FAIL"),
        ("Pass", True, 1, "FAIL"),
    ):
        payload = make_qpa(status, terminated=terminated)
        qpa.write_bytes(payload)
        code.write_text(f"{return_code}\n")
        verdict = report(capture, app, BUILD_ID)
        assert verdict["CORRECTNESS"] == correctness, verdict
        assert verdict["EXECUTE"] == ("ERROR" if terminated else "PASS"), verdict
        assert verdict["cts_return"] == return_code, verdict
        assert (verdict["PERFORMANCE"], verdict["SHELL_EXIT"]) == ("NOT_RUN", "UNCONFIRMED")
        assert verdict["qpa"] == {
            "case_id": CASE, "qpa_status": status, "detail": status if terminated else "synthetic fixture",
            "case_completed": not terminated, "qpa_sha256": hashlib.sha256(payload).hexdigest(),
        }, verdict

    qpa.write_bytes(make_qpa())
    code.write_text("0\n")
    rejects(report, "journal", capture, app, "b" * 64)
    journal.write_text(JOURNAL.replace(CASE, "wrong"))
    rejects(report, "journal", capture, app, BUILD_ID)
    journal.write_text(JOURNAL.replace(TITLE_ID, "PPSA99743"))
    rejects(report, "journal", capture, app, BUILD_ID)
    journal.write_text(JOURNAL)
    for bad_qpa, diagnostic in (
        (make_qpa(vendor="0x10005"), "Vulkan vendor"),
        (make_qpa(case="wrong"), "selected case"),
        (make_qpa(run="run-000013"), "Manager retrieval"),
    ):
        qpa.write_bytes(bad_qpa)
        rejects(report, diagnostic, capture, app, BUILD_ID)
    qpa.write_bytes(make_qpa())
    receipt.write_text(json.dumps({"title_id": "PPSA99743", "run": RUN}))
    rejects(report, "Manager retrieval", capture, app, BUILD_ID)
    receipt.write_text(json.dumps({"title_id": TITLE_ID, "run": RUN}))
    code.write_text("00\n")
    rejects(report, "return code", capture, app, BUILD_ID)
    code.write_text("1\n")
    rejects(report, "return code", capture, app, BUILD_ID)
    code.write_text("0\n")
    qpa.write_bytes(make_qpa("Fail"))
    rejects(report, "return code", capture, app, BUILD_ID)
    code.write_text("1\n")
    qpa.write_bytes(make_qpa("NotSupported"))
    rejects(report, "return code", capture, app, BUILD_ID)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cts_source", type=Path, help="pinned Khronos VK-GL-CTS checkout")
    args = parser.parse_args()
    with TemporaryDirectory() as temporary, patch.dict(os.environ, CTS=str(args.cts_source.resolve())):
        root = Path(temporary)
        app = root / TITLE_ID
        app.mkdir()
        check_transfer(root, app)
        check_reports(root, app)
    print("Synthetic CTS title capture and transfer checks passed")


if __name__ == "__main__":
    main()
