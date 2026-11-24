# OpenSpec workflow

M0 initialized the repo-local, `spec-driven` structure with OpenSpec 1.14.0.

```bash
openspec --version
OPENSPEC_TELEMETRY=0 openspec init --tools none --no-animation .
OPENSPEC_TELEMETRY=0 openspec validate --all --strict
```

Use one focused change per deliverable. Capture proposal, design where applicable, specification deltas and acceptance tasks. Verify against the milestone and actual target. Archive only after implementation and evidence are reviewed. Keep the current accepted behavior in specs/; active changes in changes/. Do not create duplicate planning documents when an accepted specification is sufficient.

- [M0 feasibility audit](changes/m0-upstream-feasibility-audit/proposal.md) records the audit and keeps the remaining gates open.
- [M0 standalone RADV compute check](changes/m0-radv-compute-smoke/proposal.md) tracks the bounded Vulkan workload and its build and runtime evidence.
- [M1 portable Vulkan smoke](changes/m1-portable-vulkan-smoke/proposal.md) is the proposed implementation contract. It depends on M0.
