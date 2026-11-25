# Hardware validation

M0 target: PS5 Slim, firmware 13.60, with an operator-provided authorized environment. The operator confirmed the Slim model, and Prospero Manager reported the firmware. M0 hardware status is `NOT_RUN`. The [upstream audit](UPSTREAM.md) identifies external console runs on other configurations. [Toolchain evidence](M0_TOOLCHAIN.md) records the local target compilation, archive build and link checks.

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

## M0 console preflight

On 2026-11-24, the connected Prospero Manager returned firmware `13.60` and the generic model label `PS5 (Prospero)`. The operator separately identified the console as a PS5 Slim. The title library returned registered title IDs, with no match for the upstream CTS title `PPSA99015` or a Vulkan test title by name. The check used the dashboard's read-only `GET /api/system/info` and `GET /api/titles` routes. [Dashboard API source](https://github.com/notmaj0r/ProsperoMgr/blob/main/source/frontend/src/lib/api.js), [upstream CTS workflow](https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/docs/CTS.md#L191).

Two intervening retries could not connect to the service. A subsequent check at 23:27 UTC returned HTTP 200 from both routes and confirmed firmware `13.60`. The refreshed catalog contained 23 entries and returned no match for ProsperoVK-Lab, Vulkan, dEQP, CTS or the candidate IDs `PPSA99015` and `PPSA99130`. Title build provenance, launch, Vulkan execution and result retrieval remain open. The Vulkan smoke status is `NOT_RUN`.

## M0 file transfer check

On 2026-11-25, Prospero Manager uploaded the timing review ZIP to the lab's data folder, `/data/prosperovk-lab`. The download from the same folder matched the local ZIP byte for byte. Both copies measured 42,624,959 bytes with SHA-256 `8f0eba9df3c522e77584c7f21a87e3eb5e69a4e9c4454b3f8ec58f1c27f9e177`. This verifies file transfer and retrieval for the review artifact. Console execution remains `NOT_RUN`. [File manager API](https://github.com/notmaj0r/ProsperoMgr/blob/main/source/frontend/src/lib/api.js#L303-L324), [archive evidence](M0_TOOLCHAIN.md#export-the-timing-review-zip).

## M0 operator smoke

