// SPDX-License-Identifier: GPL-3.0-or-later
#include "compute.hpp"

#include <array>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "compute_spv.hpp"

namespace {

// Case dimensions and oracle follow PS5_Vulkan test_compute at
// 7f492b4c6f67a4e8c8c67a4272cfeef22abea9cc.
constexpr std::uint32_t word_count = 4096;
constexpr std::uint32_t workgroup_size = 64;
constexpr std::uint32_t group_count = word_count / workgroup_size;
constexpr VkDeviceSize buffer_size = word_count * sizeof(std::uint32_t);
constexpr VkDeviceSize allocation_limit = 1024 * 1024;
constexpr std::uint64_t fence_timeout_ns = 5'000'000'000;
constexpr char case_id[] = "m0.radv.compute";

int diagnostic(const char* status, const char* stage, const char* reason) {
    std::printf("{\"case_id\":\"%s\",\"status\":\"%s\",\"stage\":\"%s\",\"reason\":\"%s\"}\n",
                case_id, status, stage, reason);
    return 1;
}

template <typename T, typename Resolve, typename Handle>
T entry(Resolve resolve, Handle handle, const char* name) {
    return reinterpret_cast<T>(resolve(handle, name));
}

#define M0_DEVICE_COMMANDS(X) \
    X(DestroyDevice) \
    X(GetDeviceQueue) \
    X(CreateBuffer) \
    X(DestroyBuffer) \
    X(GetBufferMemoryRequirements) \
    X(AllocateMemory) \
    X(FreeMemory) \
    X(BindBufferMemory) \
    X(MapMemory) \
    X(UnmapMemory) \
    X(FlushMappedMemoryRanges) \
    X(InvalidateMappedMemoryRanges) \
    X(CreateShaderModule) \
    X(DestroyShaderModule) \
    X(CreateDescriptorSetLayout) \
    X(DestroyDescriptorSetLayout) \
    X(CreatePipelineLayout) \
    X(DestroyPipelineLayout) \
    X(CreateComputePipelines) \
    X(DestroyPipeline) \
    X(CreateDescriptorPool) \
    X(DestroyDescriptorPool) \
    X(AllocateDescriptorSets) \
    X(UpdateDescriptorSets) \
    X(CreateCommandPool) \
    X(DestroyCommandPool) \
    X(AllocateCommandBuffers) \
    X(BeginCommandBuffer) \
    X(EndCommandBuffer) \
    X(CmdBindPipeline) \
    X(CmdBindDescriptorSets) \
    X(CmdDispatch) \
    X(CmdPipelineBarrier) \
    X(CreateFence) \
    X(DestroyFence) \
    X(QueueSubmit) \
    X(WaitForFences)

struct DeviceFunctions {
#define DECLARE(name) PFN_vk##name name = nullptr;
    M0_DEVICE_COMMANDS(DECLARE)
#undef DECLARE

    const char* load(PFN_vkGetDeviceProcAddr resolve, VkDevice device) {
#define LOAD(name) \
    name = entry<PFN_vk##name>(resolve, device, "vk" #name); \
    if (!name) return "vk" #name;
        M0_DEVICE_COMMANDS(LOAD)
#undef LOAD
        return nullptr;
    }
};

#undef M0_DEVICE_COMMANDS

struct Workload {
    VkInstance instance = VK_NULL_HANDLE;
    PFN_vkDestroyInstance destroy_instance = nullptr;
    VkDevice device = VK_NULL_HANDLE;
    DeviceFunctions vk;
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    void* mapped = nullptr;
    bool coherent = false;
    VkShaderModule shader = VK_NULL_HANDLE;
    VkDescriptorSetLayout set_layout = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet set = VK_NULL_HANDLE;
    VkCommandPool command_pool = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;
    bool abandon = false;

