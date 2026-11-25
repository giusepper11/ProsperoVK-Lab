# SPDX-License-Identifier: GPL-3.0-or-later
"""Bind a retrieved focused CTS session to its title and upstream runner."""
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import xml.etree.ElementTree as ET

qpa = runpy.run_path(str(Path(__file__).with_name("verify-m0-cts-qpa.py")))
CASE = qpa["CASE_ID"]
REVISION = "f6a29701220f34dd1407513bfe80d74ca7b392ce"


def cts_run_report(run, app, identity):
    journal = f"build {identity}\ntitle {app.name}\ncase {CASE}\n".encode()
    if (run / "start.log").read_bytes() != journal:
        raise ValueError("CTS title journal differs from the verified manifest")
    source = Path(os.environ["CTS"])
    parser = "scripts/log/log_parser.py"
    if subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True).strip() != REVISION:
        raise ValueError("CTS parser revision mismatch")
    subprocess.run(["git", "-C", source, "diff", "--quiet", "HEAD", "--", parser], check=True)
    report = run / "TestResults.qpa"
    try:
        result = qpa["verify"](source, report)
    except ET.ParseError as error:
        raise ValueError("invalid CTS case XML") from error

    session = {}
    with report.open("rb") as stream:
        for line in stream:
            if line.rstrip() == b"#beginSession":
                break
            if line.startswith(b"#sessionInfo "):
                _, key, value = line.decode().split(maxsplit=2)
                if key in session:
                    raise ValueError("duplicate CTS session field " + key)
                session[key] = value.strip()
    if session["releaseName"] != REVISION or int(session["vendorID"], 0) != 0x1002:
        raise ValueError("QPA release or Vulkan vendor differs from the Slim baseline")
    args = shlex.split(session["commandLineParameters"])
    if len(args) != 1:
        raise ValueError("invalid CTS command line metadata")
    options = shlex.split(args[0])
    log_paths = [arg for arg in options if arg.startswith("--deqp-log-filename=")]
    if len(log_paths) != 1:
        raise ValueError("expected one CTS log path")
    match = re.fullmatch(r"--deqp-log-filename=/app0/(run-[0-9]{6})/TestResults\.qpa", log_paths[0])
    if not match or [arg for arg in options if arg.startswith("--deqp-case=")] != ["--deqp-case=" + CASE]:
        raise ValueError("QPA does not identify the title capture path and selected case")
    receipt = run / "retrieval.json"
    if receipt.exists():
        capture = json.loads(receipt.read_bytes())
        if (capture["run"], capture["title_id"]) != (match[1], app.name):
            raise ValueError("QPA capture path differs from Manager retrieval")
    code = (run / "exit-code.txt").read_bytes()
    if code not in (b"0\n", b"1\n"):
        raise ValueError("invalid CTS return code")
    status = result["qpa_status"]
    completed = result["case_completed"]
    expected_codes = {"Pass": 0, "Fail": 1, "NotSupported": 0}
    if completed and status in expected_codes and int(code) != expected_codes[status]:
        raise ValueError("CTS return code contradicts the QPA verdict")
    correctness = {"Pass": "PASS", "NotSupported": "UNSUPPORTED"}.get(status, "FAIL") if completed else "FAIL"
    return dict(EXECUTE="PASS" if completed else "ERROR", CORRECTNESS=correctness,
                PERFORMANCE="NOT_RUN", SHELL_EXIT="UNCONFIRMED", cts_return=int(code), qpa=result)