The first run is one offscreen Vulkan compute case from the pinned CTS baseline. It uses an existing authorized CTS title with a verified PS5 port, a known RADV archive and an operator-approved launch, writable directory, and recovery path. The title, fork revision and console deployment commands have yet to be supplied for the Slim. Record `NOT_RUN` if one of these prerequisites is missing. The [toolchain page](M0_TOOLCHAIN.md#reproduce-the-sdk-and-release-archive-build) gives the RADV archive build and digest commands.

1. Before transfer, verify the publisher, build manifest and SHA-256 of the launch artifact. Media Player Classic PS5 also uses `PPSA99015`, so confirm the CTS build identity for any catalog match. Record the console model, firmware, environment version, toolchain and SDK revisions, base CTS commit, port revision, compiled external revisions and RADV archive hash and variant. Use a fresh run directory and verify a test file can be written and retrieved through the approved transfer mechanism. Record the actual build, transfer, launch and retrieval commands or UI actions with console identifiers redacted. [Title identity findings](UPSTREAM.md#cts-execution-and-report-ingestion).
2. For the documented upstream CTS title layout, stage the following arguments in `cts/args.txt` in the authorized title's content directory. Confirm from the title manifest that the directory maps to `/app0/cts/` and the build accepts these arguments. Move any prior `cts/TestResults.qpa` into its own run directory before launch so the new run starts with no QPA at that path.

   ```text
   --deqp-case=dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation
   --deqp-log-filename=/app0/cts/TestResults.qpa
   --deqp-archive-dir=/app0/cts
   --deqp-log-flush=disable
   --deqp-log-images=disable
   ```

3. Launch the verified title once with the operator's approved launcher. Capture start, completion and any driver errors from the available title log. Use a 60-second operator observation deadline for this single small case. On device loss, suspected hang or exceeded deadline, stop the run and follow the verified recovery procedure. Preserve any accessible output before trying again in a later run.
4. Retrieve `cts/TestResults.qpa` and the available title log into the run directory. Capture exit status, whether the run ended normally, and timestamps. Keep raw artifacts in operator-controlled storage. Review shared copies for personal data, secrets and device addresses. Record hashes against the exact artifact copies used as evidence, for example `sha256sum TestResults.qpa title.log` when both are present.
5. Require exactly one completed QPA session with the case ID above and upstream `StatusCode="Pass"`, a normal title exit, and no device loss or hang. The CTS case compares a storage-buffer result to expected values. Run the following commands on the host from the retrieved run directory. Set `lab_root` to the lab checkout and `cts_source` to the pinned Khronos CTS checkout from the [Linux reproduction](M0_TOOLCHAIN.md#reproduce-the-single-cts-smoke-on-linux).

   ```bash
   set -eu
   qpa_exit=0
   python3 -B "$lab_root/tools/verify-m0-cts-qpa.py" "$cts_source" TestResults.qpa \
     > qpa-result.json 2> qpa-check.log || qpa_exit=$?
   sha256sum TestResults.qpa qpa-result.json qpa-check.log
   test "$qpa_exit" -eq 0
   ```

   The verifier returns 1 for a complete non-Pass result or a case termination, and records the upstream status, detail and completion flag in JSON. It returns 2 if the report is missing or invalid and records the diagnostic in `qpa-check.log`. Retain raw artifacts and record the title exit and run provenance separately. File the run ID and artifact hashes against [M0 issue #1](https://github.com/giusepper11/ProsperoVK-Lab/issues/1) after evidence review.

This smoke checks launch, bounded Vulkan execution and output retrieval on the exact device. M1 acceptance requires the lab's own versioned report and deterministic smoke on both targets.

## M0 standalone RADV compute check

The standalone fixture adapts the pinned upstream RADV compute workload. It submits one offscreen dispatch and compares 4,096 unsigned integer results against `i * 3 + 7`. Its case ID is `m0.radv.compute`. The build-host checks produced Linux execution evidence, a PS5-target relocatable object and a reproducible pre-packaging ELF. The Khronos CTS smoke retains its own case ID and evidence requirements. [Build-host checks](M0_TOOLCHAIN.md#standalone-radv-compute).

The lab title folder and ZIP have passed [build-host validation](M0_TOOLCHAIN.md#build-the-deployable-m0-title). Slim 13.60 execution remains `NOT_RUN`.

1. Verify the ZIP SHA-256 and confirm `PPSA99743` is free in the local title library and destination. Manually transfer the complete folder to the homebrew environment's title directory (upstream uses `/data/homebrew/PPSA99743/`). Keep `eboot.bin` directly inside that directory. Record the package identity, console model, firmware and launch environment.
2. Launch **ProsperoVK Lab**. The title requests a start notification, journals its build ID, and runs the exact offscreen smoke. A pass enables the bounded timing probe. Observe the result notification and shell exit separately. Use the existing 60-second observation deadline and stop after device loss or a suspected hang.
3. Retrieve the new `run-NNNNNN/` from the transferred title folder. It contains `start.log`, `result.json` and the smoke return code in `exit-code.txt`. Once timing runs it also contains `timing.json` and, on completed capture, `timing-exit-code.txt`. Preserve partial files if the title stopped. The smoke and timing return codes refer to their workloads. Record the externally observed title exit independently.
4. On the host, set `lab_root` to the lab checkout and `run_dir` to the fresh run directory. Verify the captured application artifacts and hash the exact copies under review.

   ```bash
   set -eu
   verify_exit=0
   python3 -B "$lab_root/tools/verify-m0-radv-compute.py" "$run_dir" \
     > "$run_dir/verification.json" 2> "$run_dir/verification.log" || verify_exit=$?
   (cd "$run_dir" && sha256sum result.json start.log exit-code.txt verification.json verification.log)
   test "$verify_exit" -eq 0
   ```

   The verifier returns 0 for one matching start marker, a complete `PASS` with 4,096 checked words and application exit 0. It returns 1 for a reported non-Pass outcome with the expected application exit, and 2 for invalid or incomplete capture. Retain the raw files and the original failure stage and status. Hardware acceptance also requires the verified console and package, a normal exit, and no device loss or hang. Keep hardware status `NOT_RUN` until operator results for the identified target are available.
