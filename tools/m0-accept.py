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
import xml.etree.ElementTree as ET
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
    title_id = app.name
    require(re.fullmatch(r"PPSA[0-9]{5}", title_id), "title folder name")
    paths = sorted(app.rglob("*"))
    require(not app.is_symlink() and all(not p.is_symlink() for p in paths), "symlink in title")
    files = {p.relative_to(app).as_posix(): digest(p) for p in paths if p.is_file()}
    m = read_json(app / "build.json")
    workload = m.get("workload", "compute")
    require(workload in ("compute", "cts", "m1") and (workload == "compute") == (title_id == ID)
            and (workload != "m1" or title_id == builder["M1_ID"]),
            "workload or title ID mismatch")
    required = {"eboot.bin", "build.json", "sce_module/libc.prx", "sce_sys/param.json", "sce_sys/icon0.png",
                "LEGAL.txt", "licenses/GPL-3.0.txt", "licenses/PS5_Vulkan-NOTICE.md", "licenses/Template-MIT.md",
                "licenses/Mesa-license.rst", "licenses/Mesa/MIT", "licenses/LLVM-copyright",
                "licenses/icon-font-copyright", "licenses/dlmalloc-SOURCE", "licenses/musl-COPYRIGHT"}
    if workload == "cts":
        cts = runpy.run_path(str(builder["CTS"] / "title-build.py"))
        require(m.get("cts") == dict(revision=cts["CTS_REVISION"], case=cts["CASE_ID"],
                                    externals=cts["EXTERNAL_PINS"]), "CTS provenance mismatch")
        require(m.get("lab_worktree") in ("clean", "dirty"), "missing CTS worktree status")
        required.update(f"licenses/{name}" for name in cts["NOTICE_NAMES"])
    if workload == "m1":
        require(m.get("case_id") == builder["M1_CASE"] and m.get("lab_worktree") in ("clean", "dirty"),
                "M1 case or worktree provenance")
        require(m.get("shader_sha256") == m["inputs"]["compute.spv"], "M1 shader provenance")
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
    require(m["title_id"] == title_id and m["archive_sdk"] == ARCHIVE_SDK and
            all(m[k] == v for k, v in PINS.items()), "dependency or title pin mismatch")
    required_inputs = ("stage-notices.py", "build-m0-title.py", "platform.c", "platform.h",
                       "ps5-native-tool", "libc.prx", "param.json", "icon0.png",
                       "link-title.sh", "libps5platform.a", "libc++.a", "libc++abi.a", "libunwind.a")
    if workload == "cts":
        archive_list = builder["CTS"] / "focused-archives.txt"
        required_inputs += (
            "title-build.py", "title.cpp", "configure-ps5.sh", "focused-archives.txt",
            "headless-platform.cpp", "headless-resolver.cpp", "focused-package.cpp",
            "compile-focused.py", "tcuMain.cpp", "cts-runner.o", "focused-package.cpp.o",
            "cts-toolchain.txt", "vktComputeBasicComputeShaderTests.cpp", "vktComputeBasicComputeShaderTests.hpp",
            *(Path(name).name for name in archive_list.read_text().splitlines()),
        )
    elif workload == "m1":
        required_inputs += ("title.cpp", "runner.cpp", "runner.hpp", "inventory.cpp", "inventory.hpp",
                            "compute.cpp", "compute.hpp", "storage.comp", "CMakeLists.txt",
                            "compute.spv", "compute_spv.hpp", "runner.o", "inventory.o", "compute.o",
                            "toolchain.txt", "run-v1.schema.json")
    else:
        required_inputs += ("main.cpp", "compute.cpp", "compute.comp", "compute.hpp",
                            "compute.o", "compute.spv", "toolchain.txt")
    require(re.fullmatch(r"[0-9a-f]{40}", m["lab_revision"]) and
            set(required_inputs) <= m["inputs"].keys() and
            all(re.fullmatch(r"[0-9a-f]{64}", value) for value in m["inputs"].values()),
            "incomplete source or toolchain identity")
    param = read_json(app / "sce_sys/param.json")
    title_name = {"cts": builder["CTS_NAME"], "compute": builder["NAME"], "m1": builder["M1_NAME"]}[workload]
    require(param["titleId"] == title_id and param["conceptId"] == title_id[4:] and
            param["localizedParameters"]["en-US"]["titleName"] == title_name and
            param["contentId"].startswith(f"UP9000-{title_id}_00-"), "title metadata")
    require(files["eboot.bin"] == m["eboot_sha256"], "executable digest")
    for name in ("sce_sys/icon0.png", "sce_sys/param.json", "sce_module/libc.prx"):
        require(files[name] == m["inputs"][Path(name).name], f"input mismatch: {name}")
    with zipfile.ZipFile(zpath) as z:
        expected = {title_id + "/", *(title_id + "/" + p.relative_to(app).as_posix() + ("/" if p.is_dir() else "") for p in paths)}
        require(len(z.infolist()) == len(expected) and set(z.namelist()) == expected, "ZIP inventory")
        for name, value in files.items():
            require(hashlib.sha256(z.read(f"{title_id}/{name}")).hexdigest() == value, f"ZIP differs: {name}")
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
        payload = elf.read_bytes()
        require(identity.encode() in payload, "executable lacks manifest build ID")
        if workload == "cts":
            require(all(marker.encode() in payload for marker in (title_id, cts["CASE_ID"])),
                    "executable lacks CTS title ID or case")
        elif workload == "m1":
            markers = (title_id, m["lab_revision"], m["case_id"], m["shader_sha256"])
            require(all(marker.encode() in payload for marker in markers), "executable lacks M1 provenance")
    return dict(BUILD="PASS", PACKAGE="PASS", build_id=identity, zip_sha256=zhash, workload=workload)


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


