# Upstream audit register

Repository existence verified at scaffold time. Contents, revisions, license compatibility, and PS5 firmware support must be audited in M0; the roles below are candidates, not validated integration contracts.

| Source | Candidate role |
| --- | --- |
| [PS5_Vulkan](https://github.com/mihawk-99/PS5_Vulkan) | Driver integration, hardware diagnostics and existing CTS work |
| [PS5_Mesa](https://github.com/mihawk-99/PS5_Mesa) | PS5 Mesa/RADV implementation and compiler behavior |
| [PS5_VulkanTemplate](https://github.com/mihawk-99/PS5_VulkanTemplate) | Public homebrew build, runtime and sample integration |
| [Vulkan CTS](https://github.com/KhronosGroup/VK-GL-CTS) | Conformance cases and result semantics |
| [Vulkan Samples](https://github.com/KhronosGroup/Vulkan-Samples) | Graphics, compute and performance examples |
| [Vulkan specification](https://registry.khronos.org/vulkan/) | Normative API requirements |
| [Vulkan-Headers](https://github.com/KhronosGroup/Vulkan-Headers) | API declarations |
| [Mesa](https://gitlab.freedesktop.org/mesa/mesa) | Linux RADV reference |
| [Sascha Willems Vulkan](https://github.com/SaschaWillems/Vulkan) | Optional additional examples |
| [vkmark](https://github.com/vkmark/vkmark) | Optional conventional graphics workloads |

For each selected dependency record exact commit/tag, license and notices, build targets, supported features, portability constraints, existing tests, local modifications and update strategy. Verify the existing CTS workflow before choosing native integration vs report ingestion. Prefer thin adapters or pinned dependencies over copied source. Do not vendor or redistribute third-party code until license requirements are reviewed.

Coverage matrix columns: Vulkan requirement/extension, upstream test ID and revision, lab test ID, capability prerequisites, target, status, correctness reference, timing availability, known issue and evidence link.
