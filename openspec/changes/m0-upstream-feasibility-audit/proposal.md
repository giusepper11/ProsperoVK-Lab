## Why

The lab needs reproducible evidence for its driver, test reuse, build strategy, and console prerequisites before it commits to a portable runtime.

## What Changes

- Pin and inspect the public Vulkan projects, the CTS baseline, and the platform toolchain.
- Record a coverage matrix, reuse decisions, verified Linux commands, and the PS5 evidence required to close M0.
- Verify a temporary Linux toolchain with an isolated CMake fixture and prepare a separate M1 proposal.
- Reuse the pinned CTS QPA parser and verify the single-case report's framing and case identity before accepting it as part of run evidence.
- Try a local headless build of the pinned Khronos CTS with a small Vulkan loader adapter. Keep the upstream workload and logging code unchanged.

## Capabilities

This feasibility change has no product capability deltas.

## Impact

The change affects audit and runbook documentation, OpenSpec configuration, a Linux verification fixture and a host-side QPA verifier. The M0 exit gate includes console feasibility and the maintainer's license decision.
