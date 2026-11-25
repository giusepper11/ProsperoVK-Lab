#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the M1 harness with a local package and a synthetic capture."""
import argparse
import json
from pathlib import Path
import runpy
import subprocess
import tempfile

TOOLS = Path(__file__).resolve().parents[2] / "tools"
ACCEPT = runpy.run_path(str(TOOLS / "m0-accept.py"))
TRANSFER = runpy.run_path(str(TOOLS / "m0-transfer.py"))


def write_json(value):
    return (json.dumps(value) + "\n").encode()


class FakeManager:
    def __init__(self, files):
        self.files = files

    def entries(self, directory):
        return [{"name": name.rsplit("/", 1)[1], "is_dir": False}
                for name in self.files if name.rsplit("/", 1)[0] == directory]

    def download(self, path):
        return self.files[path]

    def request(self, route):
        assert route in ("logs", "klogs")
        return {"lines": ["ProsperoVK Lab M1: synthetic evidence", "ProsperoVK Lab CTS: separate title"]}


def rejects(callback, *args):
    try:
        callback(*args)
    except (ValueError, subprocess.CalledProcessError):
        return
    raise AssertionError(f"accepted invalid fixture: {args}")


def main(app, report_path):
    package = ACCEPT["package"](app)
    assert package["workload"] == "m1"
    manifest = ACCEPT["read_json"](app / "build.json")
    build = package["build_id"]
    case, revision = manifest["case_id"], manifest["lab_revision"]
    report = ACCEPT["read_json"](report_path)
    assert report["target"] == "linux" and report["status"] == "PASS" and report["case_id"] == case
    assert report["shader_sha256"] == manifest["shader_sha256"]
    run_name = "run-000001"
    report.update(target="ps5", build_id=build, revision=revision, run_id=run_name)
    journal = dict(schema_version=1, event="start", case_id=case, device_index=0,
                   target="ps5", build_id=build, revision=revision, run_id=run_name)
    dest = f"{TRANSFER['PARENT']}/{app.name}"
    files = {f"{dest}/{p.relative_to(app)}": p.read_bytes() for p in app.rglob("*") if p.is_file()}
    remote = f"{dest}/{run_name}"
    start = f"build {build}\nrevision {revision}\ntitle {app.name}\ncase {case}\ndevice 0\npath /app0/{run_name}\n"
    files[f"{remote}/start.log"] = start.encode()
    files[f"{remote}/report.json.start.json"] = write_json(journal)
    manager = FakeManager(files)

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        partial = root / "partial"
        TRANSFER["retrieve"](manager, run_name, partial, app)
        assert (partial / "start.log").read_bytes() == start.encode()
        assert (partial / "report.json.start.json").read_bytes() == write_json(journal)
        assert not (partial / "report.json").exists()

        files[f"{remote}/report.json"] = write_json(report)
        files[f"{remote}/exit-code.txt"] = b"0\n"
        run = root / "complete"
        TRANSFER["retrieve"](manager, run_name, run, app)
        assert (run / "title-klog.log").read_text() == "ProsperoVK Lab M1: synthetic evidence\n"
        result = ACCEPT["m1_run_report"](run, app, build)
        assert [result[gate] for gate in ("EXECUTE", "CORRECTNESS", "PERFORMANCE", "SHELL_EXIT")] == [
            "PASS", "PASS", "NOT_RUN", "UNCONFIRMED"]

        for file, bad in [
            ("start.log", start.replace(build, "0" * 64).encode()),
            ("start.log", start.replace("device 0", "device 1").encode()),
            ("start.log", start.replace("device 0", "device 4294967296").encode()),
            ("retrieval.json", write_json(dict(run="run-000002", title_id=app.name, build_id=build))),
            ("report.json.start.json", write_json(dict(journal, device_index=1))),
            ("report.json.start.json", write_json(dict(journal, run_id="run-000002"))),
            ("exit-code.txt", b"1\n"),
            ("report.json", write_json(dict(report, target="linux"))),
            ("report.json", write_json(dict(report, run_id="run-000002"))),
            ("report.json", write_json(dict(report, shader_sha256="0" * 64))),
        ]:
            path = run / file
            original = path.read_bytes()
            path.write_bytes(bad)
            rejects(ACCEPT["m1_run_report"], run, app, build)
            path.write_bytes(original)

        inventory_name = "run-000002"
        inventory_remote = f"{dest}/{inventory_name}"
        inventory_start = start.replace(f"case {case}\ndevice 0", "case inventory\ndevice 2")
        inventory_start = inventory_start.replace(run_name, inventory_name)
        inventory = dict(report, case_id=None, shader_sha256=None, requirements={}, enabled=None,
                         correctness=None, timing=None, eligibility="not_evaluated", device_index=2,
                         run_id=inventory_name,
                         inventory=dict(report["inventory"], device_count=3,
                                        selected_device=dict(report["inventory"]["selected_device"], index=2)))
        files[f"{inventory_remote}/start.log"] = inventory_start.encode()
        files[f"{inventory_remote}/report.json"] = write_json(inventory)
        files[f"{inventory_remote}/exit-code.txt"] = b"0\n"
        inventory_run = root / "inventory"
        TRANSFER["retrieve"](manager, inventory_name, inventory_run, app)
        result = ACCEPT["m1_run_report"](inventory_run, app, build)
        assert result["EXECUTE"] == "PASS" and result["CORRECTNESS"] == "NOT_RUN" and result["case_id"] is None
        assert result["device_index"] == 2
        subprocess.run([TOOLS / "m0", "accept", app, inventory_run], check=True, stdout=subprocess.DEVNULL)
        (inventory_run / "report.json.start.json").write_bytes(write_json(journal))
        rejects(ACCEPT["m1_run_report"], inventory_run, app, build)

        files[f"{dest}/build.json"] = b"{}"
        mismatched = root / "mismatched"
        rejects(TRANSFER["retrieve"], manager, run_name, mismatched, app)
        assert not mismatched.exists()

    print("M1 package, synthetic retrieval and acceptance regression checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("linux_smoke_report", type=Path)
    args = parser.parse_args()
    main(args.app, args.linux_smoke_report)
