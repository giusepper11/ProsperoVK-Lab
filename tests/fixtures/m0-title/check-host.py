#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the title's capture handling with Linux Vulkan and stubbed shell calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

binary, verifier = map(lambda path: Path(path).resolve(), sys.argv[1:])
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    env = dict(os.environ, MESA_SHADER_CACHE_DISABLE="true",
               VK_DRIVER_FILES="/usr/share/vulkan/icd.d/lvp_icd.json")

    def launch(code, verdict):
        run = subprocess.run([binary], cwd=root, env=env, capture_output=True, timeout=20)
        assert run.returncode == code and verdict in run.stderr, run

    launch(1, b"ERROR creating capture directory")
    (root / "capture").mkdir()
    launch(0, b"30 timing samples saved")
    first = root / "capture/run-000001"
    subprocess.run([sys.executable, verifier, first], check=True)
    timing = json.loads((first / "timing.json").read_text())
    assert timing["execution_target"] == "linux" and timing["sample_count"] == 30
    assert (first / "timing-exit-code.txt").read_text() == "0\n"
    env["VK_DRIVER_FILES"] = str(root / "missing-icd.json")
    launch(1, b"vkCreateInstance")
    second = root / "capture/run-000002"
    assert (second / "exit-code.txt").read_text() == "1\n"
    assert not (second / "timing.json").exists()
    assert (first / "timing.json").exists()
    print("Linux title capture checks passed")
