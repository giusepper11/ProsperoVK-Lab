#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Inventory public link-stub candidates for an M0 pre-packaging ELF."""

import argparse
from collections import defaultdict
import csv
import os
from pathlib import Path
import re
import subprocess
import sys


def readelf(option, path):
    return subprocess.check_output(
        ["readelf", "--wide", option, "--", path],
        text=True, env=os.environ | {"LC_ALL": "C"},
    )


def dynamic_names(path, tag):
    text = readelf("--dynamic", path)
    return re.findall(rf"\({tag}\)[^\n]*\[([^\]\n]+)\]", text)


def dynamic_symbols(path, undefined):
    for line in readelf("--dyn-syms", path).splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].removesuffix(":").isdigit():
            continue
        _, _, _, kind, binding, visibility, section, name, *_ = fields
        if ((section == "UND") == undefined and binding in ("GLOBAL", "WEAK", "UNIQUE")
                and visibility in ("DEFAULT", "PROTECTED")):
            yield name, binding, kind


def collect_imports(elf, stub_files):
    needed = set(dynamic_names(elf, "NEEDED"))
    imports = sorted(dynamic_symbols(elf, undefined=True))
    if not needed or not imports:
        raise ValueError("expected dynamic library declarations and imports in the linked ELF")

    export_candidates = defaultdict(set)
    declared_stubs = set()
    for stub in stub_files:
        sonames = dynamic_names(stub, "SONAME")
        if len(sonames) == 1 and sonames[0] in needed:
            soname = sonames[0]
            declared_stubs.add(soname)
            for name, binding, kind in dynamic_symbols(stub, undefined=False):
                export_candidates[name].add((soname, stub.name, binding, kind))

    if needed - declared_stubs:
        raise ValueError("missing staged link stubs for " + ", ".join(sorted(needed - declared_stubs)))
    if any("@" in name for name, _, _ in imports):
        raise ValueError("expected unversioned dynamic imports in the linked ELF")
    missing = [name for name, binding, _ in imports if binding != "WEAK" and name not in export_candidates]
    if missing:
        raise ValueError("no candidate stub exports strong imports: " + ", ".join(missing))

    return imports, export_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("stubs", type=Path, nargs="+")
    args = parser.parse_args()

    try:
        imports, candidates = collect_imports(args.elf, args.stubs)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ELF import inventory failed: {error}", file=sys.stderr)
        return 1

    writer = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    writer.writerow(("symbol", "import_binding", "import_type", "soname", "link_stub", "stub_binding", "stub_type"))
    for name, binding, kind in imports:
        exports = sorted(candidates[name]) if name in candidates else [("", "", "", "")]
        for export in exports:
            writer.writerow((name, binding, kind, *export))
    return 0


if __name__ == "__main__":
    sys.exit(main())
