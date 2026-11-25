# ProsperoVK-Lab

An open-source Vulkan validation, benchmarking, and regression testing framework for PlayStation 5, designed to accelerate graphics driver development and optimization.

**Status:** M0 audit documented and Linux Vulkan feasibility verified with llvmpipe. The PS5 Slim firmware 13.60 gate remains open. The [M0 compute homebrew folder and ZIP](docs/M0_TOOLCHAIN.md#build-the-deployable-m0-title) passed structural checks on the build host. The portable runner is planned for M1.

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
- [Upstream audit](docs/UPSTREAM.md): pinned sources, reuse decisions and integration gates.
- [Vulkan coverage](docs/VULKAN_COVERAGE.md): test candidates, prerequisites and evidence.
- [M0 toolchain evidence](docs/M0_TOOLCHAIN.md): Linux checks and the pinned PS5 RADV cross-build.
- [Hardware validation](docs/HARDWARE_VALIDATION.md): console safety and evidence.
- [M0 handoff](docs/HANDOFF.md): verified work, reproduction commands and the remaining hardware gate.
- [OpenSpec workflow](openspec/README.md): change management.
- [Contributing](CONTRIBUTING.md): how to submit changes.

This is an independent research project, not affiliated with Sony or Khronos. Running selected CTS cases does not constitute Vulkan certification.

## License

The lab's original work is licensed under the GNU General Public License, version 3 or any later version (`GPL-3.0-or-later`). Third-party work retains its own license and notices. [License text](LICENSE), [upstream provenance](docs/UPSTREAM.md).