def m1_run_report(run, app, identity):
    manifest = read_json(app / "build.json")
    revision = manifest["lab_revision"]
    start = (run / "start.log").read_text().splitlines()
    require(len(start) == 6 and start[:3] == [f"build {identity}", f"revision {revision}", f"title {app.name}"],
            "M1 title journal differs from the verified manifest")
    require(start[3] in ("case inventory", f"case {manifest['case_id']}"), "invalid M1 selection")
    case = None if start[3] == "case inventory" else manifest["case_id"]
    device = re.fullmatch(r"device (0|[1-9][0-9]{0,9})", start[4])
    require(device and int(device[1]) <= 0xFFFFFFFF, "invalid M1 device index")
    device_index = int(device[1])
    path = re.fullmatch(r"path /app0/(run-[0-9]{6})", start[5])
    require(path, "invalid M1 capture path")
    receipt = run / "retrieval.json"
    if receipt.exists():
        capture = read_json(receipt)
        require((capture["run"], capture["title_id"], capture["build_id"]) ==
                (path[1], app.name, identity), "M1 journal differs from retrieval receipt")
    report = run / "report.json"
    subprocess.run(["python3", "-B", TOOLS / "validate-m1.py", report],
                   stdout=subprocess.DEVNULL, check=True)
    data = read_json(report)
    require((data["build_id"], data["revision"], data["target"], data["case_id"], data["shader_sha256"],
             data["device_index"], data["run_id"]) == (identity, revision, "ps5", case,
                                       manifest["shader_sha256"] if case else None, device_index, path[1]),
            "M1 report provenance mismatch")
    status = data["status"]
    journal_path = run / "report.json.start.json"
    if case is None:
        require(not journal_path.exists(), "unexpected M1 inventory case journal")
    elif status != "NOT_RUN":
        journal = dict(schema_version=1, event="start", case_id=case, device_index=device_index,
                       target="ps5", build_id=identity, revision=revision, run_id=path[1])
        require(read_json(journal_path) == journal, "M1 case journal mismatch")
    code = (run / "exit-code.txt").read_bytes()
    allowed_codes = {"PASS": (b"0\n",), "NOT_RUN": (b"1\n", b"2\n")}.get(status, (b"1\n",))
    require(code in allowed_codes, "M1 runner return code disagrees with status")
    execution = {"NOT_RUN": "NOT_RUN", "UNSUPPORTED": "NOT_RUN",
                 "TIMEOUT": "TIMEOUT", "ERROR": "ERROR"}.get(status, "PASS")
    return dict(EXECUTE=execution, CORRECTNESS=status if case else "NOT_RUN", PERFORMANCE="NOT_RUN",
                SHELL_EXIT="UNCONFIRMED", case_id=case, device_index=device_index, report_sha256=digest(report))


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
                if out["workload"] == "cts":
                    report = runpy.run_path(str(TOOLS / "m0-cts-report.py"))["cts_run_report"]
                    out.update(report(args.run, args.app, out["build_id"]))
                elif out["workload"] == "m1":
                    out.update(m1_run_report(args.run, args.app, out["build_id"]))
                else:
                    out.update(run_report(args.run, out["build_id"]))
            print(json.dumps(out, indent=2))
            if args.cmd == "run":
                expected_performance = "PASS" if out["workload"] == "compute" else "NOT_RUN"
                expected_correctness = "NOT_RUN" if out["workload"] == "m1" and out["case_id"] is None else "PASS"
                if (out["EXECUTE"], out["CORRECTNESS"], out["PERFORMANCE"]) != (
                        "PASS", expected_correctness, expected_performance):
                    raise SystemExit(1)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.CalledProcessError,
            zipfile.BadZipFile, ET.ParseError) as error:
        parser.exit(2, f"Validation failed: {error}\n")
