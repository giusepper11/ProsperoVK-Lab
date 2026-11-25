# Milestones

M0 is in progress. M1–M7 are planned. Each milestone must have an OpenSpec change (or explicit documentation-only exception), tests, artifacts and a reviewable exit gate. Dependencies are listed below. Independent tasks within a milestone may proceed in parallel.

| ID | Outcome | Depends on |
| --- | --- | --- |
| M0 | Upstream and feasibility audit | None |
| M1 | Portable capability inventory and PS5 smoke | M0 |
| M2 | Correctness and upstream workload integration | M1 |
| M3 | Reproducible core microbenchmarks | M2 |
| M4 | Advanced features and presentation | M3 |
| M5 | Regression, recovery and stability harness | M3 |
| M6 | Driver comparison and community homebrew release | M4, M5 |
| M7 | Evidence-led driver improvements | M6 |

## M0: audit and feasibility

- [x] Record upstream revisions, licenses, build entry points, existing tests, and the documented CTS port/report mechanism. Exact port revision and rebuild remain open. [Upstream audit](UPSTREAM.md).
- [x] Map Vulkan features and limits to test candidates, including required, optional and upstream-reported unavailable features. [Coverage matrix](VULKAN_COVERAGE.md).
- [x] Build and structurally validate the complete standalone compute title folder and its deployment ZIP on the host. [Title package and hashes](M0_TOOLCHAIN.md#build-the-deployable-m0-title).
- [ ] Verify title launch, notifications, normal shell exit, Vulkan results and file retrieval on PS5 Slim firmware 13.60. Hardware execution is `NOT_RUN`. [Operator runbook](HARDWARE_VALIDATION.md#m0-standalone-radv-compute-check).
- [x] Document the firmware 13.60 compatibility blocker, device access, resource limits and unresolved interfaces. [Audit risks](UPSTREAM.md#risks-and-outstanding-evidence), [M0 issue](https://github.com/giusepper11/ProsperoVK-Lab/issues/1).
- [x] Record the original-work license and integration choices. [GPL-3.0-or-later](../LICENSE), [upstream audit](UPSTREAM.md), [M1 implementation proposal](../openspec/changes/m1-portable-vulkan-smoke/proposal.md).
- [ ] Review the combined title's integrated components and distribution terms against its final package manifest. The standalone pre-packaging ELF's component inventory is available. [Component review](UPSTREAM.md#standalone-compute-component-review).

The [M0 OpenSpec change](../openspec/changes/m0-upstream-feasibility-audit/proposal.md) remains active. Hardware validation is blocked pending manual launch and artifact retrieval for the Slim on firmware 13.60.

The original Khronos CTS case passed on Linux with the local headless adapter. The focused PS5-target CTS ELF and the standalone RADV smoke ELF linked reproducibly on the build host. The packaged compute title has passed host checks. CTS packaging and hardware execution remain open. [Local CTS build](M0_TOOLCHAIN.md#link-the-focused-cts-executable-for-ps5), [standalone evidence](M0_TOOLCHAIN.md#standalone-radv-compute).

The standalone compute timing probe verified raw host samples, accuracy checks and optional detailed logs in Linux. The same probe produces a reproducible PS5-target ELF with recorded clock and logging imports. The portable runner, GPU timing and PS5 baseline retain their milestone gates. [Linux timing evidence](M0_TOOLCHAIN.md#run-the-homebrew-timing-probe-on-linux), [PS5 build evidence](M0_TOOLCHAIN.md#cross-build-the-homebrew-timing-probe-for-ps5).

The reproducible title review archives cover both the PS5 smoke and timing ELFs with their build, dependency and capture records. The standalone compute deployment package is recorded separately above. [Smoke archive](M0_TOOLCHAIN.md#stage-the-title-review-archive), [timing archive](M0_TOOLCHAIN.md#export-the-timing-review-zip).

Exit: reproducible audit, pinned dependency plan, host build feasibility and console smoke evidence or explicit blocked hardware gate. Do not close M0 until required console feasibility is demonstrated or maintainer changes scope.

## M1: discovery and portable runner
- [ ] CMake host build, minimal CLI, registry, result schema, explicit error statuses, bounded execution and cleanup.
- [ ] Enumerate Vulkan version, driver/device IDs, features, extensions, formats, limits, queues and memory types.
- [ ] Run one deterministic offscreen compute or graphics smoke case with readback.
- [ ] Implement PS5 adapter from verified public APIs; capture firmware, driver revision and report on actual Slim.
Exit: host tests pass, Linux and PS5 reports parse against versioned schema, smoke output matches CPU reference, absent features skip with reason.

## M2: correctness and reuse
- [ ] Integrate selected Khronos samples and existing CTS result/import path, preserving upstream IDs and revision.
- [ ] Add deterministic graphics, compute, format, synchronization and resource lifetime smoke cases.
- [ ] Maintain explicit coverage matrix by requirement, source and test status; record known skips and failures without suppressing them.
Exit: curated cases execute on both targets, CPU/golden checks documented, imported CTS statuses reconcile with source reports, no certification claim.

## M3: core performance
- [ ] Graphics throughput (draw count, instancing, indirect draws, fill rate).
- [ ] Compute throughput (dispatch sizes, arithmetic, atomics and supported subgroups).
- [ ] Memory bandwidth and latency across supported resource/memory types.
- [ ] Pipeline creation/cache, command recording/submission and synchronization overhead.
- [ ] CPU and GPU timing when valid, warm-up, repeated samples, raw measurements, median and tail statistics.
Exit: same workload definitions on both targets, correctness checks pass, reproducible PS5 baseline and repeatability envelope recorded; invalid/missing timings are never zero-filled.

## M4: advanced workloads
- [ ] Mesh/task shader capability checks; compare compute culling + indirect indexed draw, vertex pipeline and mesh path only where supported using equivalent output.
- [ ] Probe ray queries, acceleration structures and ray tracing pipelines independently; add supported cases.
- [ ] Evaluate async compute overlap only where independent queues and valid synchronization exist.
- [ ] Add separate WSI/presentation cases (frame pacing, supported resolution/refresh).
Exit: each category has executed evidence or precise unsupported/blocker reason; identical-output paths validated, graphics-only timings exclude presentation.

## M5: reliability and regression harness
- [ ] Resumable journal, deterministic selection, raw logs, bounded workloads, failure isolation where possible and recovery documentation.
- [ ] Host comparison CLI with configuration checks, statistical thresholds and explicit exclusions.
- [ ] Unit tests and Linux CI for report schema, runner and comparison; hardware runs manual or through a verified dedicated runner.
- [ ] Opt-in stress tests for allocation churn, long-running workloads and repeated submission.
Exit: injected failures are classified correctly, synthetic regressions detected, real console runs survive restart/report retrieval; no unsupported automatic GPU reset claim.

## M6: comparison and release
- [ ] Compare at least two identified PS5 driver builds on the same console/configuration.
- [ ] Publish versioned homebrew packaging, documented commands, limits, compatibility matrix and example anonymized reports.
- [ ] Add interactive console UI if supported; keep CLI/automation behavior identical.
Exit: reproducible build and deployment instructions, two comparable baseline reports, schema-compatible regression report, release review and license/provenance checks.

## M7: driver contributions
- [ ] Rank confirmed bottlenecks and correctness failures by impact, reproducibility and feasibility.
- [ ] Produce minimal reproductions and separate driver patches for selected issues.
- [ ] Verify changes against identical workloads and relevant CTS/smoke cases.
Exit: at least one evidence-backed improvement or a documented negative result/blocker with reproduction and no hidden regressions. Upstream acceptance is not under this project's control.

## Progress policy
Update checkboxes only with links to commits, test evidence or issues. Record blocked gates explicitly. Do not treat a planned milestone, host-only test or unsupported feature as a completed hardware test.
