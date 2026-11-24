# Hardware validation

Target proposal: retail PS5 Slim, firmware 13.60, with a user-provided working homebrew environment. Compatibility is unverified.

## Runbook
1. Verify platform adapter, public toolchain, binary hash, driver revision, deployment method and documented recovery procedure on the actual device.
2. Confirm user consent for experimental GPU workloads. Start with capability inventory and bounded smoke tests; use conservative memory budgets derived from verified availability.
3. Record model, firmware, environment, driver build/commit, lab commit, test configuration and run ID.
4. Journal each case before submitting GPU work and flush completed results to writable user-controlled storage. Do not modify system files.
5. Bound CPU waits and workload size. A timeout is evidence of incomplete work, not proof that the GPU has stopped. On device loss/hang, stop submitting, preserve logs if safe, and follow the documented operator recovery process.
6. Retrieve artifacts using the verified transfer mechanism; redact addresses and device-specific secrets before sharing.
7. Run opt-in stress cases only after smoke tests and recovery path are validated.

Record execution target (Linux hardware, Linux software, PS5 hardware), commands, outcome, artifact hashes and limitations. CI without a console cannot satisfy a hardware gate. Do not fabricate timestamps, GPU counters, firmware support or performance results.

No firmware modification, persistence, privileged diagnostics, proprietary SDK artifacts or automatic reset assumptions are required for the lab's initial scope.
