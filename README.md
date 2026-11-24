# ProsperoVK-Lab

An open-source Vulkan validation, benchmarking, and regression testing framework for PlayStation 5, designed to accelerate graphics driver development and optimization.

**Status:** Planning scaffold. No executable, performance baseline, or console compatibility claim exists yet.

## Goals

- Discover and validate Vulkan capabilities, including advertised versus working features.
- Reuse upstream tests before writing new workloads.
- Measure graphics, compute, memory, synchronization, compilation and presentation performance independently.
- Produce reproducible evidence for driver bugs, regressions and optimizations.
- Run shared workloads on Linux and PS5 through the same test contract.

Initial proposed hardware target: PS5 Slim, firmware 13.60, subject to M0 verification. Linux with a Vulkan implementation is the reference host; hardware and driver differences must be recorded.

## Start here

- [AGENTS.md](AGENTS.md): instructions for coding agents.
- [Architecture](docs/ARCHITECTURE.md): component boundaries and execution model.
- [Roadmap](docs/MILESTONES.md): milestones and exit criteria.
- [Benchmark methodology](docs/BENCHMARK_METHODOLOGY.md): measurement and comparison rules.
- [Upstream audit](docs/UPSTREAM.md): candidates and integration gates.
- [Hardware validation](docs/HARDWARE_VALIDATION.md): console safety and evidence.
- [OpenSpec workflow](openspec/README.md): change management.
- [Contributing](CONTRIBUTING.md): how to submit changes.

This is an independent research project, not affiliated with Sony or Khronos. Running selected CTS cases does not constitute Vulkan certification. License selection for original code is pending maintainer approval; do not vendor third-party code until license compatibility is checked.