    ~Workload() {
        if (abandon) return;
        if (device) {
            if (!vk.DestroyDevice) return;
            if (fence) vk.DestroyFence(device, fence, nullptr);
            if (command_pool) vk.DestroyCommandPool(device, command_pool, nullptr);
            if (pipeline) vk.DestroyPipeline(device, pipeline, nullptr);
            if (descriptor_pool) vk.DestroyDescriptorPool(device, descriptor_pool, nullptr);
            if (pipeline_layout) vk.DestroyPipelineLayout(device, pipeline_layout, nullptr);
            if (set_layout) vk.DestroyDescriptorSetLayout(device, set_layout, nullptr);
            if (shader) vk.DestroyShaderModule(device, shader, nullptr);
            if (mapped) vk.UnmapMemory(device, memory);
            if (buffer) vk.DestroyBuffer(device, buffer, nullptr);
            if (memory) vk.FreeMemory(device, memory, nullptr);
            vk.DestroyDevice(device, nullptr);
        }
        if (instance && destroy_instance) destroy_instance(instance, nullptr);
    }

    bool check(VkResult result, const char* stage) {
        if (result == VK_SUCCESS) return true;
        if (result == VK_ERROR_DEVICE_LOST) abandon = true;
        std::printf("{\"case_id\":\"%s\",\"status\":\"ERROR\",\"stage\":\"%s\",\"vk_result\":%d}\n",
                    case_id, stage, static_cast<int>(result));
        return false;
    }

