# SPDX-License-Identifier: GPL-3.0-or-later
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
validator = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools/validate-m1.py"))

with tempfile.TemporaryDirectory() as directory:
    for fault, status, detail in (
        ("timeout", "TIMEOUT", "VK_TIMEOUT"),
        ("device-lost", "ERROR", "VK_ERROR_DEVICE_LOST"),
        ("memory-bits", "UNSUPPORTED", "memoryTypeBits"),
    ):
        report = Path(directory) / f"{fault}.json"
        result = subprocess.run([binary, fault, report], capture_output=True, text=True, timeout=12)
        assert result.returncode == 0, (fault, result.stderr)
        outcome = validator["validate"](report)
        assert outcome["status"] == status and detail in outcome["reason"], outcome
        assert outcome["eligibility"] == ("unmet" if status == "UNSUPPORTED" else "met")
        assert outcome["timing"] is None and outcome["correctness"] is None, outcome

        journal = json.loads(report.with_name(report.name + ".start.json").read_text())
        assert journal["event"] == "start"
        for key in ("build_id", "run_id", "revision", "case_id", "target", "device_index", "schema_version"):
            assert journal[key] == outcome[key], (key, journal, outcome)
