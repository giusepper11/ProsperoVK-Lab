#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate the M0 deployment artifact and optional retrieved run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import statistics
import subprocess
import tempfile
import zipfile

TOOLS = Path(__file__).resolve().parent
builder = runpy.run_path(str(TOOLS / "build-m0-title.py"))
smoke = runpy.run_path(str(TOOLS / "verify-m0-radv-compute.py"))
ID = builder["ID"]
digest = builder["digest"]
ARCHIVE_SDK = "b83202be73e930050e00de0f1b4d9ec46c0391bf"
LEGACY_ZIP = "072c62478a1292f1bd7b9fe96a6092aa909cbb5d7e70945926560ff2acecb87f"
METRICS = ("cpu_queue_submit_ns", "cpu_fence_wait_ns", "cpu_submit_to_completion_ns")
PINS = {key: builder[name] for key, name in
        (("template", "TEMPLATE"), ("ps5_vulkan", "VULKAN"), ("mesa", "MESA"),
         ("title_sdk", "SDK"), ("radv_sha256", "RADV"))}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=smoke["unique_fields"],
                      parse_constant=smoke["invalid_constant"])


def inputs():
    for name in ("TEMPLATE", "VULKAN", "MESA"):
        tree = Path(os.environ[name])
        rev = subprocess.check_output(["git", "-C", tree, "rev-parse", "HEAD"], text=True).strip()
        require(rev == builder[name], f"{name} pin mismatch")
        subprocess.run(["git", "-C", tree, "diff", "--quiet", "HEAD"], check=True)
    for name, pin in (("TITLE_SDK", builder["SDK"]), ("ARCHIVE_SDK", ARCHIVE_SDK)):
        require((Path(os.environ[name]) / ".ps5-sdk-revision").read_text().strip() == pin,
                f"{name} pin mismatch")
    subprocess.run(["git", "-C", os.environ["SDK_SOURCE"], "cat-file", "-e", builder["SDK"] + "^{commit}"], check=True)
    provenance = (Path(os.environ["RADV"]) / "PROVENANCE.txt").read_text().splitlines()
    for line in ("revision: " + builder["MESA"], "sdk: " + ARCHIVE_SDK, "archive sha256: " + builder["RADV"]):
        require(line in provenance, "RADV provenance mismatch")
    require(digest(Path(os.environ["RADV"]) / "lib/libvulkan_radeon.ps5.a") == builder["RADV"], "RADV digest")


def package(app):
    require(app.name == ID, "title folder name")
    paths = sorted(app.rglob("*"))
    require(not app.is_symlink() and all(not p.is_symlink() for p in paths), "symlink in title")
    files = {p.relative_to(app).as_posix(): digest(p) for p in paths if p.is_file()}
    m = read_json(app / "build.json")
    required = {"eboot.bin", "build.json", "sce_module/libc.prx", "sce_sys/param.json", "sce_sys/icon0.png",
                "LEGAL.txt", "licenses/GPL-3.0.txt", "licenses/PS5_Vulkan-NOTICE.md", "licenses/Template-MIT.md",
                "licenses/Mesa-license.rst", "licenses/Mesa/MIT", "licenses/LLVM-copyright",
                "licenses/icon-font-copyright", "licenses/dlmalloc-SOURCE", "licenses/musl-COPYRIGHT"}
    require(required <= files.keys(), f"missing package files: {sorted(required - files.keys())}")
    zpath = app.with_suffix(".zip")
    zhash = digest(zpath)
    if zhash != LEGACY_ZIP:
        require({"licenses/SoftFloat", "licenses/xxHash", "licenses/TRE", "licenses/BLAKE3-origin", "licenses/zlib-1.3.1.txt"} <= files.keys(),
                "missing component notices")
    hashes = {k: v for k, v in files.items() if k != "build.json"}
    require(m.get("files_sha256") == hashes or ("files_sha256" not in m and zhash == LEGACY_ZIP),
            "package checksum inventory")
    identity_fields = {k: v for k, v in m.items() if k not in ("eboot_sha256", "files_sha256", "build_id")}
    identity = hashlib.sha256(json.dumps(identity_fields, sort_keys=True).encode()).hexdigest()
    require(identity == m["build_id"], "build identity mismatch")
    require(m["title_id"] == ID and m["archive_sdk"] == ARCHIVE_SDK and
            all(m[k] == v for k, v in PINS.items()), "dependency or title pin mismatch")
    required_inputs = ("main.cpp", "stage-notices.py", "build-m0-title.py", "compute.cpp", "compute.comp",
                       "compute.hpp", "compute.o", "compute.spv", "platform.c", "platform.h",
                       "ps5-native-tool", "libc.prx", "param.json", "icon0.png", "toolchain.txt",
                       "link-title.sh", "libps5platform.a", "libc++.a", "libc++abi.a", "libunwind.a")
    require(re.fullmatch(r"[0-9a-f]{40}", m["lab_revision"]) and
            all(re.fullmatch(r"[0-9a-f]{64}", m["inputs"][k]) for k in required_inputs),
            "incomplete source or toolchain identity")
    param = read_json(app / "sce_sys/param.json")
    require(param["titleId"] == ID and param["conceptId"] == ID[4:] and
            param["localizedParameters"]["en-US"]["titleName"] == builder["NAME"] and
            param["contentId"].startswith(f"UP9000-{ID}_00-"), "title metadata")
    require(files["eboot.bin"] == m["eboot_sha256"], "executable digest")
    for name in ("sce_sys/icon0.png", "sce_sys/param.json", "sce_module/libc.prx"):
        require(files[name] == m["inputs"][Path(name).name], f"input mismatch: {name}")
    with zipfile.ZipFile(zpath) as z:
        expected = {ID + "/", *(ID + "/" + p.relative_to(app).as_posix() + ("/" if p.is_dir() else "") for p in paths)}
        require(len(z.infolist()) == len(expected) and set(z.namelist()) == expected, "ZIP inventory")
        for name, value in files.items():
            require(hashlib.sha256(z.read(f"{ID}/{name}")).hexdigest() == value, f"ZIP differs: {name}")
    vulkan = Path(os.environ["VULKAN"])
    native = vulkan / "build/host/ps5-native-tool"
    require(digest(native) == m["inputs"]["ps5-native-tool"], "native tool mismatch")
    subprocess.run(["bash", vulkan / "tools/validate-assets.sh", app / "sce_sys"], check=True, stdout=subprocess.DEVNULL)
    for name in ("eboot.bin", "sce_module/libc.prx"):
        inspect = subprocess.check_output([native, "self", "--inspect", "--file", app / name], text=True)
        require("integrity: valid" in inspect.splitlines(), f"SELF integrity: {name}")
    with tempfile.TemporaryDirectory() as tmp:
        elf = Path(tmp) / "extracted.elf"
        subprocess.run([native, "self", "--extract", "--file", app / "eboot.bin", "--out", elf],
                       stdout=subprocess.DEVNULL, check=True)
        require(identity.encode() in elf.read_bytes(), "executable lacks manifest build ID")
    return dict(BUILD="PASS", PACKAGE="PASS", build_id=identity, zip_sha256=zhash)


