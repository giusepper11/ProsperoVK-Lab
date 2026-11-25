## Context

M0 verifies the Linux loader build, the PS5-target object compilation and a pinned public SDK and RADV archive build. Console title integration is subject to M0 closure. Preserve the existing component boundaries and the common CLI runner.

## Decisions

- Build one C++20 workload and result model. Linux uses the system loader selected at process launch. PS5 uses the verified RADV static linkage plus a platform-supplied function resolver and storage/logging path. Validate entry points before use. Link the headers that match the respective Vulkan interface.
- Define the first case as `core.compute.storage-buffer`. Use a Vulkan 1.0 compute pipeline with a single storage-buffer descriptor and one 64-invocation workgroup. Invocation `i` writes `0x12340000 ^ i` into word `1 + i` of a 66-word array. The host initializes guard words at both ends and verifies all values exactly. Compile GLSL to pinned SPIR-V on the build host and record the shader digest.
- Preflight queue flags and count, compute local-size/invocation limits, descriptor and storage-range limits, the chosen buffer's memory-type bits, host visibility, and the case allocation ceiling. Set a provisional 1 MiB ceiling for the one mapped buffer allocation, reducing it if M0 supplies a lower safe target budget. Use a host write/flush where required, a compute-to-host barrier, a five-second fence wait and host invalidation for non-coherent memory. Map and synchronize the allocation with valid alignment.
- Query only valid property and feature structures for the negotiated version and extension path. Use core 1.0 queries for the baseline, use `properties2` and `features2` where available, and identify unavailable inventory sections in the report. Track enumerated support, per-case eligibility, the enabled device configuration, and observed output as separate fields.
- Accept one optional explicit device index, one case ID or inventory-only mode, and a report destination. Persist the case start before submission and flush the terminal record after completion. Record configuration, identifiers, revision, optional reasons, correctness counts and outcome in a versioned JSON contract. Follow the project status definitions. After timeout or device loss, stop submission and route recovery to the platform and operator. A pending resource must not be destroyed while it can still be in use.

## Risks and verification

- Driver-reported support differs across builds. Exercise missing requirements and explicit device choice in runner tests, then validate both coherent and non-coherent paths where supported.
- Console filesystem and error paths must be exercised under the actual launch environment. Capture output retrieval and recovery evidence in the target run.
- Keep external CTS report parsing and performance measurement for their scheduled milestones. The external M0 CTS case supplies independent evidence for the launch path.
