# Milestones

All milestones are planned. No dates or hardware results are assumed. Each milestone must have an OpenSpec change (or explicit documentation-only exception), tests, artifacts and a reviewable exit gate. Dependencies are listed below; independent tasks within a milestone may proceed in parallel.

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
- [ ] Record upstream revisions, licenses, build entry points, existing tests, and actual CTS port/report mechanism.
- [ ] Map Vulkan features and limits to test candidates; distinguish mandatory, optional and unavailable.
- [ ] Verify SDK/toolchain and packaging from public sources. Determine Linux and console run/log retrieval commands, with a minimal console smoke experiment where feasible.
- [ ] Document firmware 13.60 compatibility evidence or blocker, device access, resource limits and unresolved interfaces.
- [ ] Decide original-code license with maintainer; record integration choices and first OpenSpec implementation proposal.
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
