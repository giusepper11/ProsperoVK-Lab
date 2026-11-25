#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Verify the staged RADV archive's object and generated OpenCL provenance."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys


ARCHIVE = "src/amd/vulkan/libvulkan_radeon.a"
MODULES = ("src/poly/cl/libpoly.spv", "src/amd/vulkan/libradv_cl.spv")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ninja(build, *args):
    return subprocess.check_output(["ninja", "-t", *args], cwd=build, text=True)


def verify_archive(build, archiver, archive, digest, output):
    query = ninja(build, "query", ARCHIVE).splitlines()
    if query[:2] != [f"{ARCHIVE}:", "  input: STATIC_LINKER_RSP"]:
        raise ValueError("unexpected Ninja rule for the RADV archive")
    objects = [line.strip() for line in query[2:query.index("  outputs:")]]
    if not objects or any(Path(path).suffix != ".o" for path in objects):
        raise ValueError("the RADV archive must have an ordered list of object inputs")
    members = subprocess.check_output([archiver, "t", archive], text=True).splitlines()
    if members != [Path(path).name for path in objects]:
        raise ValueError("Ninja object order differs from the staged RADV archive")

    reassembled = output / "radv-reassembled.a"
    subprocess.run([archiver, "csrD", reassembled, *objects], cwd=build, check=True)
    if sha256(reassembled) != digest or sha256(build / ARCHIVE) != digest:
        raise ValueError("Ninja or reassembled RADV archive differs from the staged archive")

    compdb = json.loads((build / "compile_commands.json").read_text())
    compilation = {entry["output"]: entry for entry in compdb}
    roster = output / "radv-archive-inputs.tsv"
    with roster.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("position", "member", "object", "object_sha256", "source", "source_sha256"))
        for index, obj in enumerate(objects, 1):
            entry = compilation[obj]
            source = Path(entry["directory"]) / entry["file"]
            writer.writerow((index, members[index - 1], obj, sha256(build / obj),
                             entry["file"], sha256(source)))
    print(f"Reassembled archive matches {len(members)} ordered members: {digest}")
    return [reassembled, roster]


def verify_generated_module(build, target, output):
    spv = Path(target)
    cpp, header = (spv.with_suffix(ext) for ext in (".cpp", ".h"))
    clc = shlex.split(ninja(build, "commands", "-s", str(spv)))
    bindgen = shlex.split(ninja(build, "commands", "-s", str(cpp)))
    if (len(clc) < 5 or len(bindgen) != 4
            or Path(clc[0]).name != "mesa_clc" or clc[1:4] != ["-o", str(spv), "--depfile"]
            or Path(bindgen[0]).name != "vtn_bindgen2" or bindgen[1:] != list(map(str, (spv, cpp, header)))):
        raise ValueError(f"unexpected Ninja generator commands for {spv}")

    replay = [output / artifact.name for artifact in (spv, cpp, header)]
    depfile = output / (spv.name + ".d")
    clc[2], clc[4] = str(replay[0]), str(depfile)
    bindgen[1:] = list(map(str, replay))
    commands = output / (spv.stem + "-replay.json")
    commands.write_text(json.dumps({"cwd": str(build), "commands": [clc, bindgen]}, indent=2) + "\n")
    for command in (clc, bindgen):
        subprocess.run(command, cwd=build, check=True)

    for artifact, rebuilt in zip((spv, cpp, header), replay):
        if sha256(build / artifact) != sha256(rebuilt):
            raise ValueError(f"regenerated {artifact} differs from the pinned build")
    subprocess.run(["spirv-val", "--target-env", "spv1.4", replay[0]], check=True)

    dependencies = output / (spv.stem + "-ninja-deps.txt")
    dependencies.write_text(ninja(build, "deps", str(spv)))
    dep_lines = dependencies.read_text().splitlines()
    if not dep_lines or not dep_lines[0].endswith(" (VALID)"):
        raise ValueError(f"missing valid Ninja dependency record for {spv}")
    inputs = {(build / line.strip()).resolve() for line in dep_lines[1:] if line.startswith("    ")}
    prefix = f"{replay[0]}: "
    recorded = depfile.read_text()
    if not recorded.startswith(prefix):
        raise ValueError(f"unexpected replay dependency file for {spv}")
    replay_inputs = {(build / path).resolve() for path in shlex.split(recorded[len(prefix):])}
    if not inputs or replay_inputs != inputs:
        raise ValueError(f"replayed OpenCL inputs differ from the Ninja dependency record for {spv}")
    print(f"{spv.name}: SPIR-V, C++ and header match, {len(inputs)} recorded OpenCL inputs")
    return replay + sorted(inputs) + [depfile, commands, dependencies, Path(clc[0]), Path(bindgen[0])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output_dir", "mesa_build", "sdk", "radv"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()

    try:
        output = args.output_dir.resolve()
        build = args.mesa_build.resolve()
        sdk = args.sdk.resolve()
        radv = args.radv.resolve()
        mesa_tree = build.parent / "radv-src"
        provenance = radv / "PROVENANCE.txt"
        pin = build / ".radv-build-id"
        source_pin = mesa_tree / ".revision"
        sdk_pin = sdk / ".ps5-sdk-revision"
        archive = radv / "lib" / "libvulkan_radeon.ps5.a"
        archiver = sdk / "bin" / "prospero-ar"
        metadata = dict(line.split(": ", 1) for line in provenance.read_text().splitlines() if ": " in line)
        digest = sha256(archive)
        revision = pin.read_text().strip()
        if (metadata.get("archive sha256") != digest or metadata.get("revision") != revision
                or source_pin.read_text().strip() != revision or metadata.get("sdk") != sdk_pin.read_text().strip()):
            raise ValueError("staged archive digest, Mesa revision or SDK revision conflicts with the build provenance")

        output.mkdir()
        evidence = verify_archive(build, archiver, archive, digest, output)
        for module in MODULES:
            evidence.extend(verify_generated_module(build, module, output))
        for path in sorted(set(evidence)):
            if path.is_relative_to(mesa_tree):
                pinned = subprocess.check_output(
                    ["git", "-C", metadata["fork"], "show", f"{revision}:{path.relative_to(mesa_tree)}"],
                )
                if sha256(path) != hashlib.sha256(pinned).hexdigest():
                    raise ValueError(f"OpenCL input differs from the pinned Mesa source: {path}")

        toolchain = output / "toolchain.txt"
        with toolchain.open("w") as stream:
            for command in ("ninja", archiver, "spirv-val"):
                subprocess.run([command, "--version"], stdout=stream, check=True)
        evidence.extend([Path(__file__).resolve(), provenance, pin, source_pin, sdk_pin, archive, archiver,
                         build / "build.ninja", build / "compile_commands.json", toolchain])
        checksums = []
        for path in sorted(set(evidence)):
            name = path.relative_to(output) if path.is_relative_to(output) else path
            checksums.append(f"{sha256(path)}  {name}\n")
        (output / "SHA256SUMS").write_text("".join(checksums))
        print(f"RADV source evidence: {output}")
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"RADV source check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
