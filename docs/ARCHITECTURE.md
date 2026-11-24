# Architecture

Status: proposed design, not an implemented system. M0 must validate platform assumptions before they become commitments.

## Boundaries

```text
CLI / later console UI
          |
     suite runner -------- report writer / host comparison
          |
  capability inventory + test registry + result validation
          |
   workload adapters (native / upstream samples / CTS bridge)
          |
  Vulkan dispatch + resource and timing helpers
          |
  platform adapter (Linux | PS5)
          |
  selected Vulkan implementation / GPU
```

| Component | Responsibility |
| --- | --- |
| core | Stable test IDs, registry, requirements, configuration, lifecycle and result types. No PS5-specific API. |
| vulkan | Instance/device discovery, queue selection, resource ownership, feature gating, timestamps and debug hooks. |
| platform/linux | Host process, loader, filesystem, timers and optional presentation. |
| platform/ps5 | Verified public homebrew initialization, loader/linkage, filesystem, logs and presentation where available. |
| suites | Deterministic graphics, compute, memory, synchronization and pipeline workloads. |
| adapters | Thin wrappers for pinned upstream samples and CTS results; retain original test identities. |
| reporting | Versioned machine-readable reports, artifact references and comparison tools. |
| app | CLI first, interactive UI later; same runner and results. |

Proposed source layout (directories are created when implemented):

```text
src/{core,vulkan,platform,app}/
suites/{graphics,compute,memory,sync,pipeline,presentation,advanced}/
adapters/{cts,samples}/
tests/{unit,integration,fixtures}/
tools/   # host runner, comparisons, report validation
schemas/ # versioned run contracts
docs/
openspec/
```

## Runtime contract

Discover device properties and advertised extensions/features/limits; distinguish enabled features from advertised features. Test descriptors declare required API, features, queue properties, formats and limits, resource budgets and risk tier. The runner evaluates requirements before setup, then performs setup, correctness validation, warm-up, measured iterations, post-validation and teardown. Persist per-case completion and journal start before GPU work. Abort the run after device loss or suspected GPU hang; never assume a host timeout can cancel GPU work.

The proposed test statuses are PASS, FAIL, UNSUPPORTED, ERROR, TIMEOUT, NOT_RUN. A correctness failure invalidates performance evidence. Unsupported must include a precise unmet requirement; an advertised feature that fails a valid workload is not unsupported.

## Portability
Linux establishes functional reference and runner CI. Compare correctness across devices, but performance regression gates require comparable hardware/configuration. Software Vulkan is a functional smoke target, not a PS5 performance baseline. Do not assume PS5 WSI, dynamic loading, debug callbacks, GPU timestamps, asynchronous queues or performance counters; probe availability and document alternatives. Offscreen workloads must not require a swapchain.

## Integration strategy
Audit the existing PS5 Vulkan template, driver, Mesa port and CTS integration first. Prefer adapting the public template and importing existing CTS reports rather than duplicating its port. Preserve third-party source identity and license notices. Do not mix driver changes with benchmark changes.

## Open decisions (M0)
Exact compiler/toolchain, Vulkan loader and driver linkage, executable packaging, CTS integration method, dependency pinning and license, available timer/WSI/telemetry interfaces, safe resource ceilings, physical console transfer/recovery workflow. No public API or support claim is final before evidence.
