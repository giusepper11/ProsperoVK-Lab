# Benchmark methodology

## Correctness before performance
Use deterministic inputs, seeds, CPU reference or justified golden output. Compare integer results exactly and floating-point/image results with test-specific tolerances declared before the run. Detect NaN/Inf where invalid. Check resource guards and cleanup. Report the tolerance and observed error. Never time a failed workload as a passing result.

## Measurement
- Default offscreen; measure presentation separately. Record resolution, work size, shader hashes, formats, pipeline state, memory type and queue configuration.
- Separate setup, pipeline compilation, CPU command recording, CPU submission, end-to-end and GPU execution times. Do not conflate fence wait with GPU execution time.
- Use Vulkan timestamps only when supported on the selected queue, honoring timestampValidBits, timestampPeriod, wraparound, query availability and synchronization rules. Otherwise report GPU time as unavailable; label CPU timing as CPU.
- Warm up and repeat. Initial proposed defaults: 5 warm-up iterations, 30 measured samples, 3 independent runs for regression evidence. Tune per workload and record actual counts, duration and rationale.
- Record individual samples, median, p95, min/max and variation. Define percentile algorithm in implementation; retain raw samples. Use consistent units (ns, bytes, operations) and explicit throughput formulas.
- Separate cold and warm pipeline caches. Record cache policy and whether validation layers or debug builds were enabled.
- Control background load and record thermal/power information when observable; never invent counters or temperatures. No VSync cap in offscreen tests.

## Comparison
Use the same console, firmware, workload revision/configuration, build mode and measurement path for driver A/B. Record driver revisions separately. Reject incompatible comparisons instead of silently normalizing. Cross-device correctness comparison is useful; cross-device performance is contextual, not a regression gate. Interleave runs where practical and report run-to-run noise. Provisional flag: median degradation over 5% AND greater than measured noise; confirm with independent repetitions before declaring a regression. Adjust thresholds per suite with rationale.

## Evidence
Store versioned run manifest, per-test status, raw timing samples, correctness metrics, failure reason, optional images/logs and hashes. Use null/absent metrics for unavailable data, not zero. Record test source revision and machine configuration; redact personal data. Report coverage against the pinned Vulkan spec and selected CTS profile, not against an unspecified total. Preserve unsupported and not-run denominators separately.
