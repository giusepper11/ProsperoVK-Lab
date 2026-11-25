#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail
export LC_ALL=C

if [[ $# -ne 4 ]]; then
    printf 'Usage: %s NEW_BUILD_DIR CTS_SOURCE SDK_DIR RADV_DIR\n' "${0##*/}" >&2
    exit 2
fi

fixture=$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cts=$(realpath -e -- "$2")
sdk=$(realpath -e -- "$3")
radv=$(realpath -e -- "$4")
archive="$radv/lib/libvulkan_radeon.ps5.a"
sdk_lib="$sdk/target/lib"
builtins="$(clang --print-resource-dir)/lib/linux/libclang_rt.builtins-x86_64.a"
revision=f6a29701220f34dd1407513bfe80d74ca7b392ce
if [[ $(git -C "$cts" rev-parse HEAD) != "$revision" ]] || ! git -C "$cts" diff --quiet HEAD; then
    printf 'Expected the clean, pinned Khronos CTS checkout at %s\n' "$revision" >&2
    exit 2
fi

mkdir -- "$1"
cd -- "$1"
cmake -S "$cts" -B . -G Ninja -DDEQP_TARGET=vulkan_headless \
    -DCMAKE_SYSTEM_NAME=FreeBSD -DCMAKE_SYSTEM_PROCESSOR=x86_64 \
    "-DCMAKE_C_COMPILER=$sdk/bin/prospero-clang" "-DCMAKE_CXX_COMPILER=$sdk/bin/prospero-clang++" \
    "-DCMAKE_AR=$sdk/bin/prospero-ar" "-DCMAKE_RANLIB=$sdk/bin/prospero-ranlib" \
    -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
    "-DCMAKE_FIND_ROOT_PATH=$sdk/target" -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY \
    -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER \
    -DCMAKE_DISABLE_FIND_PACKAGE_ZLIB=ON -DCMAKE_DISABLE_FIND_PACKAGE_PNG=ON \
    -DDEQP_DISABLE_VK_VIDEO_TESTS=ON -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    '-DCMAKE_C_FLAGS=-include malloc_np.h' \
    "-DCMAKE_CXX_FLAGS=-DM0_CTS_USE_RADV -I$radv/include -include cstdint -include cstddef -include cstring" \
    '-DCMAKE_C_FLAGS_RELEASE=-O0 -g0 -DNDEBUG' '-DCMAKE_CXX_FLAGS_RELEASE=-O0 -g0 -DNDEBUG' \
    "-DTCUTIL_PLATFORM_SRCS=$fixture/headless-platform.cpp;$fixture/headless-resolver.cpp" \
    > configure.log 2>&1 || { tail -60 configure.log >&2; exit 1; }

compute=external/vulkancts/modules/vulkan/compute/CMakeFiles/deqp-vk-compute.dir/vktComputeBasicComputeShaderTests.cpp.o
ninja -t targets all | awk '
    /framework\/platform\/CMakeFiles\/tcutil-platform.dir.*headless-(platform|resolver).cpp.o:/ ||
    /deqp-vk.dir.*tcuMain.cpp.o:/ { sub(/:$/, "", $1); print $1 }
' > selected-objects.txt
printf '%s\n' "$compute" >> selected-objects.txt
mapfile -t objects < selected-objects.txt
if [[ ${#objects[@]} -ne 4 ]]; then
    printf 'Expected two adapter objects, the upstream entry point and the selected case source object\n' >&2
    exit 2
fi
ninja -j3 "${objects[@]}" > compile-objects.log 2>&1 || { tail -60 compile-objects.log >&2; exit 1; }

for object in "${objects[@]}"; do
    readelf -h "$object" > "${object##*/}.elf-header.txt"
    rg --quiet '^ +Type: +REL ' "${object##*/}.elf-header.txt"
    rg --quiet '^ +Machine: +Advanced Micro Devices X86-64' "${object##*/}.elf-header.txt"
    ninja -t commands -s "$object"
    if [[ ${object##*/} == headless-resolver.cpp.o ]]; then
        llvm-nm --undefined-only "$object" > resolver-imports.txt
    fi
done > compile-commands.txt
llvm-nm --defined-only --demangle "$compute" > compute-defined.txt
rg --quiet 'createBasicComputeShaderTests\(' compute-defined.txt
strings "$compute" > compute-strings.txt
rg --line-regexp --quiet 'copy_ssbo_single_invocation' compute-strings.txt
rg --quiet ' U vk_icdGetInstanceProcAddr$' resolver-imports.txt

# Assemble the target objects and driver as an ordinary relocatable ELF.
linked=m0-cts-ps5-relocatable.o
ld.lld -r -o "$linked" --wrap=malloc --wrap=calloc --wrap=realloc --wrap=free \
    "${objects[@]}" --whole-archive "$archive" --no-whole-archive \
    --start-group "$sdk_lib"/{libc++.a,libc++abi.a,libunwind.a,libps5platform.a} \
    "$builtins" --end-group
readelf -h "$linked" > "$linked.elf-header.txt"
rg --quiet '^ +Type: +REL ' "$linked.elf-header.txt"
llvm-nm --extern-only --defined-only --format=posix "$linked" > linked-defined.txt
llvm-nm --undefined-only --format=posix "$linked" > linked-imports.txt
for symbol in main vk_icdGetInstanceProcAddr vk_common_GetDeviceProcAddr __wrap_malloc; do
    rg --quiet "^${symbol} [TW]( |$)" linked-defined.txt
done

{
    printf 'CTS revision: %s\n' "$revision"
    "$sdk/bin/prospero-clang++" --version
    ld.lld --version
    cat "$sdk/.ps5-sdk-revision" "$radv/PROVENANCE.txt"
} > provenance.txt
sha256sum "$fixture"/{build-ps5-objects.sh,headless-platform.cpp,headless-resolver.cpp} \
    "$cts/framework/platform/tcuMain.cpp" \
    "$cts/external/vulkancts/modules/vulkan/compute/vktComputeBasicComputeShaderTests.cpp" \
    "$archive" "$sdk_lib"/{libc++.a,libc++abi.a,libunwind.a,libps5platform.a} "$builtins" \
    "${objects[@]}" "$linked" selected-objects.txt compile-commands.txt \
    configure.log compile-objects.log *.elf-header.txt compute-defined.txt compute-strings.txt \
    resolver-imports.txt linked-defined.txt linked-imports.txt provenance.txt > SHA256SUMS
sha256sum --quiet --strict -c SHA256SUMS
printf 'CTS PS5-target object evidence: %s\n' "$PWD"
