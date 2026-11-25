# ProsperoVK Lab handoff

Work is on `feat/m0-vulkan-feasibility`. M0 passed on 2026-11-25. The target is PS5 Slim, firmware 13.60, with the original compute baseline in run-000001 and a verified hardened compute run-000002, including observed shell exit. The CTS title passed the selected case on hardware and returned normally to the shell. [Milestone gates](MILESTONES.md#m0-audit-and-feasibility)

## Verified work

| Area | Evidence |
| --- | --- |
| Linux software Vulkan | The shared offscreen compute fixture validates all 4,096 output words. The timing probe runs one correctness check, five warm-ups and 30 measured dispatches, with optional verbose logs. CTest covers report statistics, invalid arguments, missing ICD, stale readback and timeout. [Linux commands](M0_TOOLCHAIN.md#run-the-homebrew-timing-probe-on-linux) |
| Khronos CTS | The original `dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation` passed on llvmpipe at CTS revision `f6a29701220f34dd1407513bfe80d74ca7b392ce`. The focused PS5 title is deployed as PPSA99744. [Case verification](M0_TOOLCHAIN.md#build-the-local-cts-headless-adapter) |
| PS5-target build | The single-dispatch smoke and timing probe link against Mihawk's RADV archive. Two timing builds produced identical ELFs. Their reports measure CPU-observed submission and completion. GPU timing remains unavailable. [Build and import checks](M0_TOOLCHAIN.md#cross-build-the-homebrew-timing-probe-for-ps5) |
| Manual deployment | `build/m0-title-final/dist/PPSA99743/` and `PPSA99743.zip` in the same directory. The package passed host structural validation. [Build record](M0_TOOLCHAIN.md#build-the-deployable-m0-title) |
| Review artifact | The exporter creates deterministic smoke and timing ZIPs with the ELF, shader and build provenance. An upload and download through Prospero Manager matched the local timing ZIP byte for byte. [Archive commands](M0_TOOLCHAIN.md#export-the-timing-review-zip), [transfer evidence](HARDWARE_VALIDATION.md#m0-file-transfer-check) |

## Resume from this branch

Use [the harness](HARNESS.md) for preflight, Linux tests, title packaging, authorized transfer, readback and report retrieval. The existing hardware-tested title and its run are preserved. The hardened package passed on the Slim, including normal shell exit. Its build ID, raw report hashes and separate timing samples are in the [hardware record](HARDWARE_VALIDATION.md#hardened-compute-result).

The first verified run and hashes are in [the baseline](HARDWARE_VALIDATION.md#first-verified-slim-baseline). The verified CTS folder is `build/m0-final-acceptance/cts/title/dist/PPSA99744/` with its ZIP alongside. See the [build record](M0_TOOLCHAIN.md#focused-cts-deployment-package). The [original Slim QPA and acceptance record](HARDWARE_VALIDATION.md#focused-cts-result) close the M0 dependency. The M1 host runner and PS5 package are described below. See [final title review](UPSTREAM.md#packaged-title-review).

## M1 portable runner

The source branch is `feat/m1-portable-vulkan-runner`, based on M0 merge `d01125f`. The M1 case writes 64 deterministic output words between two guards. Its resources, synchronization and CPU timing intervals derive from the hardware-validated M0 implementation. The M0 timings use a different shader and dispatch size. The M1 OpenSpec change stays active until the Slim evidence is accepted.

### Linux reproduction

Install CMake 3.24+, Ninja, a C++20 compiler, Git, Vulkan headers and loader, glslangValidator, spirv-val, a Vulkan ICD and Python with jsonschema. Set the loader to a known ICD. In the verified workspace, the M0 environment script supplies the host tools and selects llvmpipe. The configure command below includes the paths required on this host.

```bash
source /tmp/prosperovk-harness-env.sh
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json MESA_SHADER_CACHE_DISABLE=true
cmake -S . -B build/m1-linux -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DVulkan_INCLUDE_DIR=/tmp/prosperovk-m0.QucJcB/toolroot/usr/include \
  -DVulkan_LIBRARY=/usr/lib/x86_64-linux-gnu/libvulkan.so.1 \
  -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build build/m1-linux
ctest --test-dir build/m1-linux --output-on-failure -j4
cmake --install build/m1-linux --prefix "$PWD/build/m1-installed"
mkdir -p build/m1-evidence/linux
bin=build/m1-installed/bin/prosperovk
"$bin" --list
"$bin" --inventory --device 0 --report build/m1-evidence/linux/inventory.json
"$bin" --case core.compute.storage-buffer --device 0 --report build/m1-evidence/linux/report.json
python3 tools/validate-m1.py build/m1-evidence/linux/inventory.json
python3 tools/validate-m1.py build/m1-evidence/linux/report.json
```

Choose fresh report paths on subsequent runs. On a host with system Vulkan development packages, omit the Vulkan path overrides. The registry and both adapters use the same workload implementation. Inventory mode creates an instance and queries the selected device without creating a device or submitting a command buffer.

### Regression commands

```bash
tools/m0 linux build/m1-m0-regression \
  -DVulkan_INCLUDE_DIR=/tmp/prosperovk-m0.QucJcB/toolroot/usr/include \
  -DVulkan_LIBRARY=/usr/lib/x86_64-linux-gnu/libvulkan.so.1
python3 -B tests/fixtures/m0-radv-compute/check-result-verifier.py \
  build/m0-baseline-smoke.UEI73b/llvmpipe build/m0-baseline-smoke.UEI73b/missing-icd
python3 -B tests/fixtures/m0-cts/check-title-capture.py build/m0-cts/source
python3 -B tests/fixtures/m0-cts/check-qpa-verifier.py build/m0-cts/source build/m0-baseline-cts.XA61W6/TestResults.qpa
python3 -B tests/fixtures/m0-title/check-harness.py build/m0-final-harness/title/dist/PPSA99743
tools/m0 verify build/m0-final-acceptance/cts/title/dist/PPSA99744
OPENSPEC_TELEMETRY=0 openspec validate --all --strict
```

The M1 tests exercise both guards, incorrect payload, incompatible memory bits, insufficient limits, missing entry points, report errors, pending resources, and retry prevention after device loss or timeout. The non-coherent test injects memory flags on llvmpipe to exercise flush and invalidate. PS5 deployment, launch, retrieval and evidence checks use the [M1 harness commands](HARNESS.md#m1-portable-runner).
