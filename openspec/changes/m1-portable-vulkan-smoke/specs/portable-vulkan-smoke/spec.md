## Purpose

Discover the Vulkan capabilities available to a run and establish portable offscreen correctness with reproducible machine-readable evidence.

## ADDED Requirements

### Requirement: Portable device inventory

The runner SHALL inventory Vulkan instance and device versions, driver and device identifiers, conformance version when available, features, extensions, relevant formats and limits, queues, and memory. The report SHALL record the target, selected device, and the availability of each inventory section.

#### Scenario: Inventory only
- **WHEN** the operator requests inventory on a supported platform
- **THEN** the runner SHALL report the discovered information without executing a workload

#### Scenario: Query path unavailable
- **WHEN** a property query is unavailable on the negotiated Vulkan API and extensions
- **THEN** the affected field or section SHALL carry an explicit availability reason

### Requirement: Requirement gating and enablement

The runner SHALL evaluate each selected case's API, feature, queue, format, limit and resource requirements before issuing case work. The report SHALL distinguish what the driver advertised, what met case prerequisites, what the runner enabled and what execution validated.

#### Scenario: Missing requirement
- **WHEN** an explicit case prerequisite is absent
- **THEN** the case SHALL be `UNSUPPORTED` with the unmet requirement and SHALL issue no workload submission

#### Scenario: Enabled subset
- **WHEN** the runner creates a device for a selected case
- **THEN** the report SHALL identify the API path, extensions, features and queues enabled for the run

### Requirement: Deterministic offscreen compute

The runner SHALL provide `core.compute.storage-buffer` with the same workload and exact integer oracle on Linux and PS5. The case SHALL test all output words and both guard words with bounded resources and a finite completion wait.

#### Scenario: Values and guards match
- **WHEN** the dispatch completes and all CPU readback checks match
- **THEN** the case SHALL report `PASS` with checked-word counts and the shader digest

#### Scenario: Incorrect result
- **WHEN** a value differs or a guard changes after a completed execution
- **THEN** the case SHALL report `FAIL` with the mismatch details and no performance result

### Requirement: Traceable terminal outcomes

The runner SHALL write the start record before workload submission and persist a versioned report containing provenance, case status and relevant details. Invalid inputs and runtime errors SHALL produce a diagnostic. A timeout or device loss SHALL stop further submission.

#### Scenario: Invalid selection
- **WHEN** an invalid or unknown case ID or device index is requested
- **THEN** the command SHALL fail with a diagnostic and SHALL issue no workload submission

#### Scenario: Incomplete wait
- **WHEN** a submitted case times out or loses the device
- **THEN** the result SHALL preserve the start record, record `TIMEOUT` or `ERROR` with the observed cause when writable, and stop further submissions

#### Scenario: Selected case was never started
- **WHEN** a run-level error stops the run before a selected case can be evaluated
- **THEN** the report SHALL identify the case as `NOT_RUN` with the reason
