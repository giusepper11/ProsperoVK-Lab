#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the focused Khronos CTS link inputs for the M0 title."""
import hashlib
import os
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import tarfile

FIXTURE = Path(__file__).resolve().parent
CTS_REVISION = "f6a29701220f34dd1407513bfe80d74ca7b392ce"
CASE_ID = "dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation"
GIT_PINS = {
    "amber": "53a4c8934bf7335d27c694e9fdac9ae1b180c0d2",
    "glslang": "715c8500e7cd67f2eba9e60e98852a1ed49d2f15",
    "jsoncpp": "9059f5cad030ba11d37818847443a53918c327b1",
    "spirv-headers": "6dd7ba990830f7c15ac1345ff3b43ef6ffdad216",
    "spirv-tools": "2d14d2e76aa7de72404b17078eda15c20a6a0389",
    "video_generator": "426300e12a5cc5d4676807039a1be237a2b68187",
    "vulkan-docs": "4abe0260bbd8e59930786eed645481808a3fe6f1",
    "vulkan-video-samples": "aaf915a0e08d679d1e8b835c30e6a346ab0c7ad2",
}
TAR_PINS = {
    "libpng": ("v1.6.50.tar.gz", "71158e53cfdf2877bc99bcab33641d78df3f48e6e0daad030afe9cb8c031aa46"),
    "zlib": ("zlib-1.2.13.tar.gz", "b3a24de97a8fdbc835b9833169501030b8977031bcb54b3b3ac13740f846ab30"),
}
RENDERDOC_PIN = "e7b5f0aa5b1b0eadc63a1c624c0ca7f5af133aa857d6a4271b0ef3d0bdb6868e"
EXTERNAL_PINS = {**GIT_PINS, **{name: pin for name, (_, pin) in TAR_PINS.items()}, "renderdoc": RENDERDOC_PIN}
NOTICES = {
    "CTS-LICENSE": "LICENSE",
    "CTS-NOTICE": "NOTICE",
    "CTS-Vulkan-LICENSE": "external/vulkancts/LICENSE",
    "CTS-amber-LICENSE": "external/amber/src/LICENSE",
    "CTS-glslang-LICENSE.txt": "external/glslang/src/LICENSE.txt",
    "CTS-spirv-headers-LICENSE": "external/spirv-headers/src/LICENSE",
    "CTS-spirv-tools-LICENSE": "external/spirv-tools/src/LICENSE",
    "CTS-libpng-LICENSE": "external/libpng/src/LICENSE",
}
RENDERDOC_HEADER = Path("external/renderdoc/src/renderdoc_app.h")
NOTICE_NAMES = (*NOTICES, "CTS-renderdoc-LICENSE")
RUNNER = "external/vulkancts/modules/vulkan/CMakeFiles/deqp-vk.dir/__/__/__/__/framework/platform/tcuMain.cpp.o"


def git(path, *args):
    return subprocess.check_output(["git", "-C", path, *args], text=True).strip()


def verify_checkout(path, revision, overlays=None):
    if git(path, "rev-parse", "HEAD") != revision:
        raise ValueError(f"wrong revision of {path}; expected {revision}")
    overlays = {} if overlays is None else overlays
    changes = git(path, "diff", "--name-only", "HEAD").splitlines()
    if any(name not in overlays or (path / name).read_bytes() != overlays[name].read_bytes()
           for name in changes) or git(path, "ls-files", "--others", "--exclude-standard"):
        raise ValueError(f"unexpected source changes in {path}")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_tar_sources(external, name, filename, pin):
    archive = external / name / "packages" / filename
    extracted = external / name / "src"
    if digest(archive) != pin:
        raise ValueError(f"archive digest mismatch: {archive}")
    expected = set()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if member.isfile():
                path = member.name.split("/", 1)[1]
                expected.add(path)
                file = extracted / path
                with tar.extractfile(member) as contents:
                    if digest(file) != hashlib.file_digest(contents, "sha256").hexdigest():
                        raise ValueError(f"extracted source digest mismatch: {file}")
    if name == "libpng":
        expected.add("pnglibconf.h")
        if digest(extracted / "pnglibconf.h") != digest(extracted / "scripts/pnglibconf.h.prebuilt"):
            raise ValueError("libpng header differs from the upstream prebuilt header")
    actual = {path.relative_to(extracted).as_posix() for path in extracted.rglob("*") if path.is_file()}
    if actual != expected:
        raise ValueError(f"unexpected files in {extracted}: {sorted(actual ^ expected)}")


def verify_sources(source):
    verify_checkout(source, CTS_REVISION)
    external = source / "external"
    for name, pin in GIT_PINS.items():
        overlays = None
        if name == "jsoncpp":
            # The pinned CTS CMakeLists copies these files on every configure.
            overlays = {
                "include/json/config.h": external / name / "config.h.cts",
                "src/lib_json/json_valueiterator.inl": external / name / "json_valueiterator.inl.cts",
            }
        verify_checkout(external / name / "src", pin, overlays)
    for name, (filename, pin) in TAR_PINS.items():
        verify_tar_sources(external, name, filename, pin)
    if digest(source / RENDERDOC_HEADER) != RENDERDOC_PIN:
        raise ValueError("RenderDoc header digest mismatch")


