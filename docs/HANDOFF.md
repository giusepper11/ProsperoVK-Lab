# ProsperoVK Lab handoff

Work is on `feat/m0-vulkan-feasibility`. M0 remains open. The target is PS5 Slim, firmware 13.60, with console execution recorded as `NOT_RUN`. [Milestone gates](MILESTONES.md#m0-audit-and-feasibility)

## Verified work

| Area | Evidence |
| --- | --- |
| Linux software Vulkan | The shared offscreen compute fixture validates all 4,096 output words. The timing probe runs one correctness check, five warm-ups and 30 measured dispatches, with optional verbose logs. CTest covers report statistics, invalid arguments, missing ICD, stale readback and timeout. [Linux commands](M0_TOOLCHAIN.md#run-the-homebrew-timing-probe-on-linux) |
| Khronos CTS | The original `dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation` passed on llvmpipe at CTS revision `f6a29701220f34dd1407513bfe80d74ca7b392ce`. The focused PS5-target ELF was linked locally. [Case verification](M0_TOOLCHAIN.md#build-the-local-cts-headless-adapter) |
| PS5-target build | The single-dispatch smoke and timing probe link against Mihawk's RADV archive. Two timing builds produced identical ELFs. Their reports measure CPU-observed submission and completion. GPU timing remains unavailable. [Build and import checks](M0_TOOLCHAIN.md#cross-build-the-homebrew-timing-probe-for-ps5) |
| Review artifact | The exporter creates deterministic smoke and timing ZIPs with the ELF, shader and build provenance. An upload and download through Prospero Manager matched the local timing ZIP byte for byte. [Archive commands](M0_TOOLCHAIN.md#export-the-timing-review-zip), [transfer evidence](HARDWARE_VALIDATION.md#m0-file-transfer-check) |

## Reproduce from this branch

Build outputs and raw reports are stored locally under `build/`. Use the [toolchain setup](M0_TOOLCHAIN.md#reproduce-the-sdk-and-release-archive-build) to regenerate them. The RADV archive uses PS5_Mesa `1ba9874f478657ccf6da72ce55f0260164cc0bd0` and PS5_PayloadSDK `b83202be73e930050e00de0f1b4d9ec46c0391bf`. Verify the component hashes and notice obligations against the [upstream audit](UPSTREAM.md#standalone-compute-component-review).

```bash
cmake -S tests/fixtures/m0-radv-compute -B build/handoff-linux -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/handoff-linux
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json \
  MESA_SHADER_CACHE_DISABLE=true ctest --test-dir build/handoff-linux --output-on-failure
OPENSPEC_TELEMETRY=0 openspec validate --all --strict
```

The Linux build requires Vulkan headers and loader, `glslangValidator`, `spirv-val`, a C++20 compiler and Python for testing. See the [verified Linux configuration](M0_TOOLCHAIN.md#standalone-radv-compute) for explicit dependency paths.

## Resume at the hardware gate

1. Identify an authorized title packaging and launch environment for the target. Record the installable title's manifest, executable and package digests, runtime library providers and review of source and notices.
2. Run the single-dispatch `m0.radv.compute` first. Retrieve `result.json`, `start.log` and the observed `exit-code.txt` and verify them against the exact title build. [Hardware runbook](HARDWARE_VALIDATION.md#m0-standalone-radv-compute-check)
3. Keep the hardware and Linux evidence distinct. Resolve the M0 gates before starting the [M1 portable runner](../openspec/changes/m1-portable-vulkan-smoke/proposal.md).
