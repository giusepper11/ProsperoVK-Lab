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

#### Scenario: Captured compute result
- **WHEN** both fixture streams and the process exit code are available
- **THEN** the host verifier checks one start marker, one terminal result and a consistent exit code for a pass, and records the hashes of the captured inputs. Console provenance and recovery observations remain part of the hardware run record.