    template <typename Handle, typename Function, typename... Args>
    bool acquire(Handle& handle, const char* stage, Function function, Args... args) {
        Handle output{};
        if (!check(function(args..., &output), stage)) return false;
        if (!output) {
            diagnostic("ERROR", stage, "success_without_output");
            return false;
        }
        handle = output;
        return true;
    }
};

struct Candidate {
    VkPhysicalDevice device = VK_NULL_HANDLE;
    VkPhysicalDeviceProperties properties{};
    VkPhysicalDeviceMemoryProperties memory{};
    std::uint32_t queue_family = 0;
};

bool meets_limits(const VkPhysicalDeviceLimits& limits) {
    return limits.maxComputeWorkGroupInvocations >= workgroup_size
        && limits.maxComputeWorkGroupSize[0] >= workgroup_size
        && limits.maxComputeWorkGroupCount[0] >= group_count
        && limits.maxStorageBufferRange >= buffer_size
        && limits.maxMemoryAllocationCount >= 1
        && limits.maxBoundDescriptorSets >= 1
        && limits.maxPerStageDescriptorStorageBuffers >= 1
        && limits.maxDescriptorSetStorageBuffers >= 1
        && limits.maxPerStageResources >= 1;
}

bool choose_device(Workload& state, PFN_vkGetInstanceProcAddr resolve, Candidate& candidate) {
    const auto enumerate = entry<PFN_vkEnumeratePhysicalDevices>(resolve, state.instance, "vkEnumeratePhysicalDevices");
    const auto properties = entry<PFN_vkGetPhysicalDeviceProperties>(resolve, state.instance, "vkGetPhysicalDeviceProperties");
    const auto memory = entry<PFN_vkGetPhysicalDeviceMemoryProperties>(resolve, state.instance, "vkGetPhysicalDeviceMemoryProperties");
    const auto queues = entry<PFN_vkGetPhysicalDeviceQueueFamilyProperties>(resolve, state.instance, "vkGetPhysicalDeviceQueueFamilyProperties");
    if (!enumerate || !properties || !memory || !queues) {
        diagnostic("ERROR", "instance_dispatch", "missing_device_discovery_entrypoint");
        return false;
    }

    std::uint32_t count = 0;
    if (!state.check(enumerate(state.instance, &count, nullptr), "vkEnumeratePhysicalDevices")) return false;
    if (count == 0) {
        diagnostic("UNSUPPORTED", "device_selection", "no_physical_devices");
        return false;
    }
    std::array<VkPhysicalDevice, 32> devices{};
    if (count > devices.size()) {
        diagnostic("ERROR", "device_selection", "physical_device_count_exceeds_fixture_limit");
        return false;
    }
    if (!state.check(enumerate(state.instance, &count, devices.data()), "vkEnumeratePhysicalDevices")) return false;

    const char* unmet_requirement = "compute_and_storage_limits";
    for (std::uint32_t i = 0; i < count; ++i) {
        properties(devices[i], &candidate.properties);
        if (candidate.properties.apiVersion < VK_API_VERSION_1_0 || !meets_limits(candidate.properties.limits)) {
            continue;
        }

        std::uint32_t family_count = 0;
        queues(devices[i], &family_count, nullptr);
        unmet_requirement = "no_compute_queue";
        if (family_count == 0) continue;
        std::array<VkQueueFamilyProperties, 64> families{};
        if (family_count > families.size()) {
            diagnostic("ERROR", "device_selection", "queue_family_count_exceeds_fixture_limit");
            return false;
        }
        queues(devices[i], &family_count, families.data());
        for (std::uint32_t j = 0; j < family_count; ++j) {
            if (families[j].queueCount && (families[j].queueFlags & VK_QUEUE_COMPUTE_BIT)) {
                candidate.device = devices[i];
                candidate.queue_family = j;
                memory(candidate.device, &candidate.memory);
                return true;
            }
        }
    }

    diagnostic("UNSUPPORTED", "device_selection", unmet_requirement);
    return false;
}

std::uint32_t memory_type(const VkPhysicalDeviceMemoryProperties& properties, std::uint32_t type_bits,
                         VkDeviceSize size) {
    constexpr VkMemoryPropertyFlags core_type_flags = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
        | VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
        | VK_MEMORY_PROPERTY_HOST_CACHED_BIT;
    constexpr VkMemoryHeapFlags core_heap_flags = VK_MEMORY_HEAP_DEVICE_LOCAL_BIT;
    std::uint32_t best = VK_MAX_MEMORY_TYPES;
    for (std::uint32_t i = 0; i < properties.memoryTypeCount; ++i) {
        const VkMemoryType& type = properties.memoryTypes[i];
        if (!(type_bits & (std::uint32_t{1} << i))
            || !(type.propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)
            || (type.propertyFlags & ~core_type_flags)) {
            continue;
        }
        const VkMemoryHeap& heap = properties.memoryHeaps[type.heapIndex];
        if ((heap.flags & ~core_heap_flags) || heap.size < size) {
            continue;
        }
        if (type.propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) return i;
        if (best == VK_MAX_MEMORY_TYPES) best = i;
    }
    return best;
}

bool prepare_buffer(Workload& state, const Candidate& candidate) {
    auto& vk = state.vk;
    const VkDevice device = state.device;
    VkBufferCreateInfo buffer_info{};
    buffer_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    buffer_info.size = buffer_size;
    buffer_info.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    if (!state.acquire(state.buffer, "vkCreateBuffer", vk.CreateBuffer, device, &buffer_info, nullptr)) return false;

    VkMemoryRequirements requirements{};
    vk.GetBufferMemoryRequirements(device, state.buffer, &requirements);
    if (requirements.size < buffer_size) {
        diagnostic("ERROR", "buffer_memory_requirements", "driver_reported_impossible_allocation_size");
        return false;
    }
    if (requirements.size > allocation_limit) {
        diagnostic("UNSUPPORTED", "buffer_memory_requirements", "allocation_exceeds_1_mib");
        return false;
    }

    if (candidate.memory.memoryTypeCount > VK_MAX_MEMORY_TYPES
        || candidate.memory.memoryHeapCount > VK_MAX_MEMORY_HEAPS) {
        diagnostic("ERROR", "buffer_memory_requirements", "driver_reported_invalid_memory_counts");
        return false;
    }
    for (std::uint32_t i = 0; i < candidate.memory.memoryTypeCount; ++i) {
        if (candidate.memory.memoryTypes[i].heapIndex >= candidate.memory.memoryHeapCount) {
            diagnostic("ERROR", "buffer_memory_requirements", "driver_reported_invalid_memory_heap_index");
            return false;
        }
    }

    const std::uint32_t type = memory_type(candidate.memory, requirements.memoryTypeBits, requirements.size);
    if (type == VK_MAX_MEMORY_TYPES) {
        diagnostic("UNSUPPORTED", "buffer_memory_requirements", "no_compatible_core_host_visible_memory");
        return false;
    }
    state.coherent = (candidate.memory.memoryTypes[type].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) != 0;

    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = type;
    if (!state.acquire(state.memory, "vkAllocateMemory", vk.AllocateMemory, device, &allocation, nullptr)
        || !state.check(vk.BindBufferMemory(device, state.buffer, state.memory, 0), "vkBindBufferMemory")
        || !state.acquire(state.mapped, "vkMapMemory", vk.MapMemory, device, state.memory, 0, VK_WHOLE_SIZE, 0)) {
        return false;
    }

    std::memset(state.mapped, 0, buffer_size);
    VkMappedMemoryRange range{};
    range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
    range.memory = state.memory;
    range.size = VK_WHOLE_SIZE;
    return state.coherent || state.check(vk.FlushMappedMemoryRanges(device, 1, &range), "vkFlushMappedMemoryRanges");
}

bool prepare_pipeline(Workload& state) {
    auto& vk = state.vk;
    const VkDevice device = state.device;
    VkShaderModuleCreateInfo shader_info{};
    shader_info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    shader_info.codeSize = sizeof(m0_radv_compute_spv);
    shader_info.pCode = m0_radv_compute_spv;
    if (!state.acquire(state.shader, "vkCreateShaderModule", vk.CreateShaderModule, device, &shader_info, nullptr)) {
        return false;
    }

    VkDescriptorSetLayoutBinding binding{};
    binding.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    binding.descriptorCount = 1;
    binding.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    VkDescriptorSetLayoutCreateInfo set_layout_info{};
    set_layout_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    set_layout_info.bindingCount = 1;
    set_layout_info.pBindings = &binding;
    if (!state.acquire(state.set_layout, "vkCreateDescriptorSetLayout", vk.CreateDescriptorSetLayout,
                       device, &set_layout_info, nullptr)) return false;

    VkPipelineLayoutCreateInfo layout_info{};
    layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    layout_info.setLayoutCount = 1;
    layout_info.pSetLayouts = &state.set_layout;
    if (!state.acquire(state.pipeline_layout, "vkCreatePipelineLayout", vk.CreatePipelineLayout,
                       device, &layout_info, nullptr)) return false;

    VkComputePipelineCreateInfo pipeline_info{};
    pipeline_info.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
    pipeline_info.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    pipeline_info.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    pipeline_info.stage.module = state.shader;
    pipeline_info.stage.pName = "main";
    pipeline_info.layout = state.pipeline_layout;
    pipeline_info.basePipelineIndex = -1;
    // Pipeline outputs are valid handles or VK_NULL_HANDLE even on failure.
    if (!state.check(vk.CreateComputePipelines(device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &state.pipeline),
                     "vkCreateComputePipelines")) return false;
    if (!state.pipeline) {
        diagnostic("ERROR", "vkCreateComputePipelines", "success_without_output");
        return false;
    }

    const VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1};
    VkDescriptorPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    pool_info.maxSets = 1;
    pool_info.poolSizeCount = 1;
    pool_info.pPoolSizes = &pool_size;
    if (!state.acquire(state.descriptor_pool, "vkCreateDescriptorPool", vk.CreateDescriptorPool,
                       device, &pool_info, nullptr)) return false;

