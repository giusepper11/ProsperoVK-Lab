# focused-cts-title Specification

## Purpose

Validate the original focused Khronos CTS case on the identified PS5 build and retain its raw hardware result.

## Requirements

### Requirement: Identified CTS deployment artifact

The M0 harness SHALL package the pinned focused Khronos runner in a separate title with executable, runtime, metadata, notices and a manifest that binds the workload inputs to the embedded identity.

#### Scenario: Host package verification
- **WHEN** the staged title and archive pass native and file inventory checks
- **THEN** the harness records the package digest and build identity and leaves console execution pending.

### Requirement: Single-case hardware evidence

The lab SHALL retain the original QPA and require a matching build and title journal, complete single-case QPA, successful CTS return and independent normal shell exit observation for a passing hardware run.

#### Scenario: Incomplete capture
- **WHEN** a returned run lacks a complete session or has a different build identity
- **THEN** the hardware acceptance gate remains open and the retrieved evidence is preserved.

#### Scenario: Occupied destination
- **WHEN** the candidate title ID is present in the catalog or destination
- **THEN** the harness refuses deployment before publishing the title folder.
