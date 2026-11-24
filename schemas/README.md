# Run report contract (proposed v1)

Implement a JSON Schema and validation fixtures in M1, before treating reports as stable.

Run manifest: schema version, run ID, UTC start/end, lab commit, build mode, platform and hardware model, firmware (nullable), Vulkan API version, driver name/version/commit (commit nullable with reason), device IDs, enabled features, queue and memory configuration, test profile and source revisions.

Case record: stable test ID, source ID/revision, status (PASS, FAIL, UNSUPPORTED, ERROR, TIMEOUT, NOT_RUN), reason, requirements, workload parameters and seed, correctness result/tolerance, timing method, warm-up count, sample count, raw samples and units, summaries, artifact paths and hashes.

Unknown measurements must be null or omitted with a reason, never fabricated. Failed correctness does not yield valid performance metrics. Report interrupted runs as partial and preserve completed cases. Schema changes require versioning and migration/compatibility tests.
