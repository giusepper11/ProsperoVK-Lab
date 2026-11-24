# Proposal

## Why

The documented PS5 CTS fork is unavailable. The public RADV smoke source provides an independent compute correctness check that the lab can validate and cross-build while the CTS path is unresolved.

## What Changes

- Adapt the pinned upstream storage-buffer compute workload into a standalone offscreen M0 fixture.
- Exercise the same shader and integer reference on Linux, and check PS5-target compilation and static RADV linkage on the build host.
- Record the actual static archive participation and runtime library declarations of the pre-packaging ELF for the M0 source and notice review.
- Verify the captured start marker, result and exit code on the host using the same contract for local and console runs.
- Document the evidence required to run that fixture on the connected firmware 13.60 console through a verified title environment.

## Capabilities

### New Capabilities

- `radv-compute-smoke` provides one bounded Vulkan compute dispatch, exact readback and a machine-readable outcome.

### Modified Capabilities

## Impact

Adds an isolated C++20/CMake fixture, a PS5 build-host check and M0 evidence. The original CTS case and the M1 portable runner retain their existing acceptance criteria.
