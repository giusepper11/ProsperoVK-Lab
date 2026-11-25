#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail
export LC_ALL=C

if [[ $# -ne 5 ]]; then
    printf 'Usage: %s NEW_BUILD_DIR CTS_PS5_BUILD SDK_DIR RADV_DIR STANDALONE_LINK_EVIDENCE\n' "${0##*/}" >&2
    exit 2
fi

fixture=$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
build=$(realpath -e -- "$2")
sdk=$(realpath -e -- "$3")
radv=$(realpath -e -- "$4")
reference=$(realpath -e -- "$5")
(cd "$reference" && sha256sum --quiet --strict -c SHA256SUMS)

# RADV supplies zlib; the standalone CTS zlib archive is intentionally absent.
mapfile -t core < "$fixture/focused-archives.txt"
entry=external/vulkancts/modules/vulkan/CMakeFiles/deqp-vk.dir/__/__/__/__/framework/platform/tcuMain.cpp.o
mkdir -- "$1"
cd -- "$1"
pending=()
for item in "$entry" "${core[@]}"; do
    if [[ ! -s "$build/$item" ]]; then
        pending+=("$item")
    fi
done
if ((${#pending[@]})); then
    ninja -C "$build" -j4 "${pending[@]}" > dependency-build.log 2>&1 || { tail -60 dependency-build.log >&2; exit 1; }
fi
for index in "${!core[@]}"; do
    core[index]="$build/${core[index]}"
done
entry="$build/$entry"
python3 -B "$fixture/compile-focused.py" "$build" "$PWD" > focused-objects.txt
mapfile -t objects < focused-objects.txt

upstream="$PWD/upstream"
cp -a -- "$reference/upstream" "$upstream"
export PS5_CLANG
PS5_CLANG=$(command -v clang)
# shellcheck source=/dev/null
source "$upstream/tools/radv-link.sh"
archive="$radv/lib/libvulkan_radeon.ps5.a"
radv_link_recipe "$upstream" "$sdk" "$archive"

elf=deqp-vk-ps5-link-only.elf
stubs=("$reference"/{libSceAgc.so,libSceAgcDriver.so} "$sdk"/target/lib/*.so)
crt=("$reference"/{app_crt.o,app_cpp_runtime.o})
command=(
    "$sdk/bin/prospero-lld" "${radv_linker_script[@]}"
    --no-undefined --gc-sections --eh-frame-hdr "${radv_link_flags[@]}"
    --version-script "$upstream/tooling/native/app-symbols.map" --exclude-libs=ALL
    --Map=elf-link.map -e _start -o "$elf"
    "${crt[@]}" "$entry" "${objects[@]}" "${stubs[@]:0:2}"
    --start-group "${core[@]}" --end-group
    "${radv_link_inputs[@]}" --as-needed "${stubs[@]:2}"
)
printf '%q ' "${command[@]}" > link-command.txt
printf '\n' >> link-command.txt
"${command[@]}" > link.log 2>&1 || { tail -60 link.log >&2; exit 1; }
chmod a-x "$elf"
readelf -h "$elf" > elf-header.txt
readelf -d "$elf" > elf-dynamic.txt
llvm-nm --defined-only --demangle "$elf" > defined.txt
rg --quiet '^ +Type: +DYN ' elf-header.txt
rg --quiet ' [Tt] main$' defined.txt
rg --quiet ' [Tt] vk_icdGetInstanceProcAddr$' defined.txt
rg --quiet 'BufferToBufferInvertTestInstance::iterate' defined.txt
python3 -B "$fixture/../m0-radv-compute/check-link-imports.py" "$elf" "${stubs[@]}" > import-stub-candidates.tsv
sha256sum "$fixture"/{link-focused-ps5.sh,compile-focused.py,focused-package.cpp,focused-archives.txt} "$reference/SHA256SUMS" \
    "$build/compile_commands.json" "$archive" "$entry" "${crt[@]}" "${stubs[@]}" "${core[@]}" "${objects[@]}" \
    "$elf" elf-header.txt elf-dynamic.txt import-stub-candidates.tsv elf-link.map link-command.txt \
    focused-compile-commands.txt focused-objects.txt > SHA256SUMS
sha256sum --quiet --strict -c SHA256SUMS
sha256sum "$elf"
