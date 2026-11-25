# M0 title harness

`tools/m0 package NEW_OUT` builds the timing-enabled shared compute object from source, links the final title with the pinned template recipe, stages its runtime, icon and notices, and inspects both the folder and ZIP. Run it from a clean checkout using a fresh writable output directory. Build and validation are offline once the public dependencies are staged. No console is needed.

## Inputs

Export absolute paths in your shell. The [toolchain procedure](M0_TOOLCHAIN.md#reproduce-the-sdk-and-release-archive-build) covers rebuilding the pinned archive. The [original packaging record](M0_TOOLCHAIN.md#build-the-deployable-m0-title) records the successful integration and historical host paths.

| Variable | Required contents |
| --- | --- |
| `TEMPLATE` | Clean PS5_VulkanTemplate checkout at `91179df760df1e6c6f2d4d172bc435319d79ff3c` |
| `VULKAN` | Clean tracked PS5_Vulkan source at `7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc`. Upstream bootstrap builds `build/host/ps5-native-tool` and `runtime/libc.prx`. Its link recipe writes into the ignored upstream build directory. |
| `MESA` | Clean PS5_Mesa at `1ba9874f478657ccf6da72ce55f0260164cc0bd0` |
| `RADV` | Release export with `include/`, `PROVENANCE.txt` and verified `lib/libvulkan_radeon.ps5.a` |
| `SDK_SOURCE` | PS5_PayloadSDK git checkout containing the title SDK revision |
| `TITLE_SDK` | Public SDK v0.42 with the template overlay at `611893fc25ef3e138f5bc2c90d829d8b58174cd2` (template's `ps5/tools/setup-sdk.sh`) |
| `ARCHIVE_SDK` | Public SDK v0.42 with the RADV build overlay at `b83202be73e930050e00de0f1b4d9ec46c0391bf` |

Use the M0 Linux toolchain with Clang/LLD/LLVM 21 and compiler-rt builtins, CMake, Ninja, glslangValidator, spirv-val, Git, ripgrep, GNU binutils/coreutils and Python 3.11+ with Pillow. The notice hook uses the Debian libllvm21 and DejaVu copyright files. Linux tests also require Vulkan development headers, a loader, C++20 and a software ICD. Set `VK_DRIVER_FILES` to the llvmpipe ICD for Linux verification. Add normal CMake `-D` overrides after the Linux output directory for non-system installs.

```bash
tools/m0 preflight
tools/m0 linux build/linux
tools/m0 package build/title-build
app=build/title-build/title/dist/PPSA99743
tools/m0 verify "$app"
python3 tests/fixtures/m0-title/check-harness.py "$app"
sha256sum "$app.zip"
```

The output contains `cross/` for compiler, shader, object and input checksums, `title/work/` for linked and converted intermediates and native-tool inspection, and `title/dist/` for the deliverables. The title's `build.json` binds the source revision, input hashes and pinned dependencies to the identifier embedded in the executable. New builds inventory every other packaged file by SHA-256. The historical hardware-tested ZIP is recognized by its exact digest. Verify preserves its original manifest.

## Transfer and evidence

For manual deployment, verify the ZIP and extract its single `PPSA99743` root. Check the title ID and destination are free. Transfer that directory to `/data/homebrew/`, with `eboot.bin` immediately under `PPSA99743/`. This system already has the hardware-tested build under that ID. Preserve its run directories.

For an explicitly authorized fresh transfer, set `PS5_HOST` locally to the console's LAN IPv4 address. The transfer commands use the Prospero Manager file API on port 7070. The deploy command aborts on an occupied title ID. It stages the folder, reads back each file, publishes by renaming the directory, and checks the published bytes. A failed transfer prints the unique staging path for inspection. Launch is manual.

```bash
tools/m0 deploy "$app" "$PS5_HOST"
tools/m0 readback "$app" "$PS5_HOST"
tools/m0 retrieve "$PS5_HOST" run-000001 build/retrieved/run-000001
tools/m0 accept "$app" build/retrieved/run-000001
```

Retrieve writes to a new directory and preserves incomplete captures. It saves available title-specific kernel log lines. Accept takes the folder of the **actual deployed build**, checks its ZIP and executable, verifies the smoke record and matching journal, and recomputes CPU timing statistics from the raw samples. Offline acceptance leaves DEPLOY unverified; a successful readback provides that independent evidence. SHELL_EXIT requires an observed normal close. A workload return code or a logged request to close provides evidence only for the corresponding event.

## Recovery findings

**Observed.** At published commit `468a64b`, the standalone change had explicit deliverables for the pre-packaging link and review ZIP. The review scenario left title ID and packaging unassigned. The deployable builder, title adapter and runtime notice hook were still outside version control after the console run. The retained failed build directories and session output identify two actual failures: the selected Python environment lacked usable Pillow for icon generation, and an extra raw-ELF comparison rejected the signer's omission of a trailing note. Upstream SELF inspection and digest verification accepted the generated modules. Two original package passes produced identical ZIPs. Commit `848cd1f` preserves the successful implementation, including the adapter hashed by the deployed manifest.

**Inference.** An acceptance workflow ending at the review ZIP allowed useful intermediate work to be reported as the final deliverable. Paths into an earlier session's dependency caches and a separate cross-build made reconstruction harder. The current package entry point starts at the shader and workload source and finishes after folder, manifest, embedded identity and ZIP validation.
