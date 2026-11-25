## Purpose

Provide a bounded, portable compute correctness check for RADV feasibility and retain a verifiable outcome for each attempted run.

## ADDED Requirements

### Requirement: Exact compute readback

The fixture SHALL make one offscreen Vulkan 1.0 dispatch using 64 groups of 64 invocations. It SHALL compare all 4,096 output words against the unsigned integer expression `i * 3 + 7` and report its outcome as one terminal JSON record with case ID `m0.radv.compute`. The process SHALL return success only for `PASS`.

#### Scenario: Correct output
- **WHEN** the dispatch completes and every output word equals its expected value
- **THEN** the fixture reports `PASS` and 4,096 checked words.

#### Scenario: Incorrect output
- **WHEN** completion succeeds and any output word differs from the oracle
- **THEN** the fixture reports `FAIL` and an output mismatch.

### Requirement: Capability and failure handling

The fixture SHALL check queue, limit and memory prerequisites before submission. It SHALL use a finite fence wait and stop GPU work after device loss or a failed completion wait. It SHALL emit a start marker before GPU work for capture by the run harness.

#### Scenario: Required capability is absent
- **WHEN** discovery establishes that a required queue, limit or memory type is unavailable
- **THEN** the fixture reports `UNSUPPORTED` with the missing requirement before submitting work.

#### Scenario: A Vulkan operation fails
- **WHEN** a required entry point is missing or an operation returns an unexpected error
- **THEN** the fixture reports `ERROR` with the failed stage and any applicable Vulkan result.

#### Scenario: Fence deadline expires
- **WHEN** the fence wait returns `VK_TIMEOUT`
- **THEN** the fixture reports `TIMEOUT` and exits without further submission or resource destruction that assumes completion.

### Requirement: Target-specific evidence

The same shader and oracle SHALL be used on both targets. Hardware acceptance SHALL require the identified console, a verified title build and a recorded terminal result from that target.

#### Scenario: Linux software execution
- **WHEN** the fixture passes with the Linux software Vulkan driver
- **THEN** its result is recorded as Linux software execution evidence.

#### Scenario: PS5-target build evidence
- **WHEN** the PS5-target objects compile and link into a relocatable with the pinned RADV archive
- **THEN** the artifact identity, inputs and unresolved imports are recorded as build-host evidence, with hardware execution `NOT_RUN` until a verified title runs on the console.

#### Scenario: Pre-packaging component evidence
- **WHEN** the build-host check links the pre-packaging ELF
- **THEN** its hash manifest includes the section map, archive extraction table, dynamic library declarations and matching public stub exports used to review component provenance.

#### Scenario: Local title review archive
- **WHEN** both PS5 link records verify and reference the same cross-build, and their executable and path-independent reports agree
- **THEN** the review tool produces a reproducible archive with the display name and stable internal app UUID, original executable, workload and build identities, linked components, report capture contract and integrity checks. It records console validation as `NOT_RUN` and leaves the console title ID, packaging and launch unassigned.

#### Scenario: Inconsistent review inputs
- **WHEN** a required checksum differs or the link records identify different builds
- **THEN** the review tool rejects the inputs without publishing an archive.

#### Scenario: Local timing review archive
- **WHEN** the verified cross-build manifest identifies the timing entry source
- **THEN** the archived ELF and build records identify the timing variant, its report version and optional verbose flag. The archive does not include the single-dispatch report verifier.

#### Scenario: Captured compute result
- **WHEN** both fixture streams and the process exit code are available
- **THEN** the host verifier checks one start marker, one terminal result and a consistent exit code for a pass, and records the hashes of the captured inputs. Console provenance and recovery observations remain part of the hardware run record.

### Requirement: Host timing feasibility

The timing probe SHALL validate one dispatch before timing, perform five warm-ups and record 30 measured dispatches using the same shader, pipeline and command buffer. It SHALL verify fresh exact readback for each dispatch. It SHALL report individual host submission and fence wait durations in nanoseconds, their statistics, the compile target and the selected device and workload parameters. It SHALL represent GPU timing as unavailable.

#### Scenario: All dispatches pass
- **WHEN** every dispatch completes and matches the oracle
- **THEN** the probe provides all timing samples, a median and nearest-rank p95, with its target in the report.

#### Scenario: Probe cannot complete or validate a dispatch
- **WHEN** discovery, submission, a fence wait or exact readback fails
- **THEN** the probe exits with the corresponding status and produces no passing timing report.

#### Scenario: Verbose diagnostics enabled
- **WHEN** verbose mode is requested
- **THEN** the probe logs the phase and index of each completed, validated dispatch on standard error outside the timed intervals.

#### Scenario: PS5 timing build requested
- **WHEN** the cross-build selects the timing probe
- **THEN** it uses the shared timing workload and the PS5 RADV resolver, and records build-host evidence for the pre-packaging ELF and its runtime imports. Console execution remains `NOT_RUN` until a verified title runs on the target.
