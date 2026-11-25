## Why

Issue #2 needs a minimal shared runner that establishes what each target reports and whether a bounded Vulkan workload produces correct output. The M0 audit identifies a Linux loader path and a source-backed PS5 static RADV path.

## What Changes

- Add a CMake build, a minimal CLI, a case registry, and a versioned result schema.
- Inventory Vulkan API and driver identity, device features and limits, extensions, formats, queues, and memory types. Record case requirements, requested enablement, and observed outcomes.
- Run one deterministic offscreen integer compute case with exact CPU readback validation through the Linux and verified PS5 adapters.
- Record status, provenance, and case lifecycle evidence for validation and manual hardware runs.

## Capabilities

### New Capabilities

- `portable-vulkan-smoke` provides capability discovery, requirement gating, and a reproducible offscreen correctness run.

### Modified Capabilities

None.

## Impact

Adds the first portable lab executable and report contract under the existing architecture. Implementation starts after M0 closes. PS5 integration depends on the verified operator environment and reviewed artifact linkage.
