#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail
export LC_ALL=C

if [[ $# -ne 5 ]]; then
    printf 'Usage: %s NEW_BUILD_DIR SDK_DIR RADV_DIR CROSS_BUILD_DIR UPSTREAM_SOURCE_DIR\n' "${0##*/}" >&2
    exit 2
fi

fixture=$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sdk=$(realpath -e -- "$2")
radv=$(realpath -e -- "$3")
cross=$(realpath -e -- "$4")
source_dir=$(realpath -e -- "$5")
archive="$radv/lib/libvulkan_radeon.ps5.a"
sdk_lib="$sdk/target/lib"
builtins="$(clang --print-resource-dir)/lib/linux/libclang_rt.builtins-x86_64.a"
verify_cross_inputs() (
    cd "$cross"
    sha256sum --quiet --strict -c SHA256SUMS
    for input in main.o compute.o "$archive" \
        "$sdk_lib"/{libc++.a,libc++abi.a,libunwind.a,libps5platform.a} "$builtins"; do
        checksum=$(sha256sum -- "$input")
        if ! rg --fixed-strings --line-regexp --quiet -- "$checksum" SHA256SUMS; then
            printf 'Link input was not verified in the cross build: %s\n' "$input" >&2
            exit 2
        fi
    done
)
verify_cross_inputs

mkdir -- "$1"
cd -- "$1"
upstream="$PWD/upstream"
while read -r expected path; do
    mkdir -p "$upstream/$(dirname "$path")"
    cp -- "$source_dir/$path" "$upstream/$path"
    if [[ $(git hash-object -- "$upstream/$path") != "$expected" ]]; then
        printf 'Upstream source hash mismatch: %s\n' "$path" >&2
        exit 2
    fi
done < "$fixture/elf-link-inputs.txt"

export PS5_PAYLOAD_SDK="$sdk"
export PS5_CLANG
PS5_CLANG=$(command -v clang)
sha256sum "$cross/SHA256SUMS" "$sdk/bin/prospero-lld" "$sdk_lib"/*.so > link-input-sha256.txt
{
    clang --version
    "$sdk/bin/prospero-lld" --version
} > toolchain.txt
native="$upstream/tooling/native"
for unit in app_crt app_cpp_runtime; do
    sh "$upstream/tooling/prospero-clang18" -std=c++20 -O2 -Wall -Wextra -fno-exceptions \
        -fno-rtti -ffunction-sections -fdata-sections -c "$native/$unit.cpp" -o "$unit.o"
done

# These shared stubs declare imports at link time. Use the actual platform
# libraries when assessing runtime availability.
link_stub() {
    local library=$1 source_file=$2
    sh "$upstream/tooling/prospero-clang18" -std=c11 -O2 -fPIC \
        -c "$upstream/vendor/ps5/sdk/stubs/$source_file" -o "${library}_stub.o"
    "$sdk/bin/prospero-lld" --shared -soname "${library}.prx" \
        -o "$library.so" "${library}_stub.o"
}
link_stub libSceAgc agc_canary_link_stub.c
link_stub libSceAgcDriver agc_driver_canary_link_stub.c

# shellcheck source=/dev/null
source "$upstream/tools/radv-link.sh"
radv_link_recipe "$upstream" "$sdk" "$archive"
elf=m0-radv-compute-link-only.elf
"$sdk/bin/prospero-lld" "${radv_linker_script[@]}" --no-undefined --eh-frame-hdr "${radv_link_flags[@]}" \
    --version-script "$native/app-symbols.map" --exclude-libs=ALL \
    --Map=elf-link.map --print-archive-stats=elf-archive-members.tsv \
    -e _start -o "$elf" app_crt.o app_cpp_runtime.o "$cross/main.o" "$cross/compute.o" \
    libSceAgc.so libSceAgcDriver.so "${radv_link_inputs[@]}" \
    --as-needed "$sdk_lib"/*.so > link.log 2>&1 || { cat link.log >&2; exit 1; }
chmod a-x "$elf"

readelf -h "$elf" > elf-header.txt
readelf -d "$elf" > elf-dynamic.txt
llvm-nm --defined-only --format=posix "$elf" > defined.txt
llvm-nm --dynamic --undefined-only --format=posix "$elf" > runtime-imports.txt
python3 -B "$fixture/check-link-imports.py" "$elf" libSceAgc.so libSceAgcDriver.so "$sdk_lib"/*.so \
    > import-stub-candidates.tsv
rg --fixed-strings --quiet -- "${archive##*/}(" elf-link.map
rg --quiet $'^members\textracted\tarchive$' elf-archive-members.tsv
rg '^ +Type: +DYN \(Position-Independent Executable file\)' elf-header.txt
rg -q '^ +Machine: +Advanced Micro Devices X86-64' elf-header.txt
for symbol in _start main vk_icdGetInstanceProcAddr radv_CreateComputePipelines \
    radv_CreateDescriptorPool vk_common_CmdDispatch; do
    rg -q "^${symbol} [Tt]( |$)" defined.txt
done
for library in libSceAgc.prx libSceAgcDriver.prx; do
    rg --fixed-strings --quiet "Shared library: [$library]" elf-dynamic.txt
done
for symbol in sceAgcInit sceAgcSuspendPoint sceAgcDriverSubmitDcb sceAgcDriverSetTFRing sceAgcDriverSetHsOffchipParam; do
    rg -q "^${symbol} U( |$)" runtime-imports.txt
done

verify_cross_inputs
sha256sum --quiet --strict -c link-input-sha256.txt
{
    sha256sum "$fixture"/{elf-link-check.sh,elf-link-inputs.txt,check-link-imports.py}
    cat link-input-sha256.txt
    while read -r _ path; do sha256sum "upstream/$path"; done < "$fixture/elf-link-inputs.txt"
    sha256sum "$elf" {app_crt,app_cpp_runtime,libSceAgc_stub,libSceAgcDriver_stub}.o \
        {libSceAgc,libSceAgcDriver}.so elf-header.txt elf-dynamic.txt defined.txt runtime-imports.txt \
        elf-link.map elf-archive-members.tsv import-stub-candidates.tsv link.log toolchain.txt
} > SHA256SUMS
sha256sum "$elf"
printf 'Build-host ELF link evidence: %s\n' "$PWD"
