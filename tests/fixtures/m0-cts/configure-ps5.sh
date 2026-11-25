#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail
export LC_ALL=C

build=$1 cts=$2 sdk=$3 radv=$4
fixture=$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$build"
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