def run_report(run, identity):
    evidence = smoke["verify"](run)
    require((run / "start.log").read_text().splitlines()[0] == "build " + identity, "journal build identity")
    status = evidence["result"]["status"]
    output = dict(EXECUTE="PASS", CORRECTNESS=status, PERFORMANCE="NOT_RUN", SHELL_EXIT="UNCONFIRMED")
    if status != "PASS":
        require(not any((run / name).exists() for name in ("timing.json", "timing-exit-code.txt")),
                "timing after failed smoke")
        return output
    if not all((run / name).is_file() for name in ("timing.json", "timing-exit-code.txt")):
        return dict(output, PERFORMANCE="INCOMPLETE")
    timing = read_json(run / "timing.json")
    code = (run / "timing-exit-code.txt").read_text().strip()
    if timing.get("status") != "PASS":
        require(timing.get("case_id") == smoke["CASE_ID"] and code == "1" and
                timing.get("status") in smoke["STATUSES"], "invalid timing failure")
        return dict(output, PERFORMANCE=timing["status"])
    config = dict(case_id=smoke["CASE_ID"], schema_version=1, status="PASS", execution_target="ps5",
                  buffer_bytes=16384, groups=64, local_size=64, checked_words_per_dispatch=4096,
                  initial_checks=1, warmups=5, sample_count=30, verbose=False, timing_clock="steady_clock",
                  gpu_execution_ns=None, gpu_timing_unavailable_reason="timestamps_not_measured_by_probe")
    for key in ("vendor_id", "device_id", "api_version", "queue_family"):
        config[key] = evidence["result"][key]
    require(code == "0" and all(type(timing[k]) is type(v) and timing[k] == v for k, v in config.items()),
            "timing configuration or return code")
    for key in ("driver_version", "memory_type_index", "memory_property_flags"):
        require(smoke["is_uint32"](timing[key]), f"invalid {key}")
    summaries = {}
    for key in METRICS:
        metric = timing[key]
        a = metric["samples"]
        require(len(a) == 30 and all(type(v) is int and v >= 0 for v in a), f"{key} samples")
        expected = dict(median=statistics.median(a), p95=sorted(a)[28], min=min(a), max=max(a), range=max(a)-min(a))
        require(all(type(metric[k]) in (int, float) and metric[k] == v for k, v in expected.items()), f"{key} statistics")
        summaries[key] = expected
    require(all(c >= a + b for a, b, c in zip(*(timing[k]["samples"] for k in METRICS))), "timing interval bounds")
    return dict(output, PERFORMANCE="PASS", cpu_ns=summaries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inputs")
    sub.add_parser("package").add_argument("app", type=Path)
    check = sub.add_parser("run")
    check.add_argument("app", type=Path)
    check.add_argument("run", type=Path)
    args = parser.parse_args()
    try:
        if args.cmd == "inputs":
            inputs()
        else:
            out = package(args.app)
            out.update(DEPLOY="UNVERIFIED", EXECUTE="NOT_RUN", CORRECTNESS="NOT_RUN",
                       PERFORMANCE="NOT_RUN", SHELL_EXIT="NOT_RUN")
            if args.cmd == "run":
                out.update(run_report(args.run, out["build_id"]))
            print(json.dumps(out, indent=2))
            if args.cmd == "run" and (out["CORRECTNESS"], out["PERFORMANCE"]) != ("PASS", "PASS"):
                raise SystemExit(1)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        parser.exit(2, f"Validation failed: {error}\n")
