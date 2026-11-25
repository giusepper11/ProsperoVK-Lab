# Portable run report v1

`run-v1.schema.json` defines both inventory-only and workload reports. Validate a capture with `python3 tools/validate-m1.py REPORT` using Python with the `jsonschema` package (Draft 2020-12). The verifier also reconciles enabled queues and memory with the inventory and checks CPU interval bounds.

Each report and case journal share a run ID. On Linux it is a random 128-bit value. On PS5 it is the fresh title run directory. Each report identifies its target, requested device, lab revision and build ID. The PS5 package manifest binds that ID to the executable, dependencies and input digests. Linux builds derive it from revision, source inputs, validated shader, build mode and compiler configuration. Compare hardware and firmware against the accompanying operator evidence.

`inventory` holds driver-advertised properties, Vulkan 1.0 features, instance and device extensions, compute-related limits, four probed formats, queue families and memory types/heaps. Extended properties include a reason when their query path is unavailable. `requirements` and `eligibility` describe workload prerequisites. `enabled` identifies the actual device configuration. Only a completed workload and its `correctness` record establish an experimental verdict for that workload.

The case journal ends in `.start.json`. A start journal without a valid terminal report records an interrupted capture. The report writer reserves a new destination before dispatch and never replaces existing evidence. `UNSUPPORTED` identifies an unmet prerequisite before submission. `NOT_RUN` records an earlier run-level failure. A failed oracle produces `FAIL`. A Vulkan error including device loss produces `ERROR`, and an expired fence wait produces `TIMEOUT`.

Passing correctness reports retain one steady-clock observation with CPU submit, wait and submit-to-completion intervals in nanoseconds. GPU duration is null with a reason. Queue timestamp bits and timestamp period record advertised capabilities. Repeated measurements and comparisons are outside M1. New cases or incompatible record changes require corresponding schema and validation fixtures.