    VkDescriptorSetAllocateInfo set_info{};
    set_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    set_info.descriptorPool = state.descriptor_pool;
    set_info.descriptorSetCount = 1;
    set_info.pSetLayouts = &state.set_layout;
    if (!state.acquire(state.set, "vkAllocateDescriptorSets", vk.AllocateDescriptorSets, device, &set_info)) {
        return false;
    }

    const VkDescriptorBufferInfo descriptor{state.buffer, 0, buffer_size};
    VkWriteDescriptorSet write{};
    write.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    write.dstSet = state.set;
    write.descriptorCount = 1;
    write.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    write.pBufferInfo = &descriptor;
    vk.UpdateDescriptorSets(device, 1, &write, 0, nullptr);
    return true;
}

bool submit_compute(Workload& state, const Candidate& candidate) {
    auto& vk = state.vk;
    const VkDevice device = state.device;
    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.queueFamilyIndex = candidate.queue_family;
    if (!state.acquire(state.command_pool, "vkCreateCommandPool", vk.CreateCommandPool, device, &pool_info, nullptr)) {
        return false;
    }

    VkCommandBufferAllocateInfo allocate{};
    allocate.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    allocate.commandPool = state.command_pool;
    allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate.commandBufferCount = 1;
    VkCommandBuffer command = VK_NULL_HANDLE;
    if (!state.acquire(command, "vkAllocateCommandBuffers", vk.AllocateCommandBuffers, device, &allocate)) {
        return false;
    }

    VkCommandBufferBeginInfo begin{};
    begin.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (!state.check(vk.BeginCommandBuffer(command, &begin), "vkBeginCommandBuffer")) return false;

    vk.CmdBindPipeline(command, VK_PIPELINE_BIND_POINT_COMPUTE, state.pipeline);
    vk.CmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_COMPUTE, state.pipeline_layout,
                             0, 1, &state.set, 0, nullptr);
    vk.CmdDispatch(command, group_count, 1, 1);

    VkMemoryBarrier barrier{};
    barrier.sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER;
    barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT;
    barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
    vk.CmdPipelineBarrier(command, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                          0, 1, &barrier, 0, nullptr, 0, nullptr);
    if (!state.check(vk.EndCommandBuffer(command), "vkEndCommandBuffer")) return false;

    VkFenceCreateInfo fence_info{};
    fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    if (!state.acquire(state.fence, "vkCreateFence", vk.CreateFence, device, &fence_info, nullptr)) return false;

    VkQueue queue = VK_NULL_HANDLE;
    vk.GetDeviceQueue(device, candidate.queue_family, 0, &queue);
    if (!queue) {
        diagnostic("ERROR", "vkGetDeviceQueue", "queue_is_null");
        return false;
    }
    VkSubmitInfo submit{};
    submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &command;
    if (!state.check(vk.QueueSubmit(queue, 1, &submit, state.fence), "vkQueueSubmit")) return false;

    // Only successful wait proves the submitted resources can be destroyed.
    state.abandon = true;
    const VkResult waited = vk.WaitForFences(device, 1, &state.fence, VK_TRUE, fence_timeout_ns);
    if (waited == VK_TIMEOUT) {
        std::printf("{\"case_id\":\"%s\",\"status\":\"TIMEOUT\",\"stage\":\"vkWaitForFences\","
                    "\"timeout_ns\":%" PRIu64 "}\n", case_id, fence_timeout_ns);
        return false;
    }
    if (!state.check(waited, "vkWaitForFences")) return false;
    state.abandon = false;

    VkMappedMemoryRange range{};
    range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
    range.memory = state.memory;
    range.size = VK_WHOLE_SIZE;
    return state.coherent
        || state.check(vk.InvalidateMappedMemoryRanges(device, 1, &range), "vkInvalidateMappedMemoryRanges");
}

