# ProsperoVK Lab handoff

Work is on `feat/m0-vulkan-feasibility`. M0 remains open. The target is PS5 Slim, firmware 13.60, with verified standalone compute correctness and CPU timing from run-000001. Shell exit and the selected hardware CTS case remain open. [Milestone gates](MILESTONES.md#m0-audit-and-feasibility)

## Verified work

| Area | Evidence |
| --- | --- |
| Linux software Vulkan | The shared offscreen compute fixture validates all 4,096 output words. The timing probe runs one correctness check, five warm-ups and 30 measured dispatches, with optional verbose logs. CTest covers report statistics, invalid arguments, missing ICD, stale readback and timeout. [Linux commands](M0_TOOLCHAIN.md#run-the-homebrew-timing-probe-on-linux) |
| Khronos CTS | The original `dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation` passed on llvmpipe at CTS revision `f6a29701220f34dd1407513bfe80d74ca7b392ce`. The focused PS5-target ELF was linked locally. [Case verification](M0_TOOLCHAIN.md#build-the-local-cts-headless-adapter) |
| PS5-target build | The single-dispatch smoke and timing probe link against Mihawk's RADV archive. Two timing builds produced identical ELFs. Their reports measure CPU-observed submission and completion. GPU timing remains unavailable. [Build and import checks](M0_TOOLCHAIN.md#cross-build-the-homebrew-timing-probe-for-ps5) |
| Manual deployment | `build/m0-title-final/dist/PPSA99743/` and `PPSA99743.zip` in the same directory. The package passed host structural validation. [Build record](M0_TOOLCHAIN.md#build-the-deployable-m0-title) |
| Review artifact | The exporter creates deterministic smoke and timing ZIPs with the ELF, shader and build provenance. An upload and download through Prospero Manager matched the local timing ZIP byte for byte. [Archive commands](M0_TOOLCHAIN.md#export-the-timing-review-zip), [transfer evidence](HARDWARE_VALIDATION.md#m0-file-transfer-check) |

## Resume from this branch

Use [the harness](HARNESS.md) for preflight, Linux tests, title packaging, authorized transfer, readback and report retrieval. The existing hardware-tested title and its run are preserved. The hardened package is a distinct build and has host evidence only.

The first verified run and hashes are in [the baseline](HARDWARE_VALIDATION.md#first-verified-slim-baseline). M0 still needs the selected CTS case's original hardware QPA and identified build, plus independent evidence of normal shell exit. Retain the M1 dependency until the M0 gates are met or explicitly changed. See [final title review](UPSTREAM.md#packaged-title-review).
