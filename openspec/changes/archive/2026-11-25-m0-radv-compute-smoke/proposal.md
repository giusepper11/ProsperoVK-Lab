# Proposal

## Why

The documented PS5 CTS fork is unavailable. The public RADV smoke source provides an independent compute correctness check that the lab can validate and cross-build while the CTS path is unresolved.

## What Changes

- Adapt the pinned upstream storage-buffer compute workload into a standalone offscreen M0 fixture.
- Exercise the same shader and integer reference on Linux, and check PS5-target compilation and static RADV linkage on the build host.
- Record the actual static archive participation and runtime library declarations of the pre-packaging ELF for the M0 source and notice review.
- Verify the captured start marker, result and exit code on the host using the same contract for local and console runs.
- Exercise a Linux timing probe built from the same workload to verify correctness-first sample capture and optional diagnostic logging for the planned homebrew app.
- Cross-build the shared timing probe as an opt-in PS5 ELF and inspect its runtime imports before title integration.
- Assemble a reproducible local title review archive from the verified PS5 link outputs, with the build identity, declared runtime dependencies and capture contract needed to review packaging.
- Document the evidence required to run that fixture on the connected firmware 13.60 console through a verified title environment.

## Capabilities

### New Capabilities

- `radv-compute-smoke` provides one bounded Vulkan compute dispatch, exact readback and a machine-readable outcome.

### Modified Capabilities

## Impact

Adds an isolated C++20/CMake fixture, a PS5 build-host check and M0 evidence. The original CTS case and the M1 portable runner retain their existing acceptance criteria.

M0 also requires a complete, host-validated title folder and deployment ZIP for manual transfer. Console execution is a separate operator gate.

Harden the existing build and packaging path with one clean-checkout entry point, explicit transfer operations and independently verifiable package and hardware evidence.
