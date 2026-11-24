#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail
export LC_ALL=C

if [[ $# -ne 3 ]]; then
    printf 'Usage: %s NEW_BUILD_DIR SDK_DIR RADV_DIR\n' "${0##*/}" >&2
    exit 2
fi

fixture_dir=$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
sdk_dir=$(realpath -e -- "$2")
radv_dir=$(realpath -e -- "$3")
archive="$radv_dir/lib/libvulkan_radeon.ps5.a"
sdk_lib="$sdk_dir/target/lib"
builtins="$(clang --print-resource-dir)/lib/linux/libclang_rt.builtins-x86_64.a"
for input in "$archive" "$sdk_lib/libc++.a" "$sdk_lib/libc++abi.a" \
    "$sdk_lib/libunwind.a" "$sdk_lib/libps5platform.a" "$builtins"; do
    if [[ ! -r "$input" ]]; then
        printf 'Missing link input: %s\n' "$input" >&2
        exit 2
    fi
done

if ! mkdir -- "$1"; then
    printf 'Choose a fresh directory under the local build tree.\n' >&2
    exit 2
fi
cd -- "$1"

sha256sum "$fixture_dir"/{compute.comp,compute.cpp,compute.hpp,main.cpp,CMakeLists.txt,cross-check.sh} \
    "$archive" "$sdk_lib"/{libc++.a,libc++abi.a,libunwind.a,libps5platform.a} "$builtins" \
    > input-sha256.txt

cmake "-DSMOKE_SHADER_SOURCE=$fixture_dir/compute.comp" \
    "-DSMOKE_SHADER_BINARY=$PWD/compute.spv" "-DSMOKE_SHADER_HEADER=$PWD/compute_spv.hpp" \
    "-DSMOKE_GLSLANG=$(command -v glslangValidator)" "-DSMOKE_SPIRV_VAL=$(command -v spirv-val)" \
    -P "$fixture_dir/CMakeLists.txt"

for source in compute main; do
    "$sdk_dir/bin/prospero-clang++" -std=c++20 -DM0_RADV_COMPUTE_PS5 \
        -I"$radv_dir/include" -I"$PWD" -c "$fixture_dir/$source.cpp" -o "$source.o"
done

ld.lld -r -o m0-radv-compute-ps5.o --print-archive-stats=archive-members.tsv \
    --wrap=malloc --wrap=calloc --wrap=realloc --wrap=free \
    main.o compute.o --whole-archive "$archive" --no-whole-archive \
    --start-group "$sdk_lib/libc++.a" "$sdk_lib/libc++abi.a" "$sdk_lib/libunwind.a" \
    "$builtins" "$sdk_lib/libps5platform.a" --end-group

readelf -h m0-radv-compute-ps5.o > elf-header.txt
rg '^ +Type: +REL ' elf-header.txt
rg '^ +Machine: +Advanced Micro Devices X86-64' elf-header.txt
llvm-nm --extern-only --defined-only --format=posix m0-radv-compute-ps5.o > defined.txt
llvm-nm --undefined-only --format=posix m0-radv-compute-ps5.o > imports.txt
for symbol in main vk_icdGetInstanceProcAddr radv_CreateDescriptorPool \
    __wrap_malloc __wrap_calloc __wrap_realloc __wrap_free; do
    rg --quiet "^${symbol} T( |$)" defined.txt
done
awk '$2 == "U" {count++} END {print "Strong undefined symbols:", count+0}' imports.txt

{
    cmake --version
    glslangValidator --version
    spirv-val --version
    "$sdk_dir/bin/prospero-clang++" --version
    ld.lld --version
} > toolchain.txt

sha256sum --quiet -c input-sha256.txt
cat input-sha256.txt > SHA256SUMS
sha256sum compute.spv compute_spv.hpp compute.o main.o m0-radv-compute-ps5.o \
    elf-header.txt archive-members.tsv imports.txt defined.txt toolchain.txt >> SHA256SUMS
printf 'Relocatable link evidence: %s\n' "$PWD"
