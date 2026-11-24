# Tasks

## 1. Shared compute workload

- [x] 1.1 Adapt the pinned upstream compute shader and integer oracle with source attribution. Verify that the Linux fixture checks all 4,096 words.
- [x] 1.2 Gate queue, limits and memory. Handle noncoherent memory, Vulkan failures and a finite wait. Verify the outcome on llvmpipe and when no ICD is available.

## 2. Reproducible build evidence

- [x] 2.1 Build the Linux fixture and validate its embedded SPIR-V. Record the commands, provenance and captured result in the M0 toolchain evidence.
- [x] 2.2 Cross-compile the same fixture, verify the relocatable link with the pinned RADV and SDK artifacts and record hashes and remaining imports.
- [x] 2.3 Repeat the build-host ELF link with pinned upstream startup and AGC link stubs. Verify byte identity, defined compute entry points, dynamic library dependencies and source hashes.
- [x] 2.4 Capture the ELF section map and archive extraction table. Inventory source and notice provenance from the observed inputs and record what the final package review still needs.
- [x] 2.5 Verify the RADV archive's ordered object provenance and reproduce the generated libpoly and libradv_cl outputs against the staged build. [Replay evidence](../../../docs/M0_TOOLCHAIN.md#verify-radv-archive-and-generated-inputs).
- [x] 2.6 Check captured compute results, start logs and exit codes on the host. Exercise successful and failed Linux executions and reject incomplete or inconsistent copies. [Capture evidence](../../../docs/M0_TOOLCHAIN.md#verify-the-captured-compute-result).
- [x] 2.7 Inventory the final host ELF's imports and matching public link stub exports. Verify strong import coverage and preserve alternate provider candidates for the package review. [Import inventory evidence](../../../docs/M0_TOOLCHAIN.md#review-the-public-stub-candidates).

## 3. Console evidence

- [ ] 3.1 Obtain a verified final title build and supported launch and result-capture path. Run once on the identified Slim with firmware 13.60 and record the evidence required by the hardware runbook.

## Workflow follow-up

- Review implementation and evidence before archiving the change.
