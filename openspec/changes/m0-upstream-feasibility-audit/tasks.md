# Tasks

## 1. Audit and build feasibility

- [x] 1.1 Read the project contract and issue inventory, initialize OpenSpec 1.14.0, and record the resulting workflow.
- [x] 1.2 Verify upstream references and inspect the pinned tree, build and license files. Record revisions, CTS report mechanics, unresolved sources and reuse choices in `docs/UPSTREAM.md`.
- [x] 1.3 Map Vulkan requirements to pinned CTS cases and proposed lab IDs. Record the disposition and correctness evidence for each group in `docs/VULKAN_COVERAGE.md`.
- [x] 1.4 Run the Linux CMake, loader, queue, SPIR-V and missing-ICD checks and the public PS5-target compile check. Record exact commands and observed results in `docs/M0_TOOLCHAIN.md`.
- [x] 1.5 Define a single-case target smoke and evidence collection workflow in `docs/HARDWARE_VALIDATION.md`. Record the verified and pending gates in the roadmap and prepare the M1 spec and tasks.
- [x] 1.6 Build the pinned SDK platform library and RADV release archive. Record tool versions, archive digest, exported symbols and the object compile with matching headers in `docs/M0_TOOLCHAIN.md`.
- [x] 1.7 Build the pinned, unmodified upstream Linux CTS and execute the single runbook case on llvmpipe. Verify the exact case ID, upstream status and complete QPA, then record the commands and evidence hashes in `docs/M0_TOOLCHAIN.md`.
- [x] 1.8 Verify PS5-target relocatable linkage of the CTS resolver reference and SDK allocation wrappers. Compare whole and selective RADV archive extraction and record the observed definitions and unresolved import count in `docs/M0_TOOLCHAIN.md`.
- [x] 1.9 Attempt the pinned CTS console configuration, compare the staged SDK exports against RADV's graphics imports and assess the public focused CTS port against the selected case and driver. Record the results in the toolchain evidence and upstream audit.
- [x] 1.10 Verify single-case QPA framing and identity around the pinned upstream parser. Exercise the verifier on the Linux CTS result, incomplete reports, contradictory case IDs and terminated or failing cases. [Linux evidence](../../../docs/M0_TOOLCHAIN.md#reproduce-the-single-cts-smoke-on-linux).
- [x] 1.11 Build a local headless adapter and compile the unchanged selected Khronos CTS workload for the PS5 target. Exercise the same adapter and case in the Linux CTS harness and record exactly which PS5 build and execution steps pass. [Local headless evidence](../../../docs/M0_TOOLCHAIN.md#build-the-local-cts-headless-adapter).
- [x] 1.12 Link a focused PS5-target CTS ELF using the upstream basic compute case factory. Verify reproducible linkage and confirm the focused registrar preserves the exact case and QPA result on Linux. [Link and run evidence](../../../docs/M0_TOOLCHAIN.md#link-the-focused-cts-executable-for-ps5).

## 2. Target and maintainer gates

- [ ] 2.1 Resolve the console CTS fork revision and compiled dependencies or obtain equivalent provenance from the authorized artifact provider. Verify console title linkage, packaging and hashes.
- [ ] 2.2 Verify operator access, transfer, startup and log retrieval on a Slim with firmware 13.60. Run the selected case once and retain its original status, QPA, identified build and artifact digests.
- [x] 2.3 Apply the reference-license direction to original work and record the rationale in `docs/UPSTREAM.md`. Verify that the `LICENSE` text matches the pinned PS5_Vulkan and SDK copies and mark original source files with `GPL-3.0-or-later`.
- [ ] 2.4 Review combined title linkage and distribution against the actual component, source, asset and notice manifest. The [standalone pre-packaging inventory](../../../docs/UPSTREAM.md#standalone-compute-component-review) supplies evidence for the linked ELF.
- [ ] 2.5 Verify M0 issue acceptance against the build and run artifacts, then update milestone status and archive the change after review.
- [x] 2.6 Verify read-only management access and record reported firmware, model label and CTS title lookup in `docs/HARDWARE_VALIDATION.md`.
- [x] 2.7 Record the operator's confirmation of the PS5 Slim model alongside the dashboard firmware evidence.
