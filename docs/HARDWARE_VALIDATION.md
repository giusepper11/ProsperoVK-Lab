# Hardware validation

M0 target: PS5 Slim, firmware 13.60, with an operator-provided authorized environment. The operator confirmed the Slim model, and Prospero Manager reported the firmware. The standalone hardware smoke and CPU timing capture passed. The hardened compute title also completed and returned to the shell. The [focused CTS run](#focused-cts-result) passed independently. [Verified baseline](#first-verified-slim-baseline). The [upstream audit](UPSTREAM.md) identifies external console runs on other configurations. [Toolchain evidence](M0_TOOLCHAIN.md) records the local target compilation, archive build and link checks.

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

Two intervening retries could not connect to the service. A subsequent check at 23:27 UTC returned HTTP 200 from both routes and confirmed firmware `13.60`. The refreshed catalog contained 23 entries and returned no match for ProsperoVK-Lab, Vulkan, dEQP, CTS or the candidate IDs `PPSA99015` and `PPSA99130`. At this preflight the Vulkan smoke was `NOT_RUN`.

## M0 file transfer check

On 2026-11-25, Prospero Manager uploaded the timing review ZIP to the lab's data folder, `/data/prosperovk-lab`. The download from the same folder matched the local ZIP byte for byte. Both copies measured 42,624,959 bytes with SHA-256 `8f0eba9df3c522e77584c7f21a87e3eb5e69a4e9c4454b3f8ec58f1c27f9e177`. This verifies file transfer and retrieval for the review artifact. At this transfer check console execution was `NOT_RUN`. [File manager API](https://github.com/notmaj0r/ProsperoMgr/blob/main/source/frontend/src/lib/api.js#L303-L324), [archive evidence](M0_TOOLCHAIN.md#export-the-timing-review-zip).

## M0 operator smoke

The accepted local package has its own [focused CTS run procedure](HARNESS.md#focused-cts-title). The original external-title procedure below documents the upstream alternative. It uses an existing authorized CTS title with a verified PS5 port, a known RADV archive and an operator-approved launch, writable directory, and recovery path. The title, fork revision and console deployment commands have yet to be supplied for the Slim. Record `NOT_RUN` if one of these prerequisites is missing. The [toolchain page](M0_TOOLCHAIN.md#reproduce-the-sdk-and-release-archive-build) gives the RADV archive build and digest commands.

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

The lab title folder and ZIP have passed [build-host validation](M0_TOOLCHAIN.md#build-the-deployable-m0-title). The first Slim run is recorded [below](#first-verified-slim-baseline).

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

## First verified Slim baseline

On 2026-11-25 the operator launched PPSA99743 on PS5 Slim, firmware 13.60. Run `run-000001` identifies build `c0c28392ddd5b8b62d9074a1b4eb27563bc8191a28198c25c9151dcae2f8a003`. A separate readback through Prospero Manager matched all 21 deployed files to the host-validated folder. A second retrieval of all five run artifacts matched the original capture byte for byte.

| State | Evidence for this build |
| --- | --- |
| BUILD / PACKAGE | PASS. ZIP SHA-256 `072c62478a1292f1bd7b9fe96a6092aa909cbb5d7e70945926560ff2acecb87f`, verified embedded identity, runtime and executable. |
| DEPLOY | PASS. Live readback matched the folder. |
| EXECUTE | PASS. Journal and both result/return-code pairs retrieved from the identified console. |
| CORRECTNESS | PASS. The shared oracle checks all 4,096 words against unsigned `3*i+7`; the smoke reported 4,096 checked and returned 0. Only the verdict and count are persisted. |
| PERFORMANCE | PASS for CPU timing capture. Five warm-ups and 30 measured samples after initial validation. Timing workload returned 0. |
| SHELL_EXIT | UNCONFIRMED. The saved filtered klog was empty. On recheck, Prospero Manager reported its klog disconnected with zero lines. Its ordinary log held 107 lines with no match for this title. The upstream hook flushes a message before requesting asynchronous shell closure. Both workload code files are written before that hook. |

Pinned PS5_Mesa `1ba9874f478657ccf6da72ce55f0260164cc0bd0`, release RADV archive `d06eaf176b42fda32b740a660f343c1e72167cb11a6f6965669ba23437bdf441`. Vulkan driver version field 109060096, API version field 4211042, queue family 0, memory type 2, flags 6. Each dispatch writes 64 groups × 64 invocations to 16 KiB. The timing probe verifies fresh readback for each dispatch. Host steady-clock nanoseconds, median and nearest-rank p95 recalculated from all samples:

| CPU interval | Median (µs) | p95 (µs) |
| --- | ---: | ---: |
| Queue submission | 15.075 | 16.358 |
| Fence wait | 8.580 | 14.834 |
| Submission to observed completion | 24.617 | 30.872 |

The probe did not measure Vulkan timestamps. GPU duration is null; GPU timestamp support remains untested. This single run establishes a baseline for this build and workload. Raw report SHA-256 values are `6b4fc0ce65d80a9302781e6f37db0d2add2fa31cb7d1b4e069fac3792985bb2c` (smoke), `b1df15d1b265c8b1bc2181ab2a1aa3df3c56d27a8a20724e0eff892e8381a7da` (timing), `5c14906f0a02ebab39a9ad5b652da67721636c0cfefc421db9ce8e95513dc83b` (journal), and `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` (each return code). See [harness commands](HARNESS.md#transfer-and-evidence) for verification.

## Final acceptance session

On 2026-11-25 the Manager reported firmware 13.60. Before transfer, PPSA99744 was absent from both the catalog and the homebrew directory. PPSA99743 was present in both. A fresh readback of the original installation matched its verified package. The Manager kernel log returned disconnected with zero lines. The ordinary log contained 107 entries and no kernel-log connection diagnostic. The Manager UI describes its kernel feed as a client of a running klogsrv. The available log interface exposes list and clear operations. This check could not distinguish an absent producer from a disconnected client. Shell exit therefore needs an independent operator observation or shell event for each title.

With separate operator approval for replacement and execution, the host verified all 30 files in the original installation, including the five run artifacts, and saved a complete local and console backup. The transfer staged the exact hardened package, copied the existing run directory forward, verified the staged files, moved the original folder to the backup and verified published files at PPSA99743. The local copy is `build/m0-final-acceptance/original-installation/`; the console backup path is recorded locally in `build/m0-final-acceptance/replacement.json`.

### Hardened compute result

PPSA99743, lab revision `163910f24a9c139fd76815be93e802a26a2ec65c`, build ID `da688570b93fec17a9dd851173c9cdfb883aa3f1a64629e971609c88391d1902`, ZIP SHA-256 `913d6ebd6b828c8a550c52b6fa3bceaf4650aa132cdb9f7ab91e3f0694b54c31`. The operator launched **ProsperoVK Lab** once. The host retrieved `run-000002` from the verified installation.

| Gate | Evidence |
| --- | --- |
| BUILD / PACKAGE | PASS. Both preserved hardened packages passed structural inspection and matched byte for byte. |
| DEPLOY | PASS. Readback matched the published folder. |
| EXECUTE / CORRECTNESS | PASS. The journal matches the build. All 4,096 words passed and both workload return codes were zero. |
| PERFORMANCE | PASS for CPU capture. Five warm-ups, 30 measured samples. Median / p95 in nanoseconds were 15,196 / 17,160 for submission, 8,700 / 10,024 for fence wait and 24,937.5 / 28,145 for submission to observed completion. GPU duration remains unmeasured. |
| SHELL_EXIT | PASS by operator observation. A notification was visible too briefly to transcribe. The home screen returned automatically within 60 seconds without a crash dialog or manual close. Both title-filtered Manager logs were empty. |

Local evidence is in `build/m0-final-acceptance/hardened/run-000002/`. Journal SHA-256 `4cbebf8a6506f0c647c41abe3e8c783e9ea8fe1830baf8422c6c04e8a3e553c0`, result `6b4fc0ce65d80a9302781e6f37db0d2add2fa31cb7d1b4e069fac3792985bb2c`, timing `a252638ce96a3e88c783ceec7f0b5b8a27ed28411cec247a74b408558392fb8d`. Both return-code hashes match the original baseline. The original run retains its own shell-exit status.

### Focused CTS result

On the same Slim the operator authorized a separate deployment and one launch of **ProsperoVK Lab CTS**, PPSA99744. The deployed artifact is the [35-file CTS build](M0_TOOLCHAIN.md#focused-cts-deployment-package) at lab commit `86386bd88d494c433cbc599ad3c75269a35a8995`. The original hardware QPA is preserved at `build/m0-final-acceptance/cts-evidence/run-000001/TestResults.qpa` (5,534 bytes). This run number belongs to PPSA99744.

| Gate | Evidence |
| --- | --- |
| BUILD / PACKAGE | PASS. Build ID `1b3e7351ff45de07319c00871048eb9b49ac2a1692c0a1c98277ea4274cb910d`, ZIP SHA-256 `f58f3c665bdc159165e211b3c2c0c957af813cc1dfd06093344c9e90ad540bf5`. |
| DEPLOY | PASS. The harness validated the stage and read back all 35 published files. Manager subsequently listed PPSA99744. |
| EXECUTE | PASS. Fresh journal identifies the deployed title, build and case. The upstream runner returned zero. The QPA identifies `PlayStation 5 GPU (RADV NAVI21)`, vendor 0x1002 and device 0x0. |
| CORRECTNESS | PASS. One complete session and one complete `dEQP-VK.compute.pipeline.basic.copy_ssbo_single_invocation` case. The pinned parser reported `Pass`, detail `Compute succeeded`. QPA SHA-256 `c408bdcaf63548753a5f892c778c6c6de28f81614c8f2ac34e23ce3e12a69760`. |
| PERFORMANCE | NOT_RUN. This case supplies a correctness verdict. |
| SHELL_EXIT | PASS. The title log recorded the request to close after the runner returned zero. The operator separately observed normal automatic closure. |

The title log reports 1/1 passed and two RADV diagnostics about invalid PCI bus information for device UUID computation. The kernel feed remained disconnected; neither Manager log yielded title-specific lines. Title log SHA-256 `6011b0f260cbf4b2d573d5988f2898e090841f1a34e68c0a2970fa72b35f6013`, journal `c39275cea7bae19d0ef71633f4b1ada8f4ec461a0ed535ba26f8b30820efe369`, return code `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`. Raw files remain in the ignored evidence directory.

```bash
source /tmp/prosperovk-harness-env.sh
export CTS="$PWD/build/m0-cts/source"
app=build/m0-final-acceptance/cts/title/dist/PPSA99744
run=build/m0-final-acceptance/cts-evidence/run-000001
tools/m0 deploy "$app" "$PS5_HOST"
# Operator launches PPSA99744 once and observes shell exit.
tools/m0 retrieve "$PS5_HOST" run-000001 "$run" --app "$app"
tools/m0 accept "$app" "$run"
python3 -B tools/verify-m0-cts-qpa.py "$CTS" "$run/TestResults.qpa"
```

## M1 portable runner

PPSA99745 is the primary M1 lab title. The intended target is the PS5 Slim used for M0. Record the observed firmware again for M1. Use the [M1 harness](HARNESS.md#m1-portable-runner) for the checked package, authorized deployment, separate launch and matching report retrieval.

| Gate | M1 evidence |
| --- | --- |
| BUILD | PASS on the build host, using the public SDK and pinned static RADV build |
| PACKAGE | PASS on the build host, complete title and matching ZIP structurally verified |
| DEPLOY | NOT_RUN |
| EXECUTE | NOT_RUN |
| CORRECTNESS | NOT_RUN on Slim |
| PERFORMANCE | NOT_RUN |
| SHELL_EXIT | NOT_RUN |

The Slim exit gate remains open. The M0 results above belong to their original titles and builds.
