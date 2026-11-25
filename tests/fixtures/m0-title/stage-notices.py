#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Notice hook for the offscreen title linked by the template's link-title.sh."""
import os
from pathlib import Path
import shutil
import sys
import subprocess

app, vulkan, archive = map(Path, sys.argv[1:])
licenses = app / "licenses"
licenses.mkdir()
for source, name in [
    (Path(os.environ["LAB_ROOT"]) / "tests/fixtures/m0-title/notices/zlib-1.3.1.txt", "zlib-1.3.1.txt"),
    (Path(os.environ["LAB_ROOT"]) / "LICENSE", "GPL-3.0.txt"),
    (Path(os.environ["TEMPLATE"]) / "LICENSE.md", "Template-MIT.md"),
    (vulkan / "NOTICE.md", "PS5_Vulkan-NOTICE.md"),
    (Path(os.environ["MESA"]) / "docs/license.rst", "Mesa-license.rst"),
    (Path("/usr/share/doc/libllvm21/copyright"), "LLVM-copyright"),
    (Path("/usr/share/doc/fonts-dejavu-core/copyright"), "icon-font-copyright"),
]:
    shutil.copyfile(source, licenses / name)
for path, name in [("platform/src/regex/COPYRIGHT.musl", "musl-COPYRIGHT"),
                   ("platform/src/dlmalloc/SOURCE", "dlmalloc-SOURCE")]:
    contents = subprocess.check_output(["git", "-C", os.environ["SDK_SOURCE"], "show",
                                        os.environ["SDK_REVISION"] + ":" + path])
    (licenses / name).write_bytes(contents)
# Preserve file-level binary notices that the generic Mesa license directory omits.
mesa = Path(os.environ["MESA"])
for source, name in [("softfloat.c", "SoftFloat"), ("xxhash.h", "xxHash")]:
    header = (mesa / "src/util" / source).read_bytes().split(b"*/", 1)[0]
    (licenses / name).write_bytes(header + b"*/\n")
shutil.copyfile(mesa / "src/util/blake3/README", licenses / "BLAKE3-origin")
tre = subprocess.check_output(["git", "-C", os.environ["SDK_SOURCE"], "show",
                               os.environ["SDK_REVISION"] + ":platform/src/regex/regcomp.c"])
(licenses / "TRE").write_bytes(tre.split(b"*/", 1)[0] + b"*/\n")
shutil.copytree(Path(os.environ["MESA"]) / "licenses", licenses / "Mesa")
(app / "LEGAL.txt").write_text(
    "ProsperoVK-Lab is GPL-3.0-or-later. The platform lifecycle and generated icon "
    "come from PS5_VulkanTemplate (MIT). The notification ABI follows John Törnblom's "
    "public SDK sample. The runtime module and CRT come from PS5_Vulkan. "
    "The compute shader is embedded in eboot.bin. See build.json for input identities "
    "and licenses/ for notices.\n")
