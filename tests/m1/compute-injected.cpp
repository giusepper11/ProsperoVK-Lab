// SPDX-License-Identifier: GPL-3.0-or-later
#include "suites/compute/compute.hpp"
#include "core/runner.hpp"

#include <cstdio>
#include <cstring>
#include <fstream>
#include <string_view>

namespace {

std::string_view fault;
std::string report_path;
PFN_vkGetDeviceProcAddr device_proc = nullptr;
PFN_vkQueueSubmit queue_submit = nullptr;
PFN_vkWaitForFences wait_for_fences = nullptr;
PFN_vkMapMemory map_memory = nullptr;
PFN_vkFlushMappedMemoryRanges flush_ranges = nullptr;
PFN_vkInvalidateMappedMemoryRanges invalidate_ranges = nullptr;
PFN_vkDestroyDevice destroy_device = nullptr;
PFN_vkDestroyBuffer destroy_buffer = nullptr;
PFN_vkGetBufferMemoryRequirements get_requirements = nullptr;
VkDeviceMemory allocation = VK_NULL_HANDLE;
void* mapped = nullptr;
int submissions = 0;
int waits = 0;
int flushes = 0;
int invalidations = 0;
int devices_destroyed = 0;
int buffers_destroyed = 0;
bool parameters_valid = true;

VKAPI_ATTR VkResult VKAPI_CALL submit(VkQueue queue, std::uint32_t count, const VkSubmitInfo* info, VkFence fence) {
    ++submissions;
    if (!report_path.empty()) {
        std::ifstream journal(report_path + ".start.json");
        std::string start;
        parameters_valid &= bool(std::getline(journal, start))
            && start.find("\"event\":\"start\"") != std::string::npos
            && start.find("\"case_id\":\"core.compute.storage-buffer\"") != std::string::npos;
    }
    if (fault == "device-lost") return VK_ERROR_DEVICE_LOST;
    if (fault == "submit-error") return VK_ERROR_OUT_OF_HOST_MEMORY;
    return queue_submit(queue, count, info, fence);
}

VKAPI_ATTR VkResult VKAPI_CALL wait(VkDevice device, std::uint32_t count, const VkFence* fences,
                                   VkBool32 wait_all, std::uint64_t timeout) {
    ++waits;
    parameters_valid &= count == 1 && wait_all == VK_TRUE && timeout == 5'000'000'000;
    const auto status = wait_for_fences(device, count, fences, wait_all, timeout);
    if (status != VK_SUCCESS) return status;
    // Faults occur after the real fence completes so the test cannot leave live GPU work.
    if (fault == "timeout") return VK_TIMEOUT;
    if (fault == "wait-error") return VK_ERROR_OUT_OF_HOST_MEMORY;
    if (fault == "left-guard" || fault == "right-guard" || fault == "output") {
        const std::size_t index = fault == "left-guard" ? 0 : fault == "right-guard" ? 65 : 1;
        const std::uint32_t zero = 0;
        std::memcpy(static_cast<char*>(mapped) + index * sizeof(zero), &zero, sizeof(zero));
    }
    return VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL map(VkDevice device, VkDeviceMemory memory, VkDeviceSize offset, VkDeviceSize size,
                                  VkMemoryMapFlags flags, void** output) {
    parameters_valid &= offset == 0 && size == VK_WHOLE_SIZE;
    const auto status = map_memory(device, memory, offset, size, flags, output);
    if (status == VK_SUCCESS) {
        allocation = memory;
        mapped = *output;
    }
    return status;
}

bool whole_allocation(std::uint32_t count, const VkMappedMemoryRange* range) {
    return count == 1 && range->sType == VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE
        && range->memory == allocation && range->offset == 0 && range->size == VK_WHOLE_SIZE;
}

VKAPI_ATTR VkResult VKAPI_CALL flush(VkDevice device, std::uint32_t count, const VkMappedMemoryRange* ranges) {
    ++flushes;
    parameters_valid &= whole_allocation(count, ranges) && submissions == 0;
    if (fault == "flush-error") return VK_ERROR_OUT_OF_HOST_MEMORY;
    return flush_ranges(device, count, ranges);
}

VKAPI_ATTR VkResult VKAPI_CALL invalidate(VkDevice device, std::uint32_t count, const VkMappedMemoryRange* ranges) {
    ++invalidations;
    parameters_valid &= whole_allocation(count, ranges) && waits == 1;
    if (fault == "invalidate-error") return VK_ERROR_OUT_OF_HOST_MEMORY;
    return invalidate_ranges(device, count, ranges);
}

VKAPI_ATTR void VKAPI_CALL requirements(VkDevice device, VkBuffer buffer, VkMemoryRequirements* output) {
    get_requirements(device, buffer, output);
    if (fault == "allocation-ceiling") output->size = 2 * 1024 * 1024;
    if (fault == "memory-bits") output->memoryTypeBits = 0;
}

VKAPI_ATTR void VKAPI_CALL destroy(VkDevice device, const VkAllocationCallbacks* allocator) {
    ++devices_destroyed;
    destroy_device(device, allocator);
}

VKAPI_ATTR void VKAPI_CALL destroy_buffer_tracked(VkDevice device, VkBuffer buffer,
                                                  const VkAllocationCallbacks* allocator) {
    ++buffers_destroyed;
    destroy_buffer(device, buffer, allocator);
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL device_resolver(VkDevice device, const char* name) {
    const auto proc = device_proc(device, name);
    if (!proc || (fault == "missing-entry" && std::strcmp(name, "vkCreateShaderModule") == 0)) return nullptr;
#define WRAP(name_suffix, original, replacement) \
    if (std::strcmp(name, "vk" #name_suffix) == 0) { \
        original = reinterpret_cast<PFN_vk##name_suffix>(proc); \
        return reinterpret_cast<PFN_vkVoidFunction>(replacement); \
    }
    WRAP(QueueSubmit, queue_submit, submit)
    WRAP(WaitForFences, wait_for_fences, wait)
    WRAP(MapMemory, map_memory, map)
    WRAP(FlushMappedMemoryRanges, flush_ranges, flush)
    WRAP(InvalidateMappedMemoryRanges, invalidate_ranges, invalidate)
    WRAP(GetBufferMemoryRequirements, get_requirements, requirements)
    WRAP(DestroyDevice, destroy_device, destroy)
    WRAP(DestroyBuffer, destroy_buffer, destroy_buffer_tracked)
#undef WRAP
    return proc;
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL instance_resolver(VkInstance instance, const char* name) {
    const auto proc = vkGetInstanceProcAddr(instance, name);
    if (proc && std::strcmp(name, "vkGetDeviceProcAddr") == 0) {
        device_proc = reinterpret_cast<PFN_vkGetDeviceProcAddr>(proc);
        return reinterpret_cast<PFN_vkVoidFunction>(device_resolver);
    }
    return proc;
}

struct Scenario {
    std::string_view name;
    std::string_view status;
    std::string_view detail;
    int submits;
    int waits;
    int devices_destroyed;
    int buffers_destroyed;
    bool abandon = false;
};

constexpr Scenario scenarios[] = {
    {"pass", "PASS", "\"mismatch_count\":0", 1, 1, 1, 1},
    {"left-guard", "FAIL", "\"index\":0", 1, 1, 1, 1},
    {"right-guard", "FAIL", "\"index\":65", 1, 1, 1, 1},
    {"output", "FAIL", "\"index\":1", 1, 1, 1, 1},
    {"noncoherent", "PASS", "\"mismatch_count\":0", 1, 1, 1, 1},
    {"flush-error", "ERROR", "vkFlushMappedMemoryRanges", 0, 0, 1, 1},
    {"invalidate-error", "ERROR", "vkInvalidateMappedMemoryRanges", 1, 1, 1, 1},
    {"missing-entry", "ERROR", "vkCreateShaderModule", 0, 0, 1, 0},
    {"no-compute-queue", "UNSUPPORTED", "compute queue family", 0, 0, 0, 0},
    {"local-size", "UNSUPPORTED", "maxComputeWorkGroupSize[0]", 0, 0, 0, 0},
    {"allocation-ceiling", "UNSUPPORTED", "1 MiB ceiling", 0, 0, 1, 1},
    {"memory-bits", "UNSUPPORTED", "memoryTypeBits", 0, 0, 1, 1},
    {"submit-error", "ERROR", "vkQueueSubmit", 1, 0, 1, 1},
    {"device-lost", "ERROR", "VK_ERROR_DEVICE_LOST", 1, 0, 0, 0, true},
    {"timeout", "TIMEOUT", "VK_TIMEOUT", 1, 1, 0, 0, true},
    {"wait-error", "ERROR", "vkWaitForFences", 1, 1, 0, 0, true},
};

} // namespace

int main(int argc, char** argv) {
    if (argc != 2 && argc != 3) return 2;
    fault = argv[1];
    for (const auto& scenario : scenarios) {
        if (scenario.name != fault) continue;
        if (argc == 3) {
            report_path = argv[2];
            const std::string build_id(64, '0');
            const std::string revision(40, '1');
            const int result = m1::run(instance_resolver, "linux", build_id.c_str(), revision.c_str(), 0,
                                       "core.compute.storage-buffer", report_path.c_str(), "00000000000000000000000000000000");
            if (result != 1 || !parameters_valid || submissions != scenario.submits || waits != scenario.waits
                || devices_destroyed != scenario.devices_destroyed || buffers_destroyed != scenario.buffers_destroyed) {
                std::fprintf(stderr, "runner injection failed: code=%d submits=%d waits=%d device_cleanup=%d "
                                     "buffer_cleanup=%d journal_before_submit=%d\n",
                             result, submissions, waits, devices_destroyed, buffers_destroyed, parameters_valid);
                return 1;
            }
            return 0;
        }
        m1::Inventory inventory;
        if (!m1::discover(inventory, instance_resolver, 0)) {
            std::fprintf(stderr, "test requires a working Linux Vulkan device: %s\n", inventory.reason.c_str());
            return 1;
        }
        if (fault == "no-compute-queue") inventory.queue_family = UINT32_MAX;
        if (fault == "local-size") inventory.properties.limits.maxComputeWorkGroupSize[0] = 63;

        // Vulkan permits the wrapped synchronization calls on a coherent allocation too.
        // Clear the advertised flag to exercise the non-coherent path on software Vulkan.
        const bool force_noncoherent = fault == "noncoherent" || fault == "flush-error" || fault == "invalidate-error";
        if (force_noncoherent) {
            for (std::uint32_t i = 0; i < inventory.memory.memoryTypeCount; ++i) {
                inventory.memory.memoryTypes[i].propertyFlags &= ~VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
            }
        }

        const auto result = m1::compute(inventory);
        bool retry_blocked = true;
        if (scenario.abandon) {
            const auto retry = m1::compute(inventory);
            retry_blocked = retry.status == "ERROR" && retry.reason.find("abandoned") != std::string::npos;
        }
        const auto& detail = result.correctness == "null" ? result.reason : result.correctness;
        const bool passed = parameters_valid && retry_blocked && result.status == scenario.status
            && detail.find(scenario.detail) != std::string::npos
            && ((result.timing != "null") == (result.status == "PASS"))
            && submissions == scenario.submits && waits == scenario.waits
            && devices_destroyed == scenario.devices_destroyed && buffers_destroyed == scenario.buffers_destroyed
            && inventory.abandon == scenario.abandon
            && (!force_noncoherent || (flushes == 1 && invalidations == (fault == "flush-error" ? 0 : 1)));
        if (!passed) {
            std::fprintf(stderr, "%s: status=%s detail=%s submits=%d waits=%d device_cleanup=%d buffer_cleanup=%d "
                                 "flush=%d invalidate=%d\n", argv[1], result.status.c_str(), detail.c_str(),
                         submissions, waits, devices_destroyed, buffers_destroyed, flushes, invalidations);
        }
        return passed ? 0 : 1;
    }
    return 2;
}
