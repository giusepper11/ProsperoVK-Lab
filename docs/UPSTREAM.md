# Upstream audit

M0 source snapshot, 2026-11-24. Lab base `abee1ca738e3ddfd0ee9bf385e875f707baafe76`. The GitHub issue inventory contained issues #1–#8, aligned with M0–M7. Issue #1 requires console feasibility and a maintainer license decision. Issue #2 depends on M0. [M0 issue], [M1 issue].

## Pinned source and integration choices

| Source and exact revision | What exists and how it builds | License and proposed use |
| --- | --- | --- |
| [PS5_Vulkan] `7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc` | RADV is the forward path. `tools/build-radv.sh` uses Meson and Ninja to export a static debug or release archive with headers and provenance. `radv/radv_smoke.c` exercises buffer fill/copy, CPU-checked compute, triangle, coherence, optional feature groups and display. Legacy `ps5vk` reports Vulkan 1.1 with its own command/limit/format audits, C/C++ host tests and console probes. | Project GPL-3.0-or-later, with file- and dependency-specific terms in [NOTICE]. Keep driver checks as external diagnostics. Reuse the RADV build and linkage contract after review. Defer the legacy driver to a separate later comparison. |
| [PS5_Mesa] `75238ae4db3249803df3deeba47340f6de27962e` inspected branch snapshot. [Archive build pin] `1ba9874f478657ccf6da72ce55f0260164cc0bd0` used by PS5_Vulkan by default. | Mesa 26.2.0 fork, RADV with ACO and a PS5 winsys for buffers, submission, synchronization and display. The upstream Linux model builds a shared ICD for API checks but models the console. The default archive and inspected branch snapshot are different revisions. The newer snapshot includes a PS5 memory-budget accounting fix. | Mesa core and most files MIT, with per-file terms and notices. Use the external pinned archive and its matching headers for initial integration. Build variants, SDK revision and archive hashes are part of driver identity. [Mesa licensing], [build script]. |
| [PS5_VulkanTemplate] `91179df760df1e6c6f2d4d172bc435319d79ff3c` | Sascha Willems Vulkan fork. `ps5/CMakeLists.txt` uses C++20 and creates sample objects for a title linked to RADV. The Linux reference uses the system loader with headless WSI or a sample-specific offscreen fallback. Scripted runs collect final PNGs, logs and summaries and compare against reference images. This revision's commit reports 39 linked host samples passing on an RTX 3070 and a console compile. | Sample and port source MIT under [license]. Assets carry individual terms. The upstream title's built artifact links the GPL PS5 platform library, and the optional UI is GPL-3.0-or-later. Adapt the CMake target and platform boundary. Use sample IDs and comparisons as external references. [Template build and results], [sample registry], [assets]. |
| [VK-GL-CTS snapshot] `05ca62dcffe1353d8e058a6a9d759e3fa1007449` inspected for layout. [CTS base] `f6a29701220f34dd1407513bfe80d74ca7b392ce` is the independently resolved `vulkan-cts-1.4.6.2` tag used for PS5 comparisons. | CMake `deqp-vk` with external dependencies from `external/fetch_sources.py`. Desktop entry point `DEQP_TARGET=vulkan_headless` selected by PS5_Vulkan's host runner. Cases and status codes are reusable directly through the CTS harness. Console port and output formats are detailed below. | Apache-2.0 CTS source, with separate external component terms. Use upstream case selection and consume its reports first. [CTS license], [CTS host build], [CTS tools]. |
| [Vulkan Samples] `979aefaa5f2f4bd30efe035ca5a39444cc24ab9f` | CMake `vulkan_samples` target, stock Linux WSI selection, sample and dependency submodules pinned by Git links. `hello_triangle`, `compute_nbody`, `timestamp_queries`, `pipeline_cache`, `mesh_shader_culling` and `ray_queries` demonstrate relevant paths. Their application framework, data, render loop and presentation assumptions vary. | Apache-2.0 project, with separate dependency and asset terms. Use stock samples on Linux as examples. Adapt only a case's needed logic, requirements and reference check for shared workloads. [Samples license], [Samples build]. |
| [Vulkan-Docs] `33d3353757d83d6aca683120114fe74cc4eaf8fb` and [Vulkan-Headers] `d277a0a3cda9c682708c93279f0c72cd6b0ae3f3`, both `v1.4.369` | Normative audit reference and API declarations. The lab records the actual header version used by each build. PS5_Vulkan's legacy audit uses its own spec pin. | Use the specification for requirement classification. Keep target compilation on compatible pinned headers. [Vulkan spec license], [Headers license]. |