int verify_words(const Workload& state, const Candidate& candidate) {
    const auto* values = static_cast<const unsigned char*>(state.mapped);
    std::uint32_t wrong = 0;
    std::uint32_t first = 0;
    std::uint32_t first_actual = 0;
    for (std::uint32_t i = 0; i < word_count; ++i) {
        std::uint32_t actual = 0;
        std::memcpy(&actual, values + i * sizeof(actual), sizeof(actual));
        if (actual == i * 3u + 7u) continue;
        if (wrong == 0) {
            first = i;
            first_actual = actual;
        }
        ++wrong;
    }
    if (wrong != 0) {
        std::printf("{\"case_id\":\"%s\",\"status\":\"FAIL\",\"checked_words\":%" PRIu32
                    ",\"mismatch_count\":%" PRIu32 ",\"first_mismatch_index\":%" PRIu32
                    ",\"first_mismatch_expected\":%" PRIu32 ",\"first_mismatch_actual\":%" PRIu32 "}\n",
                    case_id, word_count, wrong, first, first * 3u + 7u, first_actual);
        return 1;
    }

    std::printf("{\"case_id\":\"%s\",\"status\":\"PASS\",\"checked_words\":%" PRIu32
                ",\"vendor_id\":%" PRIu32 ",\"device_id\":%" PRIu32 ",\"api_version\":%" PRIu32
                ",\"queue_family\":%" PRIu32 ",\"host_coherent\":%s}\n",
                case_id, word_count, candidate.properties.vendorID, candidate.properties.deviceID,
                candidate.properties.apiVersion, candidate.queue_family, state.coherent ? "true" : "false");
    return 0;
}

} // namespace

