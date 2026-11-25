#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Relink the existing pinned Linux CTS build with the M0 headless adapter."""

import argparse
from pathlib import Path
import shlex
import subprocess
import sys


def ninja_command(build, target):
    recipe = subprocess.check_output(["ninja", "-t", "commands", "-s", target], cwd=build, text=True)
    return shlex.split(recipe)


def relink(build, output, vulkan_headers, vulkan_library, focused_objects):
    fixture = Path(__file__).resolve().parent
    platform_archive = "framework/platform/libtcutil-platform.a"
    stock_object = "framework/platform/CMakeFiles/tcutil-platform.dir/lnx/tcuLnxPlatform.cpp.o"
    compile_args = ninja_command(build, stock_object)
    for option in ("-MT", "-MF"):
        if option in compile_args:
            index = compile_args.index(option)
            del compile_args[index:index + 2]
    if "-MD" in compile_args:
        compile_args.remove("-MD")
    compile_args.append(f"-I{vulkan_headers}")

    recipe = ninja_command(build, "external/vulkancts/modules/vulkan/deqp-vk")
    if recipe[:2] != [":", "&&"] or recipe[-2:] != ["&&", ":"]:
        raise ValueError("expected the stock single-command Linux CTS link rule")
    link = recipe[2:-2]
    link = [argument for argument in link if not argument.startswith("-Wl,--dependency-file=")]
    if link.count(platform_archive) != 1:
        raise ValueError("expected exactly one stock Linux platform archive in the link rule")
    if focused_objects:
        package = "external/vulkancts/modules/vulkan/libdeqp-vk-package.a"
        entries = [arg for arg in link if arg.endswith("/vktTestPackageEntry.cpp.o")]
        if len(entries) != 1 or link.count(package) != 1:
            raise ValueError("expected one CTS registry object and package archive in the link rule")
        link.remove(entries[0])
        index = link.index(package)
        link[index:index + 1] = [str(Path(path).resolve(strict=True))
                                for path in focused_objects.read_text().splitlines()]
        link.append("-Wl,--gc-sections")

    output.mkdir()
    objects = []
    with (output / "compile-command.txt").open("w") as log:
        for unit in ("headless-platform", "headless-resolver"):
            object_path = str(output / f"{unit}.o")
            compile_args[compile_args.index("-o") + 1] = object_path
            compile_args[compile_args.index("-c") + 1] = str(fixture / f"{unit}.cpp")
            print(shlex.join(compile_args), file=log)
            subprocess.run(compile_args, cwd=build, check=True)
            objects.append(object_path)

    link[link.index("-o") + 1] = str(output / "deqp-vk-local-headless")
    index = link.index(platform_archive)
    link[index:index + 1] = objects
    link.append(str(vulkan_library))
    (output / "link-command.txt").write_text(shlex.join(link) + "\n")
    subprocess.run(link, cwd=build, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("linux_build", type=Path)
    parser.add_argument("new_build_dir", type=Path)
    parser.add_argument("vulkan_headers", type=Path)
    parser.add_argument("vulkan_library", type=Path)
    parser.add_argument("--focused-objects", type=Path)
    args = parser.parse_args()

    try:
        relink(args.linux_build.resolve(strict=True), args.new_build_dir.resolve(),
               args.vulkan_headers.resolve(strict=True), args.vulkan_library.resolve(strict=True),
               args.focused_objects)
    except (OSError, ValueError) as error:
        print(f"Build of the Linux CTS adapter failed: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Linux CTS build command exited {error.returncode}: {error.cmd[0]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