The archive SDK pin is [PS5_PayloadSDK at `b83202be73e930050e00de0f1b4d9ec46c0391bf`][SDK build pin]. The Template uses [`611893fc25ef3e138f5bc2c90d829d8b58174cd2`][SDK template pin]. Both layer on the hash-pinned public payload SDK v0.42. [Driver SDK setup], [Template SDK setup], [SDK setup sources]. Treat those SDK revisions as distinct until the archive and title linkage are verified together.

The lab's original work follows the primary PS5_Vulkan and SDK platform references under `GPL-3.0-or-later`. Preserve the separate license and notices attached to each upstream component. Before distributing a combined title, review that build's actual link inputs, assets, corresponding source and notices. [Lab license](../LICENSE), [PS5_Vulkan license], [SDK license], [NOTICE].

## CTS execution and report ingestion

- **Linux.** The [upstream host runner] builds `deqp-vk`, selects one case pattern, and emits `stdout.log`, `results.qpa` and `summary.json`. Its stated reference setup uses the simulated PS5 winsys ICD for API groups. The lab built the pinned Khronos CTS unchanged and ran the selected console smoke case on Linux llvmpipe. The lab verifier confirmed one complete session and the expected XML case identity. The pinned upstream parser returned Pass. [Linux evidence](M0_TOOLCHAIN.md#reproduce-the-single-cts-smoke-on-linux).
- **Console.** Upstream documents `PS5_VK-GL-CTS`, a fork of the pinned release with `DEQP_TARGET=ps5`. The title links the RADV archive directly and resolves Vulkan through `vk_icdGetInstanceProcAddr`. The documented runner selects a case or list, collects QPA, and can add klog-derived or runner-derived rows to batched `results.tsv`. A raw QPA status, a klog observation and an inferred timeout or crash have different provenance. Preserve each source and its original status when importing. [CTS workflow], [console link script], [run-cts.py], [cts-results.py].
- **Port reproducibility.** The named fork returned GitHub API 404 and `git ls-remote https://github.com/mihawk-99/PS5_VK-GL-CTS.git HEAD` returned repository not found. A follow-up GitHub repository search returned no match for `PS5_VK-GL-CTS in:name fork:true`. The release APIs returned empty lists for PS5_Vulkan and PS5_VulkanTemplate. A later check of the public pages still found the 404 and no published releases. The exact fork commit, patches, compiled externals and title artifact remain unverified. The [pin manifest] records the base CTS commit plus declared and checked-out externals. A title's build manifest must identify what it compiled. Console relaunch behavior in the upstream batch runner is unsuitable after a device loss or suspected hang under this lab's stop rule. [Named CTS fork], [PS5_Vulkan releases], [Template releases].
- **Public focused CTS alternative.** The GPL-3.0-or-later `mpereiraesaa/ps5-vulkan` snapshot `e6d3c3f82f3c8a574e28c174b15b287f9c0ecc6d` carries a native PS5 platform adapter and a focused suite based on Khronos CTS `a0270c1897597e6c77679870e10415398a13001c` (`vulkan-cts-1.3.8.4`). Its adapter binds the project's own ps5vk driver and its manifest excludes the selected storage-buffer compute case. It supplies a source reference for platform adaptation and reporting. Running its supplied selection would provide evidence for its own driver, CTS pin and tests. [Focused CTS design], [platform adapter], [selection manifest].
- **Published outcomes.** Upstream reports `main-1` across evolving builds, and `full-1` on debug Mesa [`6824f491209269fbbc31825ff8aeca6b2b394ed9`][Mesa full-1]. Of 2,919,757 `full-1` cases, 1,569,390 passed, 1,350,306 were NotSupported, 60 were QualityWarning, one was Crash attributed to an operator interruption, and zero were Fail. A passing conformance run for the current archive remains unverified. The older conformance text in `CTS.md` conflicts with the pinned PS5 driver source, which sets `conformanceVersion = 0.0.0.0`. Record that separately from advertised Vulkan 1.4. [Phase log], [CTS gaps], [archive physical device source].

**Reuse decision.** Run native Linux CTS cases unchanged in their upstream harness. Import authorized external QPA and ancillary reports with original IDs, CTS and fork revisions when known, driver identity and selection manifest. Adapt the Template's build/platform approach and sample references only where they fit a bounded shared workload. Implement the lab's registry, preflight, exact correctness checks, result contract and recovery policy locally. A native PS5 CTS rebuild and sample benchmark integration depend on the relevant source and platform inputs.

## Standalone compute component review

This inventory covers the locally linked `m0.radv.compute` ELF with SHA-256 `3b621e426545170c13ff4e501af6a952b43bba747d98f3ddb8b6904d4784b6fb`. It uses the section map, archive extraction table and dynamic library declarations from the same link. [Reproduction and evidence](M0_TOOLCHAIN.md#link-the-build-host-elf).

| Component | Evidence in the pre-packaging link | Source and notices to retain for review |
| --- | --- | --- |
| Lab fixture and PS5_Vulkan application startup | `main.o`, `compute.o` with generated SPIR-V, `app_crt.o` and `app_cpp_runtime.o` have sections in the ELF map. | Lab and pinned PS5_Vulkan source files carry GPL-3.0-or-later. Retain the shader source, CRT, C++ startup, linker scripts, build recipe and their notices. [Lab license](../LICENSE), [pinned link inputs](../tests/fixtures/m0-radv-compute/elf-link-inputs.txt), [NOTICE]. |
| PS5 Mesa 26.2.0 RADV release | The recipe supplies the archive with `--whole-archive`. `llvm-ar t` lists 704 members and the map shows 695 distinct member names with nonzero input sections. Two archive basenames are duplicated. | Preserve the exact Mesa pin, build inputs and generated-source provenance. Core Mesa is MIT. Review file-level terms, including embedded zlib 1.3.1 and its WrapDB patch, BLAKE3 1.8.2 (upstream offers CC0 or Apache 2.0 variants), modified Berkeley SoftFloat 3e (BSD-3-Clause), and xxHash (BSD-2-Clause). The map shows zlib, BLAKE3 and SoftFloat objects, and the ELF defines local `XXH_INLINE_XXH32` symbols. [Pinned Mesa license guide], [zlib wrap], [zlib license], [BLAKE3 source note], [BLAKE3 terms], [SoftFloat notice], [xxHash notice]. |
| SDK platform overlay | `libps5platform.a` contributed 17 of 25 members, including `mspace.o`, `regcomp.o` and `regexec.o`. | Preserve the pinned fork's GPL-3.0-or-later platform source and the notices for dlmalloc 2.8.6 (MIT-0), the TRE implementation (BSD-2-Clause), and the musl 1.2.5 regex header (MIT). [SDK license], [allocator source], [TRE source], [musl notice]. |
| SDK C++ runtimes | `libc++.a` contributed 15 of 54 members, `libc++abi.a` 14 of 18, and `libunwind.a` 4 of 9. All three archives matched the digest-verified SDK v0.42 ZIP bytes. | The v0.42 build script uses LLVM 18.1.8. Preserve the SDK build recipe and the component notices for Apache-2.0 with LLVM exceptions. [SDK runtime build], [libc++ terms], [libc++abi terms], [libunwind terms]. |
| Compiler builtins | Ubuntu `libclang-rt-21-dev` `1:21.1.8-6ubuntu1` supplied `libclang_rt.builtins-x86_64.a`. The map shows `emutls.c.o` and `x86.c.o` from its 173 members. | Preserve the distro package source and its `usr/share/doc/libclang-rt-21-dev/copyright` along with the upstream compiler-rt terms. [compiler-rt terms]. |
| Dynamic libraries | Seven `DT_NEEDED` declarations. Two are from public PS5_Vulkan AGC link stubs. The other five correspond to SDK v0.42 import libraries. All 287 imported names had matching public stub exports. | Preserve the GPL-3.0-or-later source headers for the AGC link stubs and review the SDK's stub generation inputs. The exact console providers and their availability remain unverified. [Stub candidates](M0_TOOLCHAIN.md#review-the-public-stub-candidates), [pinned link inputs](../tests/fixtures/m0-radv-compute/elf-link-inputs.txt), [SDK v0.42 stub build], [SDK v0.42 license]. |

The map shows code from both generated OpenCL libraries, `libpoly` and `libradv_cl`. The build-host replay verified the generated SPIR-V, C++ and headers, as well as the Mesa sources and the Clang resource headers used in generation. The Mesa OpenCL sources carry MIT notices. The two Clang OpenCL headers carry Apache-2.0 with LLVM exceptions. The compiled C++ objects also depend on generated Mesa headers and headers from the SDK and Clang. Review header and generator provenance alongside the archive's ordered direct input list. [Pinned libpoly build rules], [pinned RADV OpenCL build rules], [replay and inputs](M0_TOOLCHAIN.md#verify-radv-archive-and-generated-inputs).

The final title review requires the actual package file list, including metadata and any assets, the executable and package SHA-256 digests, the sources and notices for shipped components, and the matching build scripts and pins. Record the maintainer's distribution decision against that package manifest. M0 task 2.4 remains open for the final title. [M0 tasks](../openspec/changes/m0-upstream-feasibility-audit/tasks.md).

## Risks and outstanding evidence

| Gap | Consequence and required evidence |
| --- | --- |
| Slim firmware 13.60 | No run ties this model and firmware to the pinned title, SDK and archive. The source records a base PS5 on 13.40 with Mesa [`7b59ef27c1b09b9671bc4153c41940c3155c3af2`][Mesa display] and a Pro smoke with Mesa [`47e9eb61ee7e1112194557e1e047178562827bc6`][Mesa Pro]. The latter reports 25 storage checks passing and 127 passes with one display-mode failure in the full run. These records provide upstream context. [Hardware findings], [Phase log]. |
| SDK and title linkage | Local C++20 target compilation, the RADV archive build and a relocatable link check passed. Whole-archive linking retains driver functions left weak and undefined by selective extraction. The standalone compute ELF linked on the build host using the pinned public AGC link stubs. The final title still needs a build manifest and package digest, verified runtime imports and target startup evidence. [Relocatable link evidence](M0_TOOLCHAIN.md#reproduce-the-ps5-relocatable-link-check), [standalone ELF evidence](M0_TOOLCHAIN.md#link-the-build-host-elf), [hardware runbook](HARDWARE_VALIDATION.md). |
| Memory and scheduling | The PS5 winsys reports integrated memory and exposes a compute/transfer family whose submissions share the graphics ring. Emulated timeline synchronization and logical queue counts cannot establish overlap. Derive safe allocation limits from target capacity and the chosen title/runtime, then verify the small smoke buffer on the exact target. [Archive winsys], [CTS gaps]. |
| Presentation and advanced features | Query formats, surface capabilities and independent feature bits on the actual target. The upstream display test differs by active video mode. Leave WSI, async overlap, mesh/task, ray tracing and special timing to their milestone-specific gates. [Coverage matrix](VULKAN_COVERAGE.md). |
| Test provenance and license | Upstream updates can change defaults, driver behavior and test IDs. Review pins together by change, check leaf IDs against the pinned case list, preserve input/output and notices, and rerun the same bounded fixture before accepting an update. The standalone ELF's component review is available. Submit the actual package manifest and notices for maintainer review before distribution. [Standalone component review](#standalone-compute-component-review). |

[M0 issue]: https://github.com/giusepper11/ProsperoVK-Lab/issues/1
[M1 issue]: https://github.com/giusepper11/ProsperoVK-Lab/issues/2
[PS5_Vulkan]: https://github.com/mihawk-99/PS5_Vulkan/tree/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc
[PS5_Vulkan license]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/LICENSE
[PS5_Vulkan releases]: https://github.com/mihawk-99/PS5_Vulkan/releases
[Named CTS fork]: https://github.com/mihawk-99/PS5_VK-GL-CTS
[NOTICE]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/NOTICE.md
[PS5_Mesa]: https://github.com/mihawk-99/PS5_Mesa/tree/75238ae4db3249803df3deeba47340f6de27962e
[Archive build pin]: https://github.com/mihawk-99/PS5_Mesa/tree/1ba9874f478657ccf6da72ce55f0260164cc0bd0
[Mesa licensing]: https://github.com/mihawk-99/PS5_Mesa/blob/75238ae4db3249803df3deeba47340f6de27962e/docs/license.rst
[build script]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/build-radv.sh
[PS5_VulkanTemplate]: https://github.com/mihawk-99/PS5_VulkanTemplate/commit/91179df760df1e6c6f2d4d172bc435319d79ff3c
[license]: https://github.com/mihawk-99/PS5_VulkanTemplate/blob/91179df760df1e6c6f2d4d172bc435319d79ff3c/LICENSE.md
[Template build and results]: https://github.com/mihawk-99/PS5_VulkanTemplate/blob/91179df760df1e6c6f2d4d172bc435319d79ff3c/ps5/README.md
[Template releases]: https://github.com/mihawk-99/PS5_VulkanTemplate/releases
[sample registry]: https://github.com/mihawk-99/PS5_VulkanTemplate/blob/91179df760df1e6c6f2d4d172bc435319d79ff3c/ps5/src/samples.cpp
[assets]: https://github.com/mihawk-99/PS5_VulkanTemplate/blob/91179df760df1e6c6f2d4d172bc435319d79ff3c/ps5/ASSETS.md
[VK-GL-CTS snapshot]: https://github.com/KhronosGroup/VK-GL-CTS/tree/05ca62dcffe1353d8e058a6a9d759e3fa1007449
[CTS base]: https://github.com/KhronosGroup/VK-GL-CTS/tree/f6a29701220f34dd1407513bfe80d74ca7b392ce
[CTS license]: https://github.com/KhronosGroup/VK-GL-CTS/blob/f6a29701220f34dd1407513bfe80d74ca7b392ce/LICENSE
[CTS host build]: https://github.com/KhronosGroup/VK-GL-CTS/blob/f6a29701220f34dd1407513bfe80d74ca7b392ce/README.md
[CTS tools]: https://github.com/KhronosGroup/VK-GL-CTS/tree/f6a29701220f34dd1407513bfe80d74ca7b392ce/scripts/log
[Vulkan Samples]: https://github.com/KhronosGroup/Vulkan-Samples/tree/979aefaa5f2f4bd30efe035ca5a39444cc24ab9f
[Samples license]: https://github.com/KhronosGroup/Vulkan-Samples/blob/979aefaa5f2f4bd30efe035ca5a39444cc24ab9f/LICENSE
[Samples build]: https://github.com/KhronosGroup/Vulkan-Samples/blob/979aefaa5f2f4bd30efe035ca5a39444cc24ab9f/docs/build.adoc
[Vulkan-Docs]: https://github.com/KhronosGroup/Vulkan-Docs/tree/33d3353757d83d6aca683120114fe74cc4eaf8fb
[Vulkan-Headers]: https://github.com/KhronosGroup/Vulkan-Headers/tree/d277a0a3cda9c682708c93279f0c72cd6b0ae3f3
[Vulkan spec license]: https://github.com/KhronosGroup/Vulkan-Docs/blob/33d3353757d83d6aca683120114fe74cc4eaf8fb/LICENSE.adoc
[Headers license]: https://github.com/KhronosGroup/Vulkan-Headers/blob/d277a0a3cda9c682708c93279f0c72cd6b0ae3f3/LICENSE.md
[SDK build pin]: https://github.com/mihawk-99/PS5_PayloadSDK/tree/b83202be73e930050e00de0f1b4d9ec46c0391bf
[SDK license]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/LICENSE
[SDK template pin]: https://github.com/mihawk-99/PS5_PayloadSDK/tree/611893fc25ef3e138f5bc2c90d829d8b58174cd2
[Driver SDK setup]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/setup-native-dependencies.sh
[Template SDK setup]: https://github.com/mihawk-99/PS5_VulkanTemplate/blob/91179df760df1e6c6f2d4d172bc435319d79ff3c/ps5/tools/setup-sdk.sh
[SDK setup sources]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/platform/tools/setup-sdk.sh
[upstream host runner]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/run-cts-host.sh
[CTS workflow]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/docs/CTS.md
[Focused CTS design]: https://github.com/mpereiraesaa/ps5-vulkan/blob/e6d3c3f82f3c8a574e28c174b15b287f9c0ecc6d/UPSTREAM_CTS.md
[platform adapter]: https://github.com/mpereiraesaa/ps5-vulkan/blob/e6d3c3f82f3c8a574e28c174b15b287f9c0ecc6d/cts/upstream/platform_ps5.cpp
[selection manifest]: https://github.com/mpereiraesaa/ps5-vulkan/blob/e6d3c3f82f3c8a574e28c174b15b287f9c0ecc6d/cts/upstream/manifest.json
[console link script]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/build-cts-title.sh
[run-cts.py]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/run-cts.py
[cts-results.py]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/tools/cts-results.py
[pin manifest]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/conformance_inventory/cts_pin.json
[Mesa full-1]: https://github.com/mihawk-99/PS5_Mesa/commit/6824f491209269fbbc31825ff8aeca6b2b394ed9
[Mesa display]: https://github.com/mihawk-99/PS5_Mesa/commit/7b59ef27c1b09b9671bc4153c41940c3155c3af2
[Mesa Pro]: https://github.com/mihawk-99/PS5_Mesa/commit/47e9eb61ee7e1112194557e1e047178562827bc6
[Phase log]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/docs/RADV_PHASE.md
[Hardware findings]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/docs/HARDWARE_FINDINGS.md
[CTS gaps]: https://github.com/mihawk-99/PS5_Vulkan/blob/7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc/docs/CTS_GAPS.md
[archive physical device source]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/amd/vulkan/radv_physical_device.c
[Archive winsys]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/amd/vulkan/winsys/ps5/radv_ps5_winsys.c
[Pinned Mesa license guide]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/docs/license.rst
[Pinned libpoly build rules]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/poly/cl/meson.build
[pinned RADV OpenCL build rules]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/amd/vulkan/meson.build#L291-L321
[zlib wrap]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/subprojects/zlib.wrap
[zlib license]: https://github.com/madler/zlib/blob/v1.3.1/LICENSE
[BLAKE3 source note]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/util/blake3/README
[BLAKE3 terms]: https://github.com/BLAKE3-team/BLAKE3/blob/1.8.2/README.md#license
[SoftFloat notice]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/util/softfloat.c
[xxHash notice]: https://github.com/mihawk-99/PS5_Mesa/blob/1ba9874f478657ccf6da72ce55f0260164cc0bd0/src/util/xxhash.h
[allocator source]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/platform/src/dlmalloc/malloc.c
[TRE source]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/platform/src/regex/regcomp.c
[musl notice]: https://github.com/mihawk-99/PS5_PayloadSDK/blob/b83202be73e930050e00de0f1b4d9ec46c0391bf/platform/src/regex/COPYRIGHT.musl
[SDK runtime build]: https://github.com/ps5-payload-dev/sdk/blob/v0.42/libcxx.sh
[SDK v0.42 stub build]: https://github.com/ps5-payload-dev/sdk/blob/v0.42/sce_stubs/Makefile
[SDK v0.42 license]: https://github.com/ps5-payload-dev/sdk/blob/v0.42/LICENSE
[libc++ terms]: https://github.com/llvm/llvm-project/blob/llvmorg-18.1.8/libcxx/LICENSE.TXT
[libc++abi terms]: https://github.com/llvm/llvm-project/blob/llvmorg-18.1.8/libcxxabi/LICENSE.TXT
[libunwind terms]: https://github.com/llvm/llvm-project/blob/llvmorg-18.1.8/libunwind/LICENSE.TXT
[compiler-rt terms]: https://github.com/llvm/llvm-project/blob/llvmorg-21.1.8/compiler-rt/LICENSE.TXT
