#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compile the focused registrar and upstream CTS executor objects."""

import argparse
from pathlib import Path
import shlex
import subprocess


SOURCES = {
    "deqp-vk-package": (
        "vktTestPackage.cpp", "vktTestCase.cpp", "vktTestCaseUtil.cpp", "vktShaderLibrary.cpp",
        "vktTestGroupUtil.cpp", "vktCustomInstancesDevices.cpp", "vktContextManager.cpp",
    ),
    "deqp-vk-amber": ("vktAmberHelper.cpp", "vktAmberTestCase.cpp", "vktAmberTestCaseUtil.cpp"),
    "deqp-vk": ("vktTestPackageEntry.cpp",),
}


def compile_focused(build, output):
    fixture = Path(__file__).resolve().parent
    listing = subprocess.check_output(["ninja", "-t", "targets", "all"], cwd=build, text=True)
    targets = [line.split(": ", 1)[0] for line in listing.splitlines()]
    objects = []
    with (output / "focused-compile-commands.txt").open("w") as log:
        for library, sources in SOURCES.items():
            for source in sources:
                matches = [target for target in targets
                           if f"/{library}.dir/" in target and target.endswith(f"/{source}.o")]
                if len(matches) != 1:
                    raise ValueError(f"expected one {library} compile rule for {source}")
                command = subprocess.check_output(["ninja", "-t", "commands", "-s", matches[0]],
                                                  cwd=build, text=True)
                args = shlex.split(command)
                for flag in ("-MF", "-MT"):
                    if flag in args:
                        index = args.index(flag)
                        del args[index:index + 2]
                if "-MD" in args:
                    args.remove("-MD")
                if source == "vktTestPackageEntry.cpp":
                    index = args.index("-c") + 1
                    module = Path(args[index]).parent
                    args[index] = str(fixture / "focused-package.cpp")
                    args.extend([f"-I{module}", f"-I{module / 'compute'}"])
                    source = "focused-package.cpp"
                object_path = output / f"{source}.o"
                args[args.index("-o") + 1] = str(object_path)
                args.extend(["-ffunction-sections", "-fdata-sections"])
                print(shlex.join(args), file=log)
                subprocess.run(args, cwd=build, check=True)
                objects.append(object_path)
    return objects


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cts_build", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    for path in compile_focused(args.cts_build.resolve(), args.output.resolve()):
        print(path)
