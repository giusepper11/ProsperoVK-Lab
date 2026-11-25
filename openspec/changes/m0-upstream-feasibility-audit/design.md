## Context

The initial project contains an architecture and acceptance criteria. M0 needs source evidence and a small toolchain experiment before the first runtime change can start.

## Decisions

- Use the existing upstream register for source revisions, licenses, CTS mechanics and reuse decisions. Link separate coverage and toolchain evidence from the register.
- Use pinned upstream files and observed Git references for source evidence. Preserve the difference between a published upstream run, a local Linux run and an observation on the requested console.
- Isolate the temporary Linux CMake experiment in a fixture. Compile a shader and check SPIR-V separately from the Vulkan loader and device exercise. A single empty submission with a bounded wait proves the basic link and submission path independently of workload code.
- Exercise the selected PS5 smoke case first on Linux with the pinned, unmodified upstream CTS runner. Use the upstream QPA parser for the status and detail. Require one ordered session and one matching case in the raw QPA and confirm the XML case identity. Retain the raw log and digest. Record a terminated case as terminated even if its status text says Pass. Record Linux execution as software-ICD evidence.
- Compile the fixture as a PS5-target object against public SDK headers. An actual launch gate requires a verified title and a matching Slim environment. Use one authorized external CTS case for that gate if the build can be identified and its artifacts retrieved.
- Verify the CTS resolver reference and archive selection through a relocatable link against the pinned RADV and SDK libraries. Record unresolved imports and keep final title linkage as a target gate.
- Use the stock CTS headless CMake entry point and its platform source override to exercise a local headless adapter. Point CTS's Vulkan entry point at the Linux loader on the host and at the linked RADV ICD for PS5. Keep CTS's application runner, basic compute case factory, memory defaults and QPA writer. Use a focused registration for the native link and select the original case through the CTS case filter. Verify that focused build on Linux. Treat target objects and link artifacts as build-host evidence until a supported title can launch.

## Risks and verification

- The reported PS5 CTS fork could not be resolved. Preserve the published test mechanism, and require an exact port and build manifest before using a run as local hardware evidence.
- GPU access, SDK linkage and firmware 13.60 compatibility remain open. Use the existing hardware runbook and the single-case profile to establish those gates.
- Keep this change active until the required console evidence and combined-title inputs are reviewed.