def record_toolchain(sdk, output):
    host_clang = os.environ.get("PS5_CLANG") or shutil.which("clang")
    if not host_clang:
        raise ValueError("Clang is required for the RADV link recipe")
    with output.open("w") as log:
        for name, command in (
            ("title C compiler", sdk / "bin/prospero-clang"),
            ("title C++ compiler", sdk / "bin/prospero-clang++"),
            ("title linker", sdk / "bin/prospero-lld"),
            ("host Clang", host_clang), ("CMake", "cmake"),
            ("Ninja", "ninja"), ("Python", sys.executable),
        ):
            version = subprocess.check_output([command, "--version"], text=True)
            print(name, file=log)
            for line in version.splitlines():
                if not line.startswith("InstalledDir:"):
                    print(line, file=log)
        resource = subprocess.check_output([host_clang, "--print-resource-dir"], text=True).strip()
        builtins = Path(resource) / "lib/linux/libclang_rt.builtins-x86_64.a"
        print(f"RADV link compiler-rt builtins SHA-256 {digest(builtins)}", file=log)


def prepare(source, sdk, radv, work):
    verify_sources(source)
    toolchain = work / "cts-toolchain.txt"
    record_toolchain(sdk, toolchain)
    build = work / "cts"
    build.mkdir()
    subprocess.run(["bash", FIXTURE / "configure-ps5.sh", build, source, sdk, radv], check=True)
    archive_list = FIXTURE / "focused-archives.txt"
    archives = archive_list.read_text().splitlines()
    log_path = build / "dependencies.log"
    with log_path.open("w") as log:
        proc = subprocess.run(["ninja", "-C", build, "-j4", *archives, RUNNER],
                              stdout=log, stderr=subprocess.STDOUT)
    if proc.returncode:
        print("\n".join(log_path.read_text().splitlines()[-60:]))
        proc.check_returncode()
    objects = runpy.run_path(str(FIXTURE / "compile-focused.py"))["compile_focused"](build, work)
    command = subprocess.check_output(["ninja", "-C", build, "-t", "commands", "-s", RUNNER], text=True)
    args = shlex.split(command)
    runner = work / "cts-runner.o"
    args[args.index("-o") + 1] = str(runner)
    args.extend(["-Dmain=m0_cts_main", "-ffunction-sections", "-fdata-sections"])
    subprocess.run(args, cwd=build, check=True)
    (work / "cts-runner-command.txt").write_text(shlex.join(args) + "\n")
    libraries = [build / name for name in archives]
    # The focused registrar needs only a subset of the CTS helper archives. RADV supplies zlib.
    link_args = ["--no-undefined", "--gc-sections", "--wrap=pathconf", runner, *objects,
                 "--start-group", *libraries, "--end-group"]
    case_sources = source / "external/vulkancts/modules/vulkan/compute"
    inputs = [Path(__file__), archive_list, toolchain, *(FIXTURE / name for name in (
        "configure-ps5.sh", "title.cpp", "headless-platform.cpp", "headless-resolver.cpp",
        "focused-package.cpp", "compile-focused.py")),
        source / "framework/platform/tcuMain.cpp",
        case_sources / "vktComputeBasicComputeShaderTests.cpp",
        case_sources / "vktComputeBasicComputeShaderTests.hpp", runner, *objects, *libraries]
    return {"revision": CTS_REVISION, "case": CASE_ID, "externals": EXTERNAL_PINS}, inputs, link_args


def compile_entry(sdk, template_src, work, build_id, title_id):
    output = work / "title.o"
    subprocess.run([sdk / "bin/prospero-clang++", "-std=c++20", "-O2", "-DM0_CTS_USE_RADV",
                    f'-DM0_BUILD_ID="{build_id}"', f'-DM0_TITLE_ID="{title_id}"',
                    f'-DM0_CTS_CASE_ID="{CASE_ID}"', "-I", template_src,
                    "-c", FIXTURE / "title.cpp", "-o", output], check=True)
    return output


def stage_notices(source, app):
    licenses = app / "licenses"
    for name, path in NOTICES.items():
        shutil.copyfile(source / path, licenses / name)
    header = (source / RENDERDOC_HEADER).read_bytes().split(b"*/", 1)[0]
    (licenses / "CTS-renderdoc-LICENSE").write_bytes(header + b"*/\n")
    (app / "LEGAL.txt").write_text(
        "ProsperoVK-Lab is GPL-3.0-or-later. The platform lifecycle and generated icon "
        "come from PS5_VulkanTemplate (MIT). The runtime module and CRT come from PS5_Vulkan. "
        "This title runs one Khronos VK-GL-CTS case using the upstream runner and QPA writer. "
        "See build.json for source and dependency identities and licenses/ for notices.\n")
