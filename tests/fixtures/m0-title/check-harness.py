#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise rejection paths against a scratch copy of a real validated package."""
import json
from pathlib import Path
import runpy
import shutil
import sys
import zipfile
from tempfile import TemporaryDirectory

tools = Path(__file__).resolve().parents[3] / "tools"
accept = runpy.run_path(str(tools / "m0-accept.py"))
transfer = runpy.run_path(str(tools / "m0-transfer.py"))


def rejects(call, *args):
    try:
        call(*args)
    except (ValueError, OSError, KeyError):
        return
    raise AssertionError("invalid input was accepted")


original = Path(sys.argv[1])
with TemporaryDirectory() as tmp:
    app = Path(tmp) / original.name
    shutil.copytree(original, app)
    zip_path = app.with_suffix(".zip")
    shutil.copy2(original.with_suffix(".zip"), zip_path)
    accept["package"](app)
    for name in ("eboot.bin", "sce_module/libc.prx", "sce_sys/icon0.png", "sce_sys/param.json",
                 "build.json", "LEGAL.txt", "licenses/GPL-3.0.txt"):
        (app / name).unlink()
        rejects(accept["package"], app)
        shutil.copy2(original / name, app / name)
    manifest = json.loads((app / "build.json").read_text())
    for key in ("title_id", "build_id", "eboot_sha256", "mesa"):
        (app / "build.json").write_text(json.dumps(dict(manifest, **{key: "bad"})))
        rejects(accept["package"], app)
    shutil.copy2(original / "build.json", app)
    with zip_path.open("wb") as f:
        f.write(b"truncated")
    try:
        accept["package"](app)
    except (zipfile.BadZipFile, ValueError):
        pass
    else:
        raise AssertionError("invalid ZIP accepted")
    rejects(transfer["retrieve"], None, "../run-000001", Path(tmp))
    # Use synthetic host-test inputs for verifier regressions without shipping hardware captures.
    run = Path(tmp) / "run"
    run.mkdir()
    identity = manifest["build_id"]
    (run / "start.log").write_text('build ' + identity + '\n{"case_id":"m0.radv.compute","event":"start"}\n')
    smoke = dict(case_id="m0.radv.compute", status="PASS", checked_words=4096, vendor_id=0,
                 device_id=0, api_version=1, queue_family=0, host_coherent=True)
    (run / "result.json").write_text(json.dumps(smoke) + "\n")
    (run / "exit-code.txt").write_text("0\n")
    (run / "timing-exit-code.txt").write_text("0\n")
    t = dict(case_id=smoke["case_id"], schema_version=1, status="PASS", execution_target="ps5",
             buffer_bytes=16384, groups=64, local_size=64, checked_words_per_dispatch=4096,
             initial_checks=1, warmups=5, sample_count=30, verbose=False, timing_clock="steady_clock",
             gpu_execution_ns=None, gpu_timing_unavailable_reason="timestamps_not_measured_by_probe",
             vendor_id=0, device_id=0, api_version=1, queue_family=0, driver_version=1,
             memory_type_index=0, memory_property_flags=6)
    for key in accept["METRICS"]:
        t[key] = dict(samples=[0]*30, min=0, max=0, range=0, median=0, p95=0)
    timing = run / "timing.json"
    assert accept["run_report"](run, identity)["PERFORMANCE"] == "INCOMPLETE"
    timing.write_text(json.dumps(t))
    assert accept["run_report"](run, identity)["PERFORMANCE"] == "PASS"
    rejects(accept["run_report"], run, "wrong-build")
    t["cpu_fence_wait_ns"]["p95"] = 42
    timing.write_text(json.dumps(t))
    rejects(accept["run_report"], run, identity)
    (run / "result.json").write_text(json.dumps(dict(smoke, checked_words=4095)) + "\n")
    rejects(accept["run_report"], run, identity)
print("M0 package, invalid-input and report regression checks passed")
