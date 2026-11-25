# M0 toolchain evidence

Run date 2026-11-24 on Ubuntu 26.04.1 LTS x86-64, lab base `abee1ca738e3ddfd0ee9bf385e875f707baafe76` with the M0 fixture in the working tree. Reproduction commands run from the repository root unless noted.

| Check | Environment | Result |
| --- | --- | --- |
| Linux C++20, CMake and Ninja | GCC 15.2.0 (Ubuntu 15.2.0-16ubuntu1), CMake 4.2.3, Ninja 1.13.2 | `PASS`. Release configure, compile and link against the system Vulkan loader. CMake 3.24 is the fixture minimum. |
| Linux software Vulkan | Loader 1.4.341, Mesa llvmpipe 26.0.8 (LLVM 21.1.8), device API 1.4.335, conformanceVersion 1.3.1.1 | `PASS`. Instance and device creation, queue 0, one empty submit and fence completion. Missing ICD returned `VK_ERROR_INCOMPATIBLE_DRIVER` (-9). |
| Shader toolchain | glslang 16.2.0, SPIRV-Tools v2026.1, target environment Vulkan 1.0 | `PASS`. Compiled and validated the fixture's minimal compute shader. |
| Linux upstream CTS smoke | Unmodified VK-GL-CTS `f6a29701220f34dd1407513bfe80d74ca7b392ce`, llvmpipe 26.0.8 | `PASS`. The selected storage-buffer compute case returned `Pass (Compute succeeded)` and a complete QPA session. |
| Linux hardware Vulkan | No `/dev/dri` exposed to the runner | `NOT_RUN`. |
| PS5-target compilation | Ubuntu Clang 18.1.8 (20ubuntu8), public SDK v0.42 headers and libc++, Vulkan headers 1.4.341 | `PASS` on the Linux build host. The same fixture source compiled to an ELF64 little-endian x86-64 relocatable with the expected unresolved Vulkan references. |
| PS5 SDK platform build and host checks | SDK v0.42 plus fork `b83202be73e930050e00de0f1b4d9ec46c0391bf`, Clang/LLVM 21.1.8 | Platform archive and host zlib built successfully. The upstream host suite passed 191/193, with two failures in its fixed `/tmp` file test. The directory-record test passed independently. The same file probe passed all six readback checks when given a workspace directory. |
| PS5 RADV release archive | Driver build scripts `7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc`, Mesa `1ba9874f478657ccf6da72ce55f0260164cc0bd0`, SDK fork as above | `PASS` on the build host. Built both host shader tools and the cross-target static archive with assertions disabled. Verified the digest and the static entry points. The C++ fixture also compiled against the archive's Vulkan headers using the SDK wrapper. |
| PS5-target RADV relocatable link | Same SDK and RADV archives, Ubuntu LLD 21.1.8 and compiler builtins | `PASS` on the build host. The ICD getter and four SDK allocation wrappers resolved. The whole-archive link retained the definition of `radv_CreateDescriptorPool`, which was weak and undefined after selective archive extraction. |
| PS5-target standalone compute ELF link | Same SDK, RADV archive and LLD, with public PS5_Vulkan startup and AGC link stubs at the pinned revision | `PASS` on the build host. Two links produced byte-identical x86-64 PIE ELFs with seven declared shared libraries and 284 strong dynamic imports. [Standalone link evidence](#link-the-build-host-elf). |
| PS5 CTS title build preflight | Khronos CTS `f6a29701220f34dd1407513bfe80d74ca7b392ce` and the staged SDK above | CMake exited 1 because the checkout lacks `targets/ps5/ps5.cmake`. The staged SDK libraries supplied none of the five AGC imports left by the RADV relocatable link. [Build preflight](#ps5-cts-build-preflight). |
| PS5 title and console runtime | Management connection verified. The operator confirmed a PS5 Slim and Prospero Manager reported firmware 13.60. The CTS title was absent from the registered title list. | Final title build and Vulkan smoke `NOT_RUN`. [Console preflight](HARDWARE_VALIDATION.md#m0-console-preflight). |
| OpenSpec | OpenSpec 1.14.0, Node v26.8.2, npm 11.19.1 | Initialized repo-local `spec-driven` configuration and created the M0 and M1 changes. [Workflow](../openspec/README.md). |

## Reproduce the Linux checks

Use the distribution packages and an installed llvmpipe ICD. In this run the loader and ICD were already installed. The compiler and build tools were obtained in a temporary directory with `apt-get download` and `dpkg-deb -x`. No system packages were installed. This reproduces that isolated setup on the same distribution with the named package versions available.

```bash
set -eu
probe_tmp=$(mktemp -d)
mkdir -p "$probe_tmp/debs" "$probe_tmp/toolroot"
(
  cd "$probe_tmp/debs"
  apt-get download \
    cmake=4.2.3-2ubuntu2 cmake-data=4.2.3-2ubuntu2 ninja-build=1.13.2-1 \
    libvulkan-dev=1.4.341.0-1 vulkan-tools=1.4.341.0+dfsg1-1 \
    glslang-tools=16.2.0-2 spirv-tools=2026.1-1 \
    libarchive13t64=3.8.5-1ubuntu2.3 librhash1=1.4.6-1.1 libjsoncpp26=1.9.6-5
  for deb in ./*.deb; do dpkg-deb -x "$deb" ../toolroot; done
)
probe_tools="$probe_tmp/toolroot/usr"
export PATH="$probe_tools/bin:$PATH"
export LD_LIBRARY_PATH="$probe_tools/lib/x86_64-linux-gnu"
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json
export MESA_SHADER_CACHE_DISABLE=true

vulkaninfo --summary
cmake -S tests/fixtures/m0-linux-probe -B "$probe_tmp/probe-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DVulkan_INCLUDE_DIR="$probe_tools/include" \
  -DVulkan_LIBRARY=/usr/lib/x86_64-linux-gnu/libvulkan.so.1
cmake --build "$probe_tmp/probe-build"
ctest --test-dir "$probe_tmp/probe-build" -V
if VK_DRIVER_FILES="$probe_tmp/missing.json" "$probe_tmp/probe-build/m0_linux_probe" \
    > "$probe_tmp/no-icd.log" 2>&1; then
  exit 1
fi
rg -F 'vkCreateInstance returned -9' "$probe_tmp/no-icd.log"
sha256sum "$probe_tmp/probe-build/probe.spv"
```

CTest reported 2/2 passed. The driver line was `device=llvmpipe (LLVM 21.1.8, 256 bits) api=1.4.335 type=4 queue=0 empty_submit=PASS`. The shader SHA-256 was `2e20fe5e958e75291419592c6b391fd15efa4a7e22a601b8cd50f6ea144588bf`. The fixture allocates no workload buffers and submits no command buffers. It uses a five-second fence wait and a 15-second CTest process limit. A failed wait exits the probe without calling into a device that may still have work in flight.

## Reproduce the single CTS smoke on Linux

Use the Linux compiler and tools above. The runbook's single compute case is in the pinned CTS release's default compute list. The Linux reproduction uses upstream CMake's `vulkan_headless` target, system zlib 1.3.1 and the upstream libpng fallback. The build reused the local tools environment from the RADV archive check. It uses GCC 15.2.0, the upstream dependency pins, no compiler optimization, and the video tests disabled by CMake. Keep the fresh run directory and raw QPA under the ignored build tree. [Pinned case list][cts-compute-list], [pinned dependencies][cts-deps].

```bash
set -eu
mkdir -p build
cts_root=$(mktemp -d "$PWD/build/m0-cts.XXXXXX")
mkdir -p "$cts_root/tmp"
export TMPDIR="$cts_root/tmp"
git init -q "$cts_root/source"
git -C "$cts_root/source" fetch --no-tags --depth=1 https://github.com/KhronosGroup/VK-GL-CTS.git \
  f6a29701220f34dd1407513bfe80d74ca7b392ce
git -C "$cts_root/source" switch --detach FETCH_HEAD
test "$(git -C "$cts_root/source" rev-parse HEAD)" = f6a29701220f34dd1407513bfe80d74ca7b392ce
GIT_TERMINAL_PROMPT=0 python3 -u "$cts_root/source/external/fetch_sources.py" > "$cts_root/fetch.log" 2>&1
for dep in amber glslang jsoncpp spirv-headers spirv-tools video_generator vulkan-docs vulkan-video-samples; do
  revision=$(git -C "$cts_root/source/external/$dep/src" rev-parse HEAD)
  printf '%s\t%s\n' "$dep" "$revision"
done > "$cts_root/externals.tsv"
cmake -S "$cts_root/source" -B "$cts_root/compiled" -G Ninja \
  -DDEQP_TARGET=vulkan_headless -DDEQP_DISABLE_VK_VIDEO_TESTS=ON \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  '-DCMAKE_C_FLAGS_RELEASE=-O0 -g0 -DNDEBUG' '-DCMAKE_CXX_FLAGS_RELEASE=-O0 -g0 -DNDEBUG' \
  '-DCMAKE_CXX_FLAGS=-include cstdint -include cstddef -include cstring' \
  > "$cts_root/configure.log" 2>&1
cmake --build "$cts_root/compiled" --target deqp-vk --parallel 6 > "$cts_root/build.log" 2>&1
```

Run the same case selected for console validation. The host uses its local data archive directory and QPA destination.

```bash
lab_root="$PWD"
cts_source="$cts_root/source"
cts_module="$cts_root/compiled/external/vulkancts/modules/vulkan"
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json
export VK_LOADER_LAYERS_DISABLE='~all~'
export MESA_SHADER_CACHE_DISABLE=true
case_id=dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation
rg --quiet --fixed-strings --line-regexp "$case_id" \
  "$cts_source/external/vulkancts/mustpass/main/vk-default/compute.txt"
run_dir=$(mktemp -d "$cts_root/run-lvp.XXXXXX")
cd "$run_dir"
if timeout --foreground 60s "$cts_module/deqp-vk" --deqp-case="$case_id" \
    --deqp-log-filename="$run_dir/TestResults.qpa" --deqp-archive-dir="$cts_module" \
    --deqp-log-flush=disable --deqp-log-images=disable > stdout.log 2>&1; then
  printf '0\n' > exit-code.txt
else
  result=$?
  printf '%s\n' "$result" > exit-code.txt
  cat stdout.log
  exit "$result"
fi
python3 -B "$lab_root/tools/verify-m0-cts-qpa.py" "$cts_source" TestResults.qpa > qpa-result.json
sha256sum TestResults.qpa stdout.log qpa-result.json exit-code.txt > SHA256SUMS
sha256sum --strict -c SHA256SUMS
python3 -B "$lab_root/tests/fixtures/m0-cts/check-qpa-verifier.py" "$cts_source" TestResults.qpa
```

The Linux process exited 0. CTS counted 1 pass, 0 failures, 0 unsupported cases, 0 warnings and 0 waivers. The verifier reported a completed case with `Pass` and `Compute succeeded` from the pinned CTS parser. The repeat run's QPA SHA-256 was `81a482fac25dd1f45031832aa448b8ae9671661bc2fc47b9bf5aee0bfaebb6b8`. The original QPA SHA-256 was `6b7afbf68b28b8ece3dddc6572a4c8a3afd847a3d4a21f57056bc6a5e41c23b1`.

The upstream CSV parser can emit a Pass row for an incomplete session or a case terminated with `Pass`. The lab verifier checks the ordered session and case boundaries, matches the XML case path to the selected test, and requires one direct XML result. The verifier checks the original XML bytes before accepting the upstream result. The regression checks exercised missing, premature and duplicate markers, trailing data, mismatched XML identity, invalid XML status bytes, a completed failure and terminated cases. [Pinned QPA parser][cts-qpa-parser], [pinned QPA writer][cts-qpa-writer].

The external Git checkouts matched the declared commit pins. Vulkan-Video-Samples tag `v0.3.9` resolved to `aaf915a0e08d679d1e8b835c30e6a346ab0c7ad2`. The local external revision manifest SHA-256 was `8f4453c774c714978f078ab5ba95c5588f174f2b1bc84ad7dadb19aec468b9b8`. This was a single software Vulkan run for M0. The PS5 counterpart remains `NOT_RUN`.

[cts-compute-list]: https://github.com/KhronosGroup/VK-GL-CTS/blob/f6a29701220f34dd1407513bfe80d74ca7b392ce/external/vulkancts/mustpass/main/vk-default/compute.txt
[cts-deps]: https://github.com/KhronosGroup/VK-GL-CTS/blob/f6a29701220f34dd1407513bfe80d74ca7b392ce/external/fetch_sources.py
[cts-qpa-parser]: https://github.com/KhronosGroup/VK-GL-CTS/blob/f6a29701220f34dd1407513bfe80d74ca7b392ce/scripts/log/log_parser.py
[cts-qpa-writer]: https://github.com/KhronosGroup/VK-GL-CTS/blob/f6a29701220f34dd1407513bfe80d74ca7b392ce/framework/qphelper/qpTestLog.c

## Reproduce the PS5 compile-only check

Keep the variables and library search path from the Linux check. Clang is a host compiler targeting `x86_64-sie-ps5`. The public release's digest matches the [pinned upstream SDK setup][sdk-setup]. The libc++ include directory must precede the C sysroot headers. The fixture uses C++ exceptions, so the compile enables exceptions and RTTI explicitly, as the SDK C++ wrapper does.

```bash
(
  cd "$probe_tmp/debs"
  apt-get download clang-18=1:18.1.8-20ubuntu8 libllvm18=1:18.1.8-20ubuntu8 \
    libclang-cpp18=1:18.1.8-20ubuntu8 libclang-common-18-dev=1:18.1.8-20ubuntu8
  for deb in ./clang-18*.deb ./libllvm18*.deb ./libclang-cpp18*.deb ./libclang-common-18-dev*.deb; do
    dpkg-deb -x "$deb" ../toolroot
  done
)
curl -fLsS https://github.com/ps5-payload-dev/sdk/releases/download/v0.42/ps5-payload-sdk.zip \
  -o "$probe_tmp/sdk-v0.42.zip"
printf '%s  %s\n' 8cfbc7cd5811e719eb4f0c47eea668d3dc7b40bc8ab11c4a5031d40c23ec02da \
  "$probe_tmp/sdk-v0.42.zip" | sha256sum -c
python3 - "$probe_tmp" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile

root = Path(sys.argv[1])
with ZipFile(root / "sdk-v0.42.zip") as sdk:
    headers = [path for path in sdk.namelist() if path.startswith("ps5-payload-sdk/target/include/")]
    sdk.extractall(root / "sdk-release", headers)
PY
probe_sdk="$probe_tmp/sdk-release/ps5-payload-sdk"
"$probe_tools/bin/clang++-18" --target=x86_64-sie-ps5 -std=c++20 \
  -isysroot "$probe_sdk" -nostdinc++ -isystem "$probe_sdk/target/include/c++/v1" \
  -isystem "$probe_sdk/target/include" -I "$probe_tools/include" -fdenormal-fp-math=ieee \
  -fexceptions -frtti -c tests/fixtures/m0-linux-probe/main.cpp -o "$probe_tmp/prospero-probe.o"
readelf -h "$probe_tmp/prospero-probe.o"
readelf -Ws "$probe_tmp/prospero-probe.o" | rg 'UND.*vk(CreateInstance|CreateDevice|QueueSubmit|WaitForFences)$'
```

This first object uses the Linux development package's Vulkan headers. The archive build below repeats the compile with RADV's exported headers. The final PS5 link should resolve Vulkan symbols through the adapter. The ELF header alone cannot identify the exact console firmware ABI.

## Build strategy

Keep shared C++20 code and Vulkan requirements in one source tree. Use CMake with `Vulkan::Vulkan` and an explicitly selected loader/ICD for Linux. For PS5, the upstream [Meson cross-file][cross-file] targets x86-64 FreeBSD via the public SDK wrappers. The [RADV builder][radv-builder] builds host `mesa_clc` and `vtn_bindgen2` with LLVM, Clang, libclc and an LLVM/SPIR-V translator, then uses ACO for the target archive. `PS5_VulkanTemplate` demonstrates CMake compilation of C++20 title objects. Its [link script][template-link] uses the RADV archive and the SDK platform and C++ libraries, checks imports, and stages the title with notices. Treat the title flow and static function resolution as PS5 adapter work.

## Reproduce the SDK and release archive build

On this host the archive dependencies were extracted under the ignored workspace build directory. Preserve `probe_tmp` and `probe_tools` from the Linux check. The build used Mesa's host LLVM, Clang and lld 21.1.8, Meson 1.10.1, Ninja 1.13.2, libclc 21 and SPIRV-Tools 2026.1. Reproduce with these Ubuntu packages and the pinned sources below. The initial compiler run hit a `/tmp` quota, so the successful build steps use a workspace `TMPDIR`.

```bash
set -eu
lab_root=$PWD
mkdir -p build
build_root=$(mktemp -d "$PWD/build/m0-archive.XXXXXX")
mkdir -p "$build_root"/{packages,tools,tmp}
(
  cd "$build_root/packages"
  apt-get download meson pkgconf pkgconf-bin libpkgconf7 bison flex unzip python3-mako python3-ply \
    clang-21 lld-21 llvm-21 llvm-21-dev llvm-21-tools llvm-21-runtime libclang-cpp21 \
    libclang-cpp21-dev libclang-common-21-dev libclang-21-dev libclang1-21 libclc-21 libclc-21-dev \
    libllvmspirvlib-21-dev libllvmspirvlib21.1 libdrm-dev spirv-headers libxml2-dev libzstd-dev libffi-dev libncurses-dev
  apt-get download spirv-tools-dev=2026.1-1 spirv-tools-headers=2026.1-1
  for deb in ./*.deb; do dpkg-deb -x "$deb" ../tools; done
)
archive_tools="$build_root/tools"
export PATH="$archive_tools/usr/lib/llvm-21/bin:$archive_tools/usr/bin:$probe_tools/bin:$PATH"
export LD_LIBRARY_PATH="$archive_tools/usr/lib/x86_64-linux-gnu:$probe_tools/lib/x86_64-linux-gnu"
export LIBRARY_PATH="$archive_tools/usr/lib/x86_64-linux-gnu"
export PYTHONPATH="$archive_tools/usr/lib/python3/dist-packages"
export PKG_CONFIG_PATH="$archive_tools/usr/lib/pkgconfig:$archive_tools/usr/lib/x86_64-linux-gnu/pkgconfig:$archive_tools/usr/share/pkgconfig"
export PKG_CONFIG_SYSROOT_DIR="$archive_tools"
export CMAKE_PREFIX_PATH="$archive_tools/usr"
export BISON_PKGDATADIR="$archive_tools/usr/share/bison"
export BUILD_JOBS=4
export TMPDIR="$build_root/tmp"

cd "$build_root"
for source in PS5_Mesa:1ba9874f478657ccf6da72ce55f0260164cc0bd0 PS5_PayloadSDK:b83202be73e930050e00de0f1b4d9ec46c0391bf; do
  repo=${source%:*}
  rev=${source#*:}
  git init -q "$repo"
  git -C "$repo" fetch --no-tags --depth=1 "https://github.com/mihawk-99/$repo.git" "$rev"
  git -C "$repo" switch --detach FETCH_HEAD
  test "$(git -C "$repo" rev-parse HEAD)" = "$rev"
done
build_rev=7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc
for path in tools/setup-native-dependencies.sh tools/build-radv.sh tooling/radv/ps5-cross.ini; do
  mkdir -p "PS5_Vulkan/${path%/*}"
  curl -fsS "https://raw.githubusercontent.com/mihawk-99/PS5_Vulkan/$build_rev/$path" -o "PS5_Vulkan/$path"
done
chmod +x PS5_Vulkan/tools/{setup-native-dependencies,build-radv}.sh
```

Prefetch the SDK release from the compile-only check and both zlib inputs for a build that can run offline. The SDK script checks v0.42 and zlib 1.3.2. Mesa checks its distinct 1.3.1 fallback against the pinned `subprojects/zlib.wrap`.

```bash
cd "$build_root/PS5_Vulkan"
mkdir -p .deps/native/zlib .deps/work/radv-src/subprojects/packagecache
cp "$probe_tmp/sdk-v0.42.zip" .deps/native/ps5-payload-sdk.zip
curl -fLsS https://zlib.net/fossils/zlib-1.3.2.tar.gz -o .deps/native/zlib/zlib-1.3.2.tar.gz
(
  cd .deps/work/radv-src/subprojects/packagecache
  curl -fLsS https://zlib.net/fossils/zlib-1.3.1.tar.gz -o zlib-1.3.1.tar.gz
  curl -fLsS https://wrapdb.mesonbuild.com/v2/zlib_1.3.1-1/get_patch -o zlib_1.3.1-1_patch.zip
)
tools/setup-native-dependencies.sh
tools/build-radv.sh release
cat .deps/native/radv-release/PROVENANCE.txt
sha256sum .deps/native/radv-release/lib/libvulkan_radeon.ps5.a
llvm-nm --defined-only .deps/native/radv-release/lib/libvulkan_radeon.ps5.a | \
  rg ' T (vk_icdGetInstanceProcAddr|radv_CreateInstance|radv_CreateDevice)$'
.deps/native/ps5-payload-sdk/bin/prospero-clang++ -std=c++20 -I "$PWD/.deps/native/radv-release/include" \
  -c "$lab_root/tests/fixtures/m0-linux-probe/main.cpp" -o "$build_root/prospero-radv-probe.o"
readelf -h "$build_root/prospero-radv-probe.o"
```

The release archive contained 704 members and 273,744,158 bytes. SHA-256 for this build was `d06eaf176b42fda32b740a660f343c1e72167cb11a6f6965669ba23437bdf441`, which matched the generated provenance. `llvm-nm` found the three named definitions. The archive exported Vulkan headers with `VK_HEADER_VERSION=354`. With those headers the fixture compiled to a relocatable ELF64 x86-64 object, with the Vulkan calls still unresolved at object stage. Console executable linkage and packaging await a verified title build.

The upstream SDK host verification command was `make -C build/m0-archive/PS5_PayloadSDK/platform test` from the lab root. It stopped after the 191/193 result. Running the resulting `build/host/test_directory_records` binary directly passed. To isolate the file-test failures, a local host harness invoked the unchanged `ps5_platform_probe_files` with a fresh directory under `/tmp` and again with a fresh directory under the workspace. Its six comparisons failed in the first location and passed in the second. These are Linux filesystem checks.

Upstream exports a debug variant for diagnostics and a release variant for deployment. Record the actual variant. The proposed M0 operator smoke uses one case in an already available, authorized CTS title. Rebuilding that title additionally requires the PS5 fork and its build provenance. [Hardware runbook](HARDWARE_VALIDATION.md).

## Reproduce the PS5 relocatable link check

Use the extracted LLVM tools, `build_root` and pinned SDK and RADV archives from the release archive build. This check links a C++20 reference to the documented CTS resolver, using the upstream archive group and four allocation wraps from the [RADV title link recipe][radv-link]. It compares ordinary archive extraction with the recipe's whole-archive setting. Both outputs remain relocatable objects, with title-specific runtime imports unresolved.

```bash
set -eu
(
  cd "$build_root/packages"
  apt-get download libclang-rt-21-dev=1:21.1.8-6ubuntu1
  dpkg-deb -x ./libclang-rt-21-dev_*.deb ../tools
)
radv="$build_root/PS5_Vulkan/.deps/native/radv-release"
sdk="$build_root/PS5_Vulkan/.deps/native/ps5-payload-sdk"
archive="$radv/lib/libvulkan_radeon.ps5.a"
builtins="$(clang --print-resource-dir)/lib/linux/libclang_rt.builtins-x86_64.a"
link_probe=$(mktemp -d "$build_root/static-link.XXXXXX")
cat > "$link_probe/lookup.cpp" <<'CPP'
// SPDX-License-Identifier: GPL-3.0-or-later
#include <vulkan/vk_icd.h>

extern "C" PFN_vkVoidFunction m0_lookup_vk_create_instance() {
    return vk_icdGetInstanceProcAddr(VK_NULL_HANDLE, "vkCreateInstance");
}
CPP
"$sdk/bin/prospero-clang++" -std=c++20 -I "$radv/include" \
  -c "$link_probe/lookup.cpp" -o "$link_probe/lookup.o"
llvm-nm --undefined-only --format=posix "$link_probe/lookup.o" | rg '^vk_icdGetInstanceProcAddr U( |$)'

wraps=(--wrap=malloc --wrap=calloc --wrap=realloc --wrap=free)
support=(--start-group "$sdk/target/lib/libc++.a" "$sdk/target/lib/libc++abi.a" \
  "$sdk/target/lib/libunwind.a" "$builtins" "$sdk/target/lib/libps5platform.a" --end-group)
ld.lld -r -o "$link_probe/wrapped.o" --print-archive-stats="$link_probe/wrapped.tsv" \
  "${wraps[@]}" "$link_probe/lookup.o" --whole-archive "$archive" --no-whole-archive "${support[@]}"
ld.lld -r -o "$link_probe/selective-wrapped.o" --print-archive-stats="$link_probe/selective-wrapped.tsv" \
  "${wraps[@]}" "$link_probe/lookup.o" "$archive" "${support[@]}"

for variant in wrapped selective-wrapped; do
  readelf -h "$link_probe/$variant.o" | rg 'Class:|Type:|Machine:'
  llvm-nm --defined-only --format=posix "$link_probe/$variant.o" > "$link_probe/$variant-defined.txt"
  llvm-nm --undefined-only --format=posix "$link_probe/$variant.o" > "$link_probe/$variant-undefined.txt"
  awk '$1 ~ /^radv_/ && $2 == "T" {print $1}' "$link_probe/$variant-defined.txt" | \
    LC_ALL=C sort -u > "$link_probe/$variant-radv.txt"
done
for symbol in vk_icdGetInstanceProcAddr __wrap_malloc __wrap_calloc __wrap_realloc __wrap_free radv_CreateDescriptorPool; do
  rg --quiet "^${symbol} T( |$)" "$link_probe/wrapped-defined.txt"
done
rg '^radv_CreateDescriptorPool w( |$)' "$link_probe/selective-wrapped-undefined.txt"
LC_ALL=C comm -23 "$link_probe/wrapped-radv.txt" "$link_probe/selective-wrapped-radv.txt" > "$link_probe/omitted-wrapped-radv.txt"
wc -l "$link_probe/omitted-wrapped-radv.txt"
awk '$2 == "U" {count++} END {print count}' "$link_probe/wrapped-undefined.txt"
sha256sum "$link_probe"/{lookup,wrapped,selective-wrapped}.o
```

The whole-archive object defined the ICD getter, all four allocation wrappers and `radv_CreateDescriptorPool`. LLD reported extracting four SDK platform objects. The selective variant extracted 525 of 704 RADV members and omitted 27 global RADV function definitions present in the whole-archive variant, including the descriptor pool function. The whole-archive object was ELF64 x86-64 `ET_REL` with SHA-256 `e953feb557e1c2a75abaa22eee12efef7d680a79e9c69a72469f46e792e0d102`. Its 259 strong undefined symbols remain for final title linkage to resolve. This verifies an archive selection and symbol resolution step. The final console link, packaging and execution remain open.

## PS5 CTS build preflight

From the same build environment and the unmodified CTS checkout used for Linux, the console configuration failed at `CMakeLists.txt:73` when CMake tried to include `targets/ps5/ps5.cmake`. Run from the lab root with the tool paths from the Linux and SDK builds. The configuration below uses the dependencies already present in the checkout.

```bash
cts_root=$(realpath build/m0-cts)
out=$(mktemp -d "$cts_root/configure-ps5-local.XXXXXX")
cmake -S "$cts_root/source" -B "$out" -G Ninja -DDEQP_TARGET=ps5 \
  -DDEQP_DISABLE_VK_VIDEO_TESTS=ON -DFETCHCONTENT_FULLY_DISCONNECTED=ON \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

The build also needs the target graphics imports. With `sdk` and `link_probe` from the [relocatable link check](#reproduce-the-ps5-relocatable-link-check), compare the strong undefined AGC symbols against the staged SDK library exports.

```bash
set -euo pipefail
audit=$(mktemp -d "$build_root/sdk-export-check.XXXXXX")
awk '$2 == "U" && $1 ~ /^sceAgc/ {print $1}' "$link_probe/wrapped-undefined.txt" | \
  LC_ALL=C sort -u > "$audit/required-agc.txt"
llvm-nm --dynamic --defined-only --format=posix "$sdk"/target/lib/*.so > "$audit/dynamic.txt"
llvm-nm --defined-only --format=posix "$sdk"/target/lib/*.a > "$audit/static.txt"
awk '$1 ~ /^sceAgc/ && $2 ~ /^[TW]$/ {print $1}' "$audit/dynamic.txt" "$audit/static.txt" | \
  LC_ALL=C sort -u > "$audit/exports-agc.txt"
LC_ALL=C comm -23 "$audit/required-agc.txt" "$audit/exports-agc.txt"
```

This found five missing definitions in the staged libraries. They were `sceAgcDriverSetHsOffchipParam`, `sceAgcDriverSetTFRing`, `sceAgcDriverSubmitDcb`, `sceAgcInit` and `sceAgcSuspendPoint`. The check establishes which link inputs are absent locally. Availability of those APIs through a verified title environment remains open. The [upstream audit](UPSTREAM.md#cts-execution-and-report-ingestion) records the console fork and the separately pinned focused CTS port.

### Build the local CTS headless adapter

This build uses the official Khronos CTS at `f6a29701220f34dd1407513bfe80d74ca7b392ce`. The lab supplies only the platform adapter and Vulkan resolver. The upstream runner, test registration, shader, result comparison and QPA writer stay in the build. The selected case checks 256 values. CMake's `TCUTIL_PLATFORM_SRCS` selects the lab adapter. The Linux build uses the system Vulkan loader. The PS5-target build refers to the public RADV ICD entry point. [Adapter](../tests/fixtures/m0-cts/headless-platform.cpp), [resolver](../tests/fixtures/m0-cts/headless-resolver.cpp).

From the lab root, use `cts_root`, `build_root` and `probe_tools` from the earlier setup. These identify the pinned Linux CTS build, the staged SDK and RADV release, and the host headers and tools.

```bash
set -eu
lab_root="$PWD"
cts_source=$(realpath "$cts_root/source")
cts_build=$(realpath "$cts_root/compiled")
sdk="$build_root/PS5_Vulkan/.deps/native/ps5-payload-sdk"
radv="$build_root/PS5_Vulkan/.deps/native/radv-release"
capture=$(mktemp -d "$cts_root/local-build.XXXXXX")
fixture=tests/fixtures/m0-cts
bash "$fixture/build-ps5-objects.sh" "$capture/ps5-target" "$cts_source" "$sdk" "$radv"
python3 -B "$fixture/relink-linux.py" "$cts_build" "$capture/linux" \
  "$probe_tools/include" /usr/lib/x86_64-linux-gnu/libvulkan.so.1
(
  cd "$capture/linux"
  status=0
  VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json MESA_SHADER_CACHE_DISABLE=true \
    timeout --foreground 60s ./deqp-vk-local-headless \
    --deqp-case=dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation \
    --deqp-log-filename=TestResults.qpa --deqp-archive-dir="$cts_build/external/vulkancts/modules/vulkan" \
    --deqp-log-flush=disable --deqp-log-images=disable --deqp-shadercache=disable > stdout.log 2>&1 || status=$?
  printf '%s\n' "$status" > exit-code.txt
  test "$status" -eq 0
  python3 -B "$lab_root/tools/verify-m0-cts-qpa.py" "$cts_source" TestResults.qpa > qpa-result.json
  sha256sum headless-platform.o headless-resolver.o deqp-vk-local-headless TestResults.qpa \
    stdout.log qpa-result.json exit-code.txt compile-command.txt link-command.txt > SHA256SUMS
  sha256sum --quiet --strict -c SHA256SUMS
)
```

The Linux command replaces the stock platform archive in the existing CTS Ninja link recipe, then links the two adapter objects with the Linux loader. The new executable ran the selected case on llvmpipe, returned exit 0 and wrote a complete QPA with `Pass (Compute succeeded)`. The QPA SHA-256 was `86c8359edb38822d34fc1a58779b6b1e53bab64d4f5292452d07614b13b18122`. An invocation with an explicit, alternate Vulkan library path reached the adapter's error and produced no accepted case.

The PS5 command builds the unmodified CTS entry point and selected compute source plus both adapter objects as x86-64 ELF relocatables. It records the compiler commands, symbol checks and hashes. The test object contains the official case registration and matches the independent compile at SHA-256 `7f4954970a1a20002dad97d84f29376804ecee83692d9c96b21b2f595967258e`. The SDK's `malloc_np.h` supplies a declaration expected by the CTS framework's Unix allocation code. The adapter's resolver object imports `vk_icdGetInstanceProcAddr`, and the ordinary relocatable link resolves it against the pinned RADV archive. Two builds of the combined object matched byte for byte at SHA-256 `0b14ebf01eeb1e8d69aea4fff1652d40d5c46342e40a4fd78b0feb98741abca0`. Its remaining imports include CTS framework and platform symbols. PS5 execution remains `NOT_RUN`.

The larger PS5-target compilation also completed CTS's platform, common, Vulkan framework and compute static archives, including the shader compiler dependencies. Reproduce this stage in the same PS5 object build directory.

```bash
ninja -C "$capture/ps5-target" -j4 tcutil-platform deqp-vk-compute
(
  cd "$capture/ps5-target"
  sha256sum framework/{platform/libtcutil-platform,common/libtcutil}.a \
    external/vulkancts/framework/vulkan/libvkutil.a \
    external/vulkancts/modules/vulkan/compute/libdeqp-vk-compute.a
)
```

### Link the focused CTS executable for PS5

The local registrar builds the `dEQP-VK.compute.pipeline.basic` group through the original Khronos factory. The case filter selects `copy_ssbo_single_invocation` from that group. The build uses the original application runner and QPA writer. Set `standalone_link` to the verified output directory of the [standalone ELF link](#link-the-build-host-elf), which supplies the pinned startup objects and AGC link stubs.

```bash
set -eu
for attempt in focused-ps5 focused-ps5-repeat; do
  bash "$fixture/link-focused-ps5.sh" "$capture/$attempt" "$capture/ps5-target" \
    "$sdk" "$radv" "$standalone_link"
  (cd "$capture/$attempt" && sha256sum --quiet --strict -c SHA256SUMS)
done
cmp "$capture"/{focused-ps5,focused-ps5-repeat}/deqp-vk-ps5-link-only.elf
cmp "$capture"/{focused-ps5,focused-ps5-repeat}/import-stub-candidates.tsv
mkdir "$capture/focused-linux-objects"
python3 -B "$fixture/compile-focused.py" "$cts_build" "$capture/focused-linux-objects" \
  > "$capture/focused-linux-objects/inputs.txt"
python3 -B "$fixture/relink-linux.py" "$cts_build" "$capture/focused-linux" \
  "$probe_tools/include" /usr/lib/x86_64-linux-gnu/libvulkan.so.1 \
  --focused-objects "$capture/focused-linux-objects/inputs.txt"
```

Run the same bounded case filter and QPA verifier from `$capture/focused-linux`. The focused Linux build returned exit 0 and a complete QPA with `Pass (Compute succeeded)`. Its QPA SHA-256 was `46e18b3df3b1b069f00516bcea16dcecf0245b29e81f43c60f29f6e937f5d0ac`. The checked-out external revisions matched the [original CTS build inventory](#reproduce-the-single-cts-smoke-on-linux), SHA-256 `8f4453c774c714978f078ab5ba95c5588f174f2b1bc84ad7dadb19aec468b9b8`.

Two PS5 links produced byte-identical ELF64 x86-64 executables at SHA-256 `996213f104aa28e67dc8eda1124288e071022c9b8411ada5c9a54f26e5520ab5`. LLD accepted the link with `--no-undefined` using the public stub inputs. All 288 strong and three weak dynamic imports had public stub candidates across seven declared SONAMEs. The link uses the zlib implementation embedded in RADV. The CTS fallback archive would duplicate its symbols.

The full stock `deqp-vk` target also compiled its sources and archives. Its default executable link requested `-lexecinfo`, `-lm` and `-lrt`, which are absent as separate SDK libraries. An ordinary ELF link using the same CTS objects and the pinned RADV link recipe completed with SHA-256 `e2357f51350ae6db8b45bd833246d6573288bdef0daf0e0115ae27727d5e12b7`. The focused ELF is the package candidate for the M0 case. Final package, runtime providers and execution on the PS5 Slim 13.60 still require verification.

## Standalone RADV compute

The `m0.radv.compute` fixture adapts the offscreen storage-buffer test and shader from PS5_Vulkan `7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc` under GPL-3.0-or-later. It keeps the 64 groups of 64 invocations and the 4,096-word `i * 3 + 7` reference. The fixture uses Vulkan 1.0 synchronization and includes a noncoherent memory path. [Upstream compute test][radv-compute], [upstream shader][radv-compute-shader].

Build from the lab root using the tool paths and `probe_tools` from the Linux setup above.

```bash
fixture=tests/fixtures/m0-radv-compute
out=build/m0-radv-compute/host
cmake -S "$fixture" -B "$out" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DVulkan_INCLUDE_DIR="$probe_tools/include" \
  -DVulkan_LIBRARY=/usr/lib/x86_64-linux-gnu/libvulkan.so.1 \
  '-DCMAKE_CXX_FLAGS=-Wall -Wextra -Wpedantic -Werror'
cmake --build "$out"
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json \
  MESA_SHADER_CACHE_DISABLE=true ctest --test-dir "$out" -V
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json MESA_SHADER_CACHE_DISABLE=true \
  "$out/m0_radv_compute" > "$out/result.json" 2> "$out/start.log"
```

The Linux run reported `PASS` and 4,096 checked words on llvmpipe 26.0.8 with host-coherent memory. CTest passed 2/2. The missing-ICD test exited 1 with `ERROR` at `vkCreateInstance` and `VK_ERROR_INCOMPATIBLE_DRIVER` (-9). An isolated build with an altered shader that wrote `i * 3 + 8` exited 1 and reported 4,096 mismatches. Injected host-side checks returned `UNSUPPORTED`, `TIMEOUT` and `ERROR` for a reduced storage-buffer limit, a fence timeout and device loss respectively. These checks used mocked API responses for the fault conditions.

### Verify the captured compute result

From the lab root, use the existing Linux fixture build. Capture each invocation's streams and exit code into its own directory, then verify each tuple using the same host check defined in the console runbook. [Verifier](../tools/verify-m0-radv-compute.py), [hardware procedure](HARDWARE_VALIDATION.md#m0-standalone-radv-compute-check).

```bash
set -eu
smoke="$PWD/build/m0-radv-compute/host/m0_radv_compute"
captures=$(mktemp -d "$PWD/build/m0-radv-compute/artifact-verifier.XXXXXX")
capture() {
  local run_dir=$1 icd=$2 status=0
  mkdir "$run_dir"
  VK_DRIVER_FILES="$icd" VK_ICD_FILENAMES="$icd" MESA_SHADER_CACHE_DISABLE=true \
    timeout --foreground 20s "$smoke" > "$run_dir/result.json" 2> "$run_dir/start.log" || status=$?
  printf '%s\n' "$status" > "$run_dir/exit-code.txt"
}
capture "$captures/llvmpipe" /usr/share/vulkan/icd.d/lvp_icd.json
capture "$captures/missing-icd" "$captures/absent-icd.json"
python3 -B tools/verify-m0-radv-compute.py "$captures/llvmpipe" > "$captures/llvmpipe/verification.json"
verify_exit=0
python3 -B tools/verify-m0-radv-compute.py "$captures/missing-icd" \
  > "$captures/missing-icd/verification.json" || verify_exit=$?
test "$verify_exit" -eq 1
for attempt in llvmpipe missing-icd; do
  (cd "$captures/$attempt" && sha256sum result.json start.log exit-code.txt verification.json > SHA256SUMS \
    && sha256sum --strict -c SHA256SUMS)
done
python3 -B tests/fixtures/m0-radv-compute/check-result-verifier.py "$captures/llvmpipe" "$captures/missing-icd"
```

The new llvmpipe invocation recorded `PASS`, 4,096 words, one start marker and exit 0. The missing-ICD invocation recorded `ERROR` at `vkCreateInstance`, Vulkan result -9, one start marker and exit 1. Both captured manifests verified. All 18 regression checks passed, including the original captures, duplicates, truncation, invalid fields and inconsistent exit codes. Derived cases exercised file validation on the host.

### Run the homebrew timing probe on Linux

Build the fixture with the Linux commands above. `m0_radv_compute_timing` uses the same shader, Vulkan setup and CPU oracle as `m0_radv_compute`. It checks one dispatch before timing, warms up five times and records 30 samples. It reuses the pipeline and command buffer, clears the 16 KiB output between dispatches and checks all 4,096 words on each dispatch. Capture JSON and diagnostics in separate files.

```bash
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json MESA_SHADER_CACHE_DISABLE=true
ctest --test-dir "$out" --output-on-failure
for run in 1 2 3; do
  timeout --foreground 20s "$out/m0_radv_compute_timing" > "$out/run-$run.json" 2> "$out/run-$run.log"
done
timeout --foreground 20s "$out/m0_radv_compute_timing" --verbose > "$out/verbose.json" 2> "$out/verbose.log"
```

The report records nanoseconds from `steady_clock` for `vkQueueSubmit`, `vkWaitForFences` and the full interval from the start of submission to observed completion. Preparation, readback and logging are outside these intervals. The report retains all samples in order, the average of the middle two samples as the median, nearest-rank p95 and the min, max and range. `gpu_execution_ns` is null. `--verbose` adds one event per completed and checked dispatch. Failure records give the Vulkan stage or mismatch, with the dispatch phase and index on standard error.

On llvmpipe 26.0.8, the three runs passed with host-observed completion medians of 45,975.5 ns, 36,667.5 ns and 52,591 ns. The verbose run emitted 36 dispatch events. CTest passed all three tests, including summary recomputation, missing ICD, invalid option, a successful fence wait with no storage writes, and an injected timeout. Both injected dispatch faults stopped the run with no passing timing report. A separate run with Vulkan validation and synchronization checks active passed without validation messages. These timings characterize the Linux execution path used to verify the probe. The local evidence is under `build/m0-homebrew-timing` with source, build, toolchain and report hashes in `host-SHA256SUMS`.

The PS5 smoke fixture passed the relocatable check and produced two byte-identical pre-packaging ELFs with SHA-256 `f35f3da5d11b83c4df283470a29656cd70db35a8de860ac157b6ea33ea4a0c4d`. See `ps5-final`, `ps5-link-first` and `ps5-link-repeat` in the local evidence directory. The [homebrew app architecture](ARCHITECTURE.md#standalone-homebrew-app) describes how this evidence feeds the planned console runner.

### Cross-build the homebrew timing probe for PS5

Use `--timing` to select the shared timing workload and PS5 RADV resolver. Inherit `sdk`, `radv` and `upstream` from the [pre-packaging link procedure](#link-the-build-host-elf). The two passes each compile and link the timing executable into fresh directories.

```bash
fixture=tests/fixtures/m0-radv-compute
timing_out=$(mktemp -d "$PWD/build/m0-portable-timing.XXXXXX")
for attempt in first repeat; do
  cross="$timing_out/ps5-timing-$attempt"
  link="$timing_out/ps5-timing-link-$attempt"
  "$fixture/cross-check.sh" "$cross" "$sdk" "$radv" --timing
  "$fixture/elf-link-check.sh" "$link" "$sdk" "$radv" "$cross" "$upstream"
  (cd "$link" && sha256sum --quiet --strict -c SHA256SUMS)
done
cmp "$timing_out"/ps5-timing-{first,repeat}/m0-radv-compute-ps5.o
cmp "$timing_out"/ps5-timing-link-{first,repeat}/m0-radv-compute-link-only.elf
sha256sum "$timing_out"/ps5-timing-link-{first,repeat}/m0-radv-compute-link-only.elf
```

The two builds under `build/m0-portable-timing` matched at the relocatable and final ELF stages. The timing ELF SHA-256 is `1771a17336aa5279cf87288037a342c3d0872a675bae25ec6a8fb8847c40a58d`. The validated SPIR-V matches the Linux probe byte for byte. Rechecking the Linux build passed all three CTests and its verbose run recorded 30 samples and 36 dispatch events. An unknown cross-build option exits 2 before creating a build directory.

The default PS5 build still produces the original single-dispatch ELF byte for byte. The timing build pulls two more members from the pinned `libc++.a` and has the same dynamic import list as the single-dispatch build. Public stub candidates for `clock_gettime` are `libkernel.sprx` and `libkernel_sys.sprx`. The report and diagnostic logging imports `fprintf` and `fflush` have a candidate in `libSceLibcInternal.sprx`. The ELF link verifies those declarations on the build host. Title packaging, runtime clock behavior, launch and report retrieval on the Slim remain `NOT_RUN`.

### Check Vulkan validation diagnostics

The Linux verification also ran with the Ubuntu Khronos validation layer `1.4.341.0-1` extracted locally. The loader trace confirmed the layer was active, the synchronization check emitted no validation diagnostics and the result matched the regular Linux run. Keep the build environment and `out` from above when repeating this check.

```bash
mkdir -p build/m0-radv-compute/validation-tools
(
  cd build/m0-radv-compute/validation-tools
  apt-get download vulkan-validationlayers=1.4.341.0-1
  dpkg-deb -x ./vulkan-validationlayers_1.4.341.0-1_amd64.deb extracted
)
validation_tools=$(realpath build/m0-radv-compute/validation-tools/extracted/usr)
env LD_LIBRARY_PATH="$validation_tools/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH" \
  VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json MESA_SHADER_CACHE_DISABLE=true \
  VK_LAYER_PATH="$validation_tools/share/vulkan/explicit_layer.d" \
  VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation VK_LAYER_VALIDATE_SYNC=1 VK_LOADER_DEBUG=layer \
  timeout 20s "$out/m0_radv_compute" > "$out/validation-result.json" 2> "$out/validation.log"
cmp "$out/result.json" "$out/validation-result.json"
rg 'Insert instance layer.*VK_LAYER_KHRONOS_validation' "$out/validation.log"
if rg -ni 'VUID-|SYNC-HAZARD|Validation Error|Validation Warning' \
    "$out/validation.log" "$out/validation-result.json"; then
  exit 1
fi
```

### Cross-link the PS5-target relocatable

Use the pinned archives, `build_root` and LLVM tool paths from the SDK build. The cross check also needs the compiler builtins package from the [relocatable link check](#reproduce-the-ps5-relocatable-link-check). Choose a fresh directory for the output.

```bash
mkdir -p build/m0-radv-compute
cross_out=build/m0-radv-compute/ps5
sdk="$build_root/PS5_Vulkan/.deps/native/ps5-payload-sdk"
radv="$build_root/PS5_Vulkan/.deps/native/radv-release"
tests/fixtures/m0-radv-compute/cross-check.sh "$cross_out" "$sdk" "$radv"
(cd "$cross_out" && sha256sum -c SHA256SUMS)
```

The Linux and PS5-target builds used the same validated embedded SPIR-V. Its SHA-256 was `640db3b3120e31dcf953100f55f179c1bacc2b0ee954f536feabb98562ca03ae`. Two independent cross builds produced byte-identical x86-64 ELF relocatables with SHA-256 `c90d87bfb94d578d746ccaea2a793a238989dab5600664747bbce3f9c21b27af`. The manifest verifies source, inputs, artifacts and toolchain information. The object retained 259 strong undefined symbols, including the five AGC imports from the preflight above.

### Link the build-host ELF

Use the same cross build directory, SDK, RADV archive and LLVM paths. Stage the nine public upstream files from the pinned revision. The link check verifies each Git blob hash, checks the cross manifest covers both application objects and the static libraries, and records the SDK link inputs and compiler versions. [Pinned input manifest](../tests/fixtures/m0-radv-compute/elf-link-inputs.txt), [upstream linker recipe][radv-link].

```bash
set -euo pipefail
fixture=tests/fixtures/m0-radv-compute
revision=7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc
link_out=$(mktemp -d build/m0-radv-compute/elf-link.XXXXXX)
upstream="$link_out/upstream"
while read -r _ path; do
  mkdir -p "$upstream/$(dirname "$path")"
  curl -fsSL "https://raw.githubusercontent.com/mihawk-99/PS5_Vulkan/$revision/$path" \
    -o "$upstream/$path"
done < "$fixture/elf-link-inputs.txt"
for attempt in first repeat; do
  "$fixture/elf-link-check.sh" "$link_out/$attempt" "$sdk" "$radv" "$cross_out" "$upstream"
  (cd "$link_out/$attempt" && sha256sum --quiet --strict -c SHA256SUMS)
done
cmp "$link_out"/{first,repeat}/m0-radv-compute-link-only.elf
cmp "$link_out"/{first,repeat}/elf-link.map
cmp "$link_out"/{first,repeat}/elf-archive-members.tsv
cmp "$link_out"/{first,repeat}/import-stub-candidates.tsv
awk -F '\t' 'NR > 1 && $2 > 0 {print $2 "/" $1, $3}' \
  "$link_out/first/elf-archive-members.tsv"
```

The two pre-packaging ELF files matched byte for byte with SHA-256 `3b621e426545170c13ff4e501af6a952b43bba747d98f3ddb8b6904d4784b6fb`. The output is ELF64 x86-64 `ET_DYN` with entry point `0x120` and defined startup, Vulkan ICD and compute dispatch symbols. The public AGC stubs satisfy the build-host link and record `libSceAgc.prx` and `libSceAgcDriver.prx` among the seven `DT_NEEDED` entries. The five AGC symbols are among the 284 strong imports expected from runtime libraries. The script stops after local ELF inspection. Hardware remains `NOT_RUN` pending a verified package, runtime dependencies and supported launch. [Standalone operator procedure](HARDWARE_VALIDATION.md#m0-standalone-radv-compute-check).

Two negative checks used copies of the link inputs. Removing the `main.o` entry from the cross manifest or changing a pinned upstream stub each caused exit 2 before an ELF was written.

The LLD section map and archive extraction table also matched across the repeated links. LLD's extraction table covers the selectively loaded archives. Use the section map and `llvm-ar t` for the RADV archive, which the recipe passes with `--whole-archive`. Mesa and zlib both have members named `compress.c.o` and `crc32.c.o`. Use the pinned Mesa build's `build.ninja` inputs to disambiguate those paths. The hash manifest covers both reports and the dynamic table. [Component and notice inventory](UPSTREAM.md#standalone-compute-component-review).

#### Review the public stub candidates

`import-stub-candidates.tsv` lists the symbol and binding from the ELF and the matching SONAME, file, binding and type from the staged public link stubs. It considers stubs whose SONAME appears in the ELF's `DT_NEEDED` table. The report includes multiple rows when several stubs export a name. [Inventory script](../tests/fixtures/m0-radv-compute/check-link-imports.py).

All 284 strong imports and three weak imports had public candidates with matching symbol types. Of the strong imports, 112 appeared under both `libkernel.sprx` and `libkernel_sys.sprx`. The other 172 appeared under a single SONAME. The SDK files `libc_stub_weak.so` and `libSceLibcInternal.so` were byte-identical and supplied duplicate candidates for the same SONAME. The two links produced matching 558-row inventories. Omitting the AGC driver stub caused the inventory command to report the missing `libSceAgcDriver.prx` SONAME and exit 1. A separate generic Linux ELF fixture with a matching SONAME but a missing symbol also failed the strong-import check. [SDK stub aliases][sdk-stub-aliases].

The weak imports are `fclose`, `fflush` and `malloc_usable_size`. Check `fflush` during the final runtime review because the fixture calls it to flush the start marker and the SDK wrapper calls the underlying `fflush`. The inventory describes build-host declarations. The final package review must establish which providers and ABIs are available to the title on firmware 13.60. [Fixture entry point](../tests/fixtures/m0-radv-compute/main.cpp), [SDK flush wrapper][sdk-flush-wrapper].

### Stage the title review archive

Use the two link directories and their common cross-build. The exporter verifies the existing SHA-256 manifests, checks that both links used the supplied cross-build and requires agreement on the ELF and its link reports. It takes a fresh ZIP path in an existing output directory and uses Python 3.11 or later.

```bash
review=$(mktemp -d "$PWD/build/m0-title-review.XXXXXX")
builder=tests/fixtures/m0-radv-compute/stage-title-review.py
for name in first repeat; do
  python3 -B "$builder" "$link_out/first" "$link_out/repeat" "$cross_out" "$review/$name.zip"
done
cmp "$review/first.zip" "$review/repeat.zip"
python3 -m zipfile -t "$review/first.zip"
python3 -m zipfile -e "$review/first.zip" "$review/inspect"
(cd "$review/inspect" && sha256sum --strict -c SHA256SUMS)
```

`manifest.json` identifies the ELF and workload, source hashes, SDK and RADV revisions, linked archives and required runtime libraries. The `application` entry records the display name **ProsperoVK Lab** and the lab-assigned UUID `a5acce60-1153-47a5-8c89-80f3413d55fb`. Repeated exports use the same identity. The smoke ZIP includes the original ELF, the validated shader, the import reports and the host result verifier. The manifest omits host paths from the component inventory. Keep the ZIP local for title review and use the final package's file list for any distribution review. [Component review](UPSTREAM.md#standalone-compute-component-review).

The two exports with the app identity from `build/m0-homebrew-timing` matched byte for byte and all extracted entries passed their checksum checks. The extracted ELF matched the original link. The manifest lists seven runtime library declarations. The ZIP SHA-256 is `754f58a2f07708091721c1daa63aa094d9400cc1a7cc268cf3a7e4a5b6a877c2`. The initial exporter verification also rejected an altered dynamic-table report. Rehashing the altered file still triggered the link-record consistency check. Both attempts left the requested ZIP path absent, and an existing archive survived an attempted export to the same path.

The next acceptance evidence is the installable title and its digest from an authorized deployment environment, the runtime providers and verified launch and report retrieval. The review archive leaves these fields open and records console validation as `NOT_RUN`. [Console procedure](HARDWARE_VALIDATION.md#m0-standalone-radv-compute-check).

#### Export the timing review ZIP

Use `timing_out` from the [timing cross-build](#cross-build-the-homebrew-timing-probe-for-ps5). Link the first cross-build again so both link manifests refer to the same cross-build receipt used by the exporter.

```bash
cross="$timing_out/ps5-timing-first"
first="$timing_out/ps5-timing-link-first"
repeat="$timing_out/ps5-timing-link-review"
"$fixture/elf-link-check.sh" "$repeat" "$sdk" "$radv" "$cross" "$upstream"
review_zip="$timing_out/prosperovk-lab-ps5-benchmark-review.zip"
python3 -B "$fixture/stage-title-review.py" "$first" "$repeat" "$cross" "$review_zip"
python3 -m zipfile -t "$review_zip"
```

The timing review ZIP identifies the original PS5 benchmark ELF, its source files and dependencies, and its report capture contract. The manifest records timing mode, JSON report version 1 and the optional `--verbose` argument. The smoke archive retains its single-dispatch verifier. The `title` fields remain open pending a verified package and launch environment.

The two timing exports in `build/m0-ps5-benchmark-package` matched byte for byte with SHA-256 `8f0eba9df3c522e77584c7f21a87e3eb5e69a4e9c4454b3f8ec58f1c27f9e177`. All archived file hashes verified, and the extracted ELF matched the original link. The smoke export retained its original report contract and verifier. A cross-build manifest with both entry sources was rejected before archive creation.

### Verify RADV archive and generated inputs

Use the existing release build, staged SDK, `build_root` and tool environment from the [archive build](#reproduce-the-sdk-and-release-archive-build). The host check uses the ordered Ninja object inputs to reassemble the archive and the compilation database to record each position, object and direct source with hashes. It replays the two OpenCL generator commands in the same build context with fresh output paths, compares the outputs and hashes the generator manifests and dependency files. [Verification script](../tests/fixtures/m0-radv-compute/radv-source-check.py).

```bash
set -e
native="$build_root/PS5_Vulkan/.deps/native"
mesa_build="$build_root/PS5_Vulkan/.deps/work/radv-build-ps5-release"
mkdir -p build/m0-radv-compute
evidence=$(mktemp -d "$PWD/build/m0-radv-compute/radv-source.XXXXXX")
for attempt in first repeat; do
  python3 -B tests/fixtures/m0-radv-compute/radv-source-check.py "$evidence/$attempt" \
    "$mesa_build" "$native/ps5-payload-sdk" "$native/radv-release"
  (cd "$evidence/$attempt" && sha256sum --quiet --strict -c SHA256SUMS)
done
for artifact in radv-reassembled.a radv-archive-inputs.tsv \
    libpoly.spv libpoly.cpp libpoly.h libradv_cl.spv libradv_cl.cpp libradv_cl.h; do
  cmp "$evidence"/{first,repeat}/"$artifact"
done
```

Each reassembled archive matched the staged release and the original Ninja archive byte for byte at SHA-256 `d06eaf176b42fda32b740a660f343c1e72167cb11a6f6965669ba23437bdf441`. The 704-row input list identified `compress.c.o` at positions 97 and 498, and `crc32.c.o` at 99 and 490. The earlier position in each pair corresponds to a Mesa utility source and the later position to zlib 1.3.1. Extracting both occurrences with `prospero-ar xN` and using `cmp` confirmed the attribution. The archive comparison reuses the already compiled objects.

Changing only the recorded archive digest in a copy of the provenance file caused the script to exit 1 before creating an evidence directory.

| Generated library | OpenCL inputs matched to the staged dependency list | SPIR-V SHA-256 |
| --- | --- | --- |
| `libpoly` | 28 files from the pinned Mesa commit, including `geometry.cl` and `tessellation.cl`, plus two Clang resource headers | `1db280963aeec85210d502add98a347cf2cda45d6eef86b3bb68e33eee6acda5` |
| `libradv_cl` | 29 files from the pinned Mesa commit, including `radv_gs_compute.cl`, plus the same two Clang resource headers | `73471d5beff0ac0c2cb6bbcd62d94b82bcfe4ee8d866c35ceab306369a0f7754` |

The replay reproduced each module's SPIR-V, generated C++ and header byte for byte. The recorded Mesa source dependencies matched commit `1ba9874f478657ccf6da72ce55f0260164cc0bd0`. The host generators were built with GCC/G++ 15.2.0. The OpenCL compiler used LLVM and Clang 21.1.8, the LLVM/SPIR-V translator 21.1.5 and SPIRV-Tools 2026.1. The Clang headers came from Ubuntu `libclang-common-21-dev` `1:21.1.8-6ubuntu1`. Both modules declare the `Physical64 OpenCL` memory model and passed structural validation with `spirv-val --target-env spv1.4`.

[sdk-setup]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/platform/tools/setup-sdk.sh
[cross-file]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tooling/radv/ps5-cross.ini
[radv-builder]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/build-radv.sh
[radv-link]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/radv-link.sh
[sdk-stub-aliases]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/sce_stubs/Makefile#L56-L60
[sdk-flush-wrapper]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/platform/src/memstream.c#L204-L206
[radv-compute]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/radv/radv_smoke.c#L442
[radv-compute-shader]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/radv/shaders/smoke.comp
[template-link]: https://github.com/mihawk-99/PS5_VulkanTemplate/blob/91179df760df1e6c6f2d4d172bc435319d79ff3c/ps5/tools/link-title.sh
