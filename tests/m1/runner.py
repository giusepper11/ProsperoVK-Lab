# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
from pathlib import Path
import resource
import signal
import runpy
import subprocess
import sys
import tempfile

runner = Path(sys.argv[1]).resolve()
validator = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/validate-m1.py"))
validate = validator["validate"]
case = "core.compute.storage-buffer"


def call(*args, success=False, env=None):
    p = subprocess.run([runner, *args], capture_output=True, text=True, env=env, timeout=12)
    assert (p.returncode == 0) == success, (args, p.returncode, p.stderr)
    if not success:
        assert p.stderr.strip(), args
    return p


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    report = base / "run.json"
    start = base / "run.json.start.json"
    assert call("--list", success=True).stdout.splitlines() == [case]
    for args in (["--case", "unknown"], ["--case", case, "--inventory"],
                 ["--inventory", "--device", "-1"], ["--inventory", "--device", "4294967296"],
                 ["--inventory", "--device", "0trailing"], ["--device", "1"], ["--inventory", "--inventory"]):
        call(*args, "--report", report)
        assert not report.exists() and not start.exists()
    call("--case", case, "--report", base)
    call("--inventory", "--report", report, success=True)
    assert validate(report)["case_id"] is None and not start.exists()
    original = report.read_bytes()
    call("--case", case, "--report", report)
    assert report.read_bytes() == original and not start.exists()
    report.unlink()

    call("--case", case, "--device", "4294967295", "--report", report)
    assert validate(report)["status"] == "NOT_RUN" and not start.exists()
    report.unlink()
    call("--case", case, "--report", report,
         env=dict(os.environ, VK_DRIVER_FILES=str(base / "absent"), VK_ICD_FILENAMES=str(base / "absent")))
    assert validate(report)["status"] == "NOT_RUN" and not start.exists()
    report.unlink()

    start.write_text("previous run")
    call("--case", case, "--report", report)
    assert start.read_text() == "previous run" and validate(report)["status"] == "NOT_RUN"
    start.unlink()
    report.unlink()
    call("--case", case, "--device", "0", "--report", report, success=True)
    result = validate(report)
    journal = json.loads(start.read_bytes())
    for key in ("build_id", "run_id", "revision", "case_id", "target", "device_index", "schema_version"):
        assert result[key] == journal[key]
    assert journal["event"] == "start" and result["status"] == "PASS"
    for key, value in (("schema_version", 2), ("inventory", None), ("correctness", None), ("status", "FAIL")):
        report.write_text(json.dumps({**result, key: value}))
        try:
            validate(report)
        except validator["ValidationError"]:
            pass
        else:
            raise AssertionError(f"validator accepted invalid {key}")

    # Force a checked short write at report close after successful discovery.
    def limit_output():
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (32, 32))

    truncated = base / "truncated.json"
    limited = subprocess.run([runner, "--inventory", "--report", truncated], capture_output=True,
                             preexec_fn=limit_output, timeout=12)
    assert limited.returncode == 2 and b"could not finalize" in limited.stderr
    assert truncated.stat().st_size <= 32
