# Design

## Context

The pinned PS5 RADV archive and SDK are available as local build inputs. The documented PS5 CTS fork and a deployable title remain unavailable. The console management preflight confirmed firmware 13.60.

## Decisions

- Adapt the compute stage and integer oracle from PS5_Vulkan revision `7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc`. Retain the upstream GPU work shape and validate each word on the host. [Upstream test](https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/radv/radv_smoke.c#L442), [upstream shader](https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/radv/shaders/smoke.comp).
- Keep the program and shader portable under the M0 test fixtures. Pass the Linux Vulkan loader or the PS5 RADV resolver through a small platform entry point. Use one storage buffer, one compute queue and base Vulkan 1.0 synchronization. Check host-visible memory compatibility and handle noncoherent memory where applicable.
- Generate SPIR-V from the shared GLSL source with the host compiler. Check the shader and capture origin and hashes in the build evidence.
- Print a start marker on standard error and one terminal JSON record on standard output. Capture both streams and the exit code outside the fixture. Use a host verifier to check the matching records and preserve the stream digests. The launcher owns process-level stop and recovery after a hang.
- Use the pinned SDK and whole RADV archive to check PS5-target relocatable linkage and enumerate remaining imports. Reuse the pinned public application startup and AGC link stubs for a strict build-host ELF link. Record its dynamic imports and required libraries for runtime verification. The final title, packaging and launch require a verified deployment environment.
- Save LLD's section map and archive extraction table from the pre-packaging link, alongside the ELF and dynamic table in the same hash manifest. Use the archive table to report extracted members and the section map to trace their output contributions. Use the dynamic table to identify imported libraries. Review the final package's component, asset and notice manifest once available.
- Match the ELF's dynamic imports to exports of the public link stubs whose SONAME appears in `DT_NEEDED`. Keep all matching candidates and record each import's binding. Use this inventory when reviewing runtime provider evidence for the final package.
- For the RADV source review, reassemble the staged archive from its ordered Ninja object list and record each member's compilation input. Replay the two OpenCL code generators into a fresh evidence directory and compare the generated outputs with the ones from the pinned build.

## Verification

Use llvmpipe for a positive execution test and an unavailable ICD for a host failure-path test. Check the exact result and process status. Match the pre-packaging ELFs byte for byte across two independent links and verify the recorded source and artifact hashes. Preserve the Linux commands, shader identity and PS5-target linkage evidence in the ignored build tree. Track console execution separately under the hardware runbook.
