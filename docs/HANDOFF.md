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

The first verified run and hashes are in [the baseline](HARDWARE_VALIDATION.md#first-verified-slim-baseline). The verified CTS folder is `build/m0-final-acceptance/cts/title/dist/PPSA99744/` with its ZIP alongside. See the [build record](M0_TOOLCHAIN.md#focused-cts-deployment-package). The [original Slim QPA and acceptance record](HARDWARE_VALIDATION.md#focused-cts-result) close the M0 dependency. M1 remains planned. See [final title review](UPSTREAM.md#packaged-title-review).
