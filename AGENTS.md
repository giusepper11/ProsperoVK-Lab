# Agent instructions

## Mission
Build a reproducible Vulkan driver validation and performance laboratory for PS5, not a game engine or a replacement Vulkan driver.

## Source authority
1. The user's explicit requirements and accepted OpenSpec changes.
2. Repository architecture, milestone acceptance criteria and benchmark methodology.
3. Pinned upstream source, Vulkan specification and reproducible evidence.
Resolve conflicts explicitly; do not silently change architecture or declare unsupported capabilities.

## Execution
- Read README.md, docs/ARCHITECTURE.md, docs/MILESTONES.md and the active OpenSpec change before editing.
- Start with M0. Do not skip dependencies or implement speculative PS5 interfaces.
- Use OpenSpec for nontrivial changes: proposal, design where needed, spec deltas, tasks, implementation, verification and archive. Follow installed tool syntax; do not fabricate tool output.
- Prefer the smallest working vertical slice. Keep Linux and PS5 test semantics shared; isolate platform and driver integration.
- Use C++ and CMake as provisional defaults, subject to M0 toolchain verification. Prefer standard Vulkan entry points, explicit resource ownership, checked VkResult values and deterministic cleanup.
- Reuse verified upstream workloads with documented provenance, license and pinned revision. No proprietary SDK, leaked code, decrypted firmware artifacts, keys or copyrighted game assets.
- Do not modify the driver inside this repository. Submit separate upstream changes with minimal reproductions and before/after evidence.
- Never force unsupported features or bypass capability checks. Do not change console firmware or persistent system settings.
- Default to bounded, offscreen, low-risk workloads. Hardware stress or experimental paths require explicit opt-in; stop after device loss or a hang.
- Do not commit credentials, console addresses, personal data, raw dumps or generated result bundles.
- No simulated or host-only result may be represented as hardware evidence.

## Verification and definition of done
- Add tests for feature gating, invalid inputs, error handling and cleanup where applicable.
- Run relevant builds/tests on available targets; report exact commands, revisions, results and blockers.
- Verify correctness before timing. Follow docs/BENCHMARK_METHODOLOGY.md.
- Record hardware validation separately from Linux/CI; if unavailable, mark NOT_RUN and keep hardware acceptance criteria open.
- Preserve raw measurements and test status, distinguish failure from unsupported and not run.
- Update docs/specs and milestone status only with evidence. Do not mark a milestone complete if an exit gate is unmet.
- Keep changes focused, reviewable and reversible. Never claim performance improvement from incomparable workloads.

## PS5 artifact acceptance
- Use `tools/m0 package NEW_OUT` for every change that affects PS5 execution. Require the complete title folder and validated ZIP. ELF and review outputs are intermediate evidence.
- Follow [the harness contract](docs/HARNESS.md) for dependencies, package verification, authorized deployment and run retrieval. Track BUILD, PACKAGE, DEPLOY, EXECUTE, CORRECTNESS, PERFORMANCE and SHELL_EXIT per build and target.
- Build and package on the host when hardware is unavailable. Obtain authorization for deployment and execution separately. Verify the retrieved journal against the deployed manifest before recording hardware results.
