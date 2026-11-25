#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile and exercise title input and capture on Linux with a stub runner."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CASE = "core.compute.storage-buffer"


def check(template, vulkan_include):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        capture = root / "capture"
        capture.mkdir()
        executable = root / "title"
        subprocess.run([
            os.environ.get("CXX", "c++"), "-std=c++20", "-I", ROOT / "src", "-I", template / "ps5/src",
            "-I", vulkan_include, '-DM1_CAPTURE_ROOT="capture"', '-DM1_BUILD_ID="host-build"',
            '-DM1_REVISION="host-revision"', '-DM1_TITLE_ID="PPSA99745"',
            ROOT / "src/platform/ps5/title.cpp", ROOT / "tests/m1/ps5-adapter-stubs.cpp", "-o", executable,
        ], check=True)

        def launch(expected):
            result = subprocess.run([executable], cwd=root, capture_output=True, timeout=5)
            assert result.returncode == expected, result

        selection = capture / "selection.txt"
        for index, raw, name, device in [
            (1, None, CASE, 0),
            (2, b"inventory\n", "inventory", 0),
            (3, b"inventory 4294967295\r\n", "inventory", 4294967295),
            (4, CASE.encode() + b" 7", CASE, 7),
        ]:
            if raw is not None:
                selection.write_bytes(raw)
            launch(0)
            run = capture / f"run-{index:06d}"
            assert (run / "report.json").read_text() == f"{name} {device} {run.name}\n"
            assert (run / "exit-code.txt").read_text() == "0\n"
            assert f"\ncase {name}\ndevice {device}\n" in (run / "start.log").read_text()

        for raw in (b"", b"inventory -1\n", b"inventory 4294967296\n", b"inventory 0\ninventory\n",
                    b"inventory\x00\n", b"inventory  0\n", b"a" * 64):
            selection.write_bytes(raw)
            launch(2)
            assert not (capture / "run-000005").exists()

        selection.write_text("unknown.case\n")
        launch(2)
        rejected = capture / "run-000005"
        assert (rejected / "exit-code.txt").read_text() == "2\n"
        assert not (rejected / "report.json").exists()

    print("PS5 title selection and stub runner dispatch passed on Linux")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("vulkan_include", type=Path, nargs="?", default=Path("/usr/include"))
    args = parser.parse_args()
    check(args.template, args.vulkan_include)
