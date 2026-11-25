#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build in a fresh directory. Inputs are the public trees and verified M0 cross-build."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TITLE = ROOT / "tests/fixtures/m0-title"
SMOKE = ROOT / "tests/fixtures/m0-radv-compute"
ID = "PPSA99743"
NAME = "ProsperoVK Lab"
TEMPLATE = "91179df760df1e6c6f2d4d172bc435319d79ff3c"
VULKAN = "7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc"
MESA = "1ba9874f478657ccf6da72ce55f0260164cc0bd0"
SDK = "611893fc25ef3e138f5bc2c90d829d8b58174cd2"
RADV = "d06eaf176b42fda32b740a660f343c1e72167cb11a6f6965669ba23437bdf441"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "template", "vulkan", "mesa", "sdk", "radv", "cross", "sdk_source"):
        parser.add_argument(name, type=lambda s: Path(s).resolve())
    a = parser.parse_args()
    for tree, pin in [(a.template, TEMPLATE), (a.vulkan, VULKAN), (a.mesa, MESA)]:
        if subprocess.check_output(["git", "-C", tree, "rev-parse", "HEAD"], text=True).strip() != pin:
            parser.error(f"wrong revision of {tree}")
        run("git", "-C", tree, "diff", "--quiet", "HEAD")
    archive = a.radv / "lib/libvulkan_radeon.ps5.a"
    if digest(archive) != RADV or (a.sdk / ".ps5-sdk-revision").read_text().strip() != SDK:
        parser.error("RADV digest or title SDK pin mismatch")
    run("sha256sum", "--quiet", "-c", "SHA256SUMS", cwd=a.cross)
    a.output.mkdir(parents=True, exist_ok=False)
    ps5 = a.output / "ps5"
    scripts = ps5 / "tools"
    scripts.mkdir(parents=True)
    work = a.output / "work"
    work.mkdir()
    upstream = a.template / "ps5"
    runtime = a.vulkan / "runtime/libc.prx"
    tool = a.vulkan / "build/host/ps5-native-tool"
    os.environ.update(LAB_ROOT=str(ROOT), TEMPLATE=str(a.template), MESA=str(a.mesa),
                      SDK_SOURCE=str(a.sdk_source), SDK_REVISION=SDK,
                      RADV_ARCHIVE=str(archive), PS5_PAYLOAD_SDK=str(a.sdk))
    shutil.copy2(upstream / "tools/link-title.sh", scripts)
    shutil.copy2(TITLE / "stage-notices.py", scripts)
    generator = runpy.run_path(str(upstream / "tools/new-title.py"))
    if ID in generator["TAKEN"]:
        parser.error("title ID already reserved")
    meta = ps5 / "sce_sys"
    meta.mkdir()
    param = generator["param_json"](ID, NAME, 60, 448)
    param["pubtools"]["creationDate"] = "2026-11-25 00:00:00"
    (meta / "param.json").write_text(json.dumps(param, indent=2) + "\n")
    generator["icon"](meta / "icon0.png", NAME)
    run("bash", a.vulkan / "tools/validate-assets.sh", meta)
    inputs = [TITLE / "main.cpp", TITLE / "stage-notices.py", Path(__file__),
              SMOKE / "compute.cpp", SMOKE / "compute.comp", SMOKE / "compute.hpp",
              a.cross / "compute.o", a.cross / "compute.spv", upstream / "src/platform.c",
              upstream / "src/platform.h", tool, runtime, meta / "param.json", meta / "icon0.png",
              a.cross / "toolchain.txt", upstream / "tools/link-title.sh",
              *(a.sdk / "target/lib" / name for name in ("libps5platform.a", "libc++.a",
                                                          "libc++abi.a", "libunwind.a"))]
    manifest = dict(title_id=ID, lab_revision=subprocess.check_output(
        ["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip(),
        template=TEMPLATE, ps5_vulkan=VULKAN, mesa=MESA, title_sdk=SDK,
        archive_sdk="b83202be73e930050e00de0f1b4d9ec46c0391bf", radv_sha256=RADV,
        hardware="NOT_RUN", inputs={p.name: digest(p) for p in inputs})
    identity = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    manifest["build_id"] = identity
    run(a.sdk / "bin/prospero-clang", "-std=c11", "-O2", "-c", upstream / "src/platform.c",
        "-o", work / "platform.o")
    run(a.sdk / "bin/prospero-clang++", "-std=c++20", "-O2", "-DM0_RADV_COMPUTE_PS5", "-DM0_RADV_COMPUTE_TIMING",
        f'-DM0_BUILD_ID="{identity}"', "-I", upstream / "src", "-I", SMOKE, "-I", a.radv / "include",
        "-c", TITLE / "main.cpp", "-o", work / "title.o")
    (work / "samples.txt").write_text("compute\n")
    run("bash", scripts / "link-title.sh", work, a.vulkan, a.sdk,
        work / "platform.o", work / "title.o", a.cross / "compute.o")
    app = a.output / "dist" / ID
    if json.loads((app / "sce_sys/param.json").read_text()) != param:
        raise ValueError("staged title metadata differs")
    run("bash", a.vulkan / "tools/validate-assets.sh", app / "sce_sys")
    for file in (app / "eboot.bin", app / "sce_module/libc.prx"):
        with (work / (file.name + ".inspect")).open("w") as log:
            run(tool, "self", "--inspect", "--file", file, stdout=log)
    if digest(app / "sce_module/libc.prx") != digest(runtime):
        raise ValueError("staged runtime differs")
    run(tool, "self", "--extract", "--file", app / "eboot.bin", "--out", work / "extracted.elf")
    # The signer stores selected segments and hashes its reconstruction, omitting
    # the standalone trailing PT_NOTE. Inspection verifies the stored digest.
    for name in ("eboot.bin", "libc.prx"):
        report = (work / (name + ".inspect")).read_text().splitlines()
        if "integrity: valid" not in report:
            raise ValueError(f"invalid {name} integrity")
    if "digest: " + digest(work / "extracted.elf") not in (work / "eboot.bin.inspect").read_text().splitlines():
        raise ValueError("extracted title digest mismatch")
    manifest["eboot_sha256"] = digest(app / "eboot.bin")
    manifest["files_sha256"] = {p.relative_to(app).as_posix(): digest(p)
                                for p in sorted(app.rglob("*")) if p.is_file()}
    (app / "build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    release = runpy.run_path(str(upstream / "tools/package-release.py"))
    zipfile = app.with_suffix(".zip")
    release["make_zip"](app, zipfile, datetime.date(2026, 11, 25))
    count = release["check_zip"](zipfile, app)
    print(f"{count} files verified. {digest(zipfile)}  {zipfile}")


if __name__ == "__main__":
    main()