int m0_radv_compute(PFN_vkGetInstanceProcAddr resolve) {
    if (!resolve) return diagnostic("ERROR", "global_dispatch", "missing_instance_resolver");
    const auto create_instance = entry<PFN_vkCreateInstance>(resolve, VkInstance{}, "vkCreateInstance");
    if (!create_instance) return diagnostic("ERROR", "global_dispatch", "missing_vkCreateInstance");

    Workload state;
    VkApplicationInfo application{};
    application.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    application.pApplicationName = case_id;
    application.apiVersion = VK_API_VERSION_1_0;
    VkInstanceCreateInfo instance_info{};
    instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_info.pApplicationInfo = &application;
    if (!state.acquire(state.instance, "vkCreateInstance", create_instance, &instance_info, nullptr)) return 1;

    state.destroy_instance = entry<PFN_vkDestroyInstance>(resolve, state.instance, "vkDestroyInstance");
    const auto create_device = entry<PFN_vkCreateDevice>(resolve, state.instance, "vkCreateDevice");
    const auto device_proc = entry<PFN_vkGetDeviceProcAddr>(resolve, state.instance, "vkGetDeviceProcAddr");
    if (!state.destroy_instance || !create_device || !device_proc) {
        return diagnostic("ERROR", "instance_dispatch", "missing_device_creation_entrypoint");
    }

    Candidate candidate;
    if (!choose_device(state, resolve, candidate)) return 1;

    const float priority = 1.0f;
    VkDeviceQueueCreateInfo queue_info{};
    queue_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_info.queueFamilyIndex = candidate.queue_family;
    queue_info.queueCount = 1;
    queue_info.pQueuePriorities = &priority;
    VkDeviceCreateInfo device_info{};
    device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device_info.queueCreateInfoCount = 1;
    device_info.pQueueCreateInfos = &queue_info;
    if (!state.acquire(state.device, "vkCreateDevice", create_device, candidate.device, &device_info, nullptr)) return 1;
    if (const char* missing = state.vk.load(device_proc, state.device)) {
        return diagnostic("ERROR", "device_dispatch", missing);
    }

    if (!prepare_buffer(state, candidate) || !prepare_pipeline(state) || !submit_compute(state, candidate)) {
        return 1;
    }
    return verify_words(state, candidate);
}
