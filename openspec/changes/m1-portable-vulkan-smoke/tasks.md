# Tasks

## 1. Portable runner

- [ ] 1.1 Confirm M0 closure and record the reviewed adapter and build inputs in the change before implementation.
- [ ] 1.2 Implement the CMake target, CLI, case registry and versioned report schema. Verify build and schema validation, and test invalid case IDs, invalid device indices and report errors.
- [ ] 1.3 Implement typed discovery, device selection and exact requirement and enablement reporting. Test missing requirements, unavailable query paths and that preflight skips submit nothing.

## 2. Shared correctness case

- [ ] 2.1 Compile and validate the pinned GLSL shader and implement the offscreen storage-buffer case and CPU oracle. Test exact output, guard corruption, error unwind and non-coherent memory handling.
- [ ] 2.2 Persist the case start and terminal result and stop submissions on timeout or device loss. Verify failure classification and safe resource handling with injected errors.
- [ ] 2.3 Exercise the inventory and case through the installed Linux executable with a selected ICD. Retain the commands and schema-validated report and record missing capability reasons.

## 3. PS5 adapter and integration

- [ ] 3.1 Integrate the M0-verified static RADV linker and public platform interfaces. Verify artifact provenance, entry points, dependency notices and log destination.
- [ ] 3.2 Run the common case and inventory on the Slim after verifying the budget and launch environment. Confirm artifact retrieval, exact readback and schema-valid output. Record the run under M1 acceptance.
