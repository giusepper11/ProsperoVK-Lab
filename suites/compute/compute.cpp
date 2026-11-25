// SPDX-License-Identifier: GPL-3.0-or-later
#include "compute.hpp"

#include <array>
#include <chrono>
#include <cstring>
#include <utility>

#include "compute_spv.hpp"

namespace m1 {
namespace {

constexpr std::uint32_t workgroup_size = 64;
constexpr std::uint32_t group_count = 1;
constexpr std::uint32_t word_count = workgroup_size + 2;
constexpr VkDeviceSize buffer_size = word_count * sizeof(std::uint32_t);
constexpr VkDeviceSize allocation_limit = 1024 * 1024;
constexpr std::uint64_t fence_timeout_ns = 5'000'000'000;
constexpr std::uint32_t first_guard = 0xa5a5a5a5u;
constexpr std::uint32_t last_guard = 0x5a5a5a5au;

// Device lifetime, mapped-memory synchronization and dispatch follow the M0 RADV probe.
template <typename T, typename Resolve, typename Handle>
T entry(Resolve resolve, Handle handle, const char* name) {
    return reinterpret_cast<T>(resolve(handle, name));
}

#define M1_DEVICE_COMMANDS(X) \
    X(GetDeviceQueue) \
    X(CreateBuffer) \
    X(DestroyBuffer) \
    X(GetBufferMemoryRequirements) \
    X(AllocateMemory) \
    X(FreeMemory) \
    X(BindBufferMemory) \
    X(MapMemory) \
    X(UnmapMemory) \
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
    PFN_vkDestroyDevice DestroyDevice = nullptr;
    PFN_vkFlushMappedMemoryRanges FlushMappedMemoryRanges = nullptr;
    PFN_vkInvalidateMappedMemoryRanges InvalidateMappedMemoryRanges = nullptr;

#define DECLARE(name) PFN_vk##name name = nullptr;
    M1_DEVICE_COMMANDS(DECLARE)
#undef DECLARE

    const char* load(PFN_vkGetDeviceProcAddr resolve, VkDevice device) {
#define LOAD(name) \
    name = entry<PFN_vk##name>(resolve, device, "vk" #name); \
    if (!name) return "vk" #name;
        M1_DEVICE_COMMANDS(LOAD)
#undef LOAD
        return nullptr;
    }
};

#undef M1_DEVICE_COMMANDS

struct Workload {
    Inventory& inventory;
    Outcome& outcome;

    Workload(Inventory& inventory, Outcome& outcome) : inventory(inventory), outcome(outcome) {}
    Workload(const Workload&) = delete;
    Workload& operator=(const Workload&) = delete;
    VkDevice device = VK_NULL_HANDLE;
    DeviceFunctions vk;
    VkBuffer buffer = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    void* mapped = nullptr;
    bool coherent = false;
    VkMemoryPropertyFlags memory_flags = 0;
    VkShaderModule shader = VK_NULL_HANDLE;
    VkDescriptorSetLayout set_layout = VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkDescriptorPool descriptor_pool = VK_NULL_HANDLE;
    VkDescriptorSet set = VK_NULL_HANDLE;
    VkCommandPool command_pool = VK_NULL_HANDLE;
    VkCommandBuffer command = VK_NULL_HANDLE;
    VkQueue queue = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;

    ~Workload() {
        if (inventory.abandon) return;
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
    }

    bool fail(const char* status, std::string reason) {
        outcome.status = status;
        outcome.reason = std::move(reason);
        if (outcome.status == "UNSUPPORTED") outcome.eligibility = "unmet";
        return false;
    }

    bool check(VkResult result, const char* stage) {
        if (result == VK_SUCCESS) return true;
        if (result == VK_ERROR_DEVICE_LOST) inventory.abandon = true;
        const std::string cause = result == VK_ERROR_DEVICE_LOST ? " (VK_ERROR_DEVICE_LOST)" : "";
        return fail("ERROR", std::string(stage) + " returned " + std::to_string(result) + cause);
    }

    template <typename Handle, typename Function, typename... Args>
    bool acquire(Handle& handle, const char* stage, Function function, Args... args) {
        Handle output{};
        if (!check(function(args..., &output), stage)) return false;
        if (!output) return fail("ERROR", std::string(stage) + " succeeded without an output");
        handle = output;
        return true;
    }
};

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
        if (type.heapIndex >= properties.memoryHeapCount) continue;
        const VkMemoryHeap& heap = properties.memoryHeaps[type.heapIndex];
        if ((heap.flags & ~core_heap_flags) || heap.size < size) {
            continue;
        }
        if (type.propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) return i;
        if (best == VK_MAX_MEMORY_TYPES) best = i;
    }
    return best;
}

VkMappedMemoryRange mapped_range(const Workload& state) {
    VkMappedMemoryRange range{};
    range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
    range.memory = state.memory;
    // Map and synchronize the entire allocation from offset zero, including any padding.
    range.size = VK_WHOLE_SIZE;
    return range;
}

bool prepare_buffer(Workload& state, PFN_vkGetDeviceProcAddr resolve) {
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
        return state.fail("ERROR", "vkGetBufferMemoryRequirements reported a size smaller than the buffer");
    }
    if (requirements.size > allocation_limit) {
        return state.fail("UNSUPPORTED", "buffer allocation requirement exceeds the 1 MiB ceiling");
    }

    const auto& memory = state.inventory.memory;
    const std::uint32_t type = memory_type(memory, requirements.memoryTypeBits, requirements.size);
    if (type == VK_MAX_MEMORY_TYPES) {
        return state.fail("UNSUPPORTED", "buffer memoryTypeBits and allocation size admit no Vulkan 1.0 host-visible memory type");
    }
    state.outcome.eligibility = "met";
    state.memory_flags = memory.memoryTypes[type].propertyFlags;
    state.coherent = (state.memory_flags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT) != 0;
    if (!state.coherent) {
        vk.FlushMappedMemoryRanges = entry<PFN_vkFlushMappedMemoryRanges>(resolve, device, "vkFlushMappedMemoryRanges");
        vk.InvalidateMappedMemoryRanges =
            entry<PFN_vkInvalidateMappedMemoryRanges>(resolve, device, "vkInvalidateMappedMemoryRanges");
        if (!vk.FlushMappedMemoryRanges || !vk.InvalidateMappedMemoryRanges) {
            return state.fail("ERROR", "missing mapped-memory synchronization entry point");
        }
    }

    VkMemoryAllocateInfo allocation{};
    allocation.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = type;
    if (!state.acquire(state.memory, "vkAllocateMemory", vk.AllocateMemory, device, &allocation, nullptr)
        || !state.check(vk.BindBufferMemory(device, state.buffer, state.memory, 0), "vkBindBufferMemory")
        || !state.acquire(state.mapped, "vkMapMemory", vk.MapMemory, device, state.memory, 0, VK_WHOLE_SIZE, 0)) {
        return false;
    }

    std::array<std::uint32_t, word_count> initial{};
    initial.front() = first_guard;
    initial.back() = last_guard;
    std::memcpy(state.mapped, initial.data(), buffer_size);
    const auto range = mapped_range(state);
    if (!state.coherent && !state.check(vk.FlushMappedMemoryRanges(device, 1, &range), "vkFlushMappedMemoryRanges")) {
        return false;
    }

    auto& enabled = state.outcome.enabled;
    enabled.pop_back();
    enabled += ",\"buffer_memory\":{\"memory_type_index\":" + std::to_string(type)
        + ",\"memory_property_flags\":" + std::to_string(state.memory_flags)
        + ",\"allocation_bytes\":" + std::to_string(requirements.size) + "}}";
    return true;
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
    if (!state.pipeline) return state.fail("ERROR", "vkCreateComputePipelines succeeded without an output");

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

bool record_compute(Workload& state, std::uint32_t queue_family) {
    auto& vk = state.vk;
    const VkDevice device = state.device;
    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.queueFamilyIndex = queue_family;
    if (!state.acquire(state.command_pool, "vkCreateCommandPool", vk.CreateCommandPool, device, &pool_info, nullptr)) {
        return false;
    }

    VkCommandBufferAllocateInfo allocate{};
    allocate.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    allocate.commandPool = state.command_pool;
    allocate.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate.commandBufferCount = 1;
    if (!state.acquire(state.command, "vkAllocateCommandBuffers", vk.AllocateCommandBuffers, device, &allocate)) {
        return false;
    }

    const VkCommandBuffer command = state.command;
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

    vk.GetDeviceQueue(device, queue_family, 0, &state.queue);
    if (!state.queue) return state.fail("ERROR", "vkGetDeviceQueue returned a null queue");
    return true;
}

struct HostTiming {
    std::int64_t submission_ns;
    std::int64_t fence_wait_ns;
    std::int64_t completion_ns;
};

bool submit_compute(Workload& state, HostTiming& timing) {
    auto& vk = state.vk;
    VkSubmitInfo submit{};
    submit.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers = &state.command;

    using Clock = std::chrono::steady_clock;
    const auto started = Clock::now();
    const VkResult submitted = vk.QueueSubmit(state.queue, 1, &submit, state.fence);
    const auto submit_finished = Clock::now();
    if (!state.check(submitted, "vkQueueSubmit")) return false;

    // A successful wait proves it is safe to destroy resources used by the queue.
    state.inventory.abandon = true;
    const auto wait_started = Clock::now();
    const VkResult waited = vk.WaitForFences(state.device, 1, &state.fence, VK_TRUE, fence_timeout_ns);
    const auto finished = Clock::now();
    if (waited == VK_TIMEOUT) return state.fail("TIMEOUT", "vkWaitForFences returned VK_TIMEOUT with a 5-second limit");
    if (!state.check(waited, "vkWaitForFences")) return false;
    state.inventory.abandon = false;

    using std::chrono::duration_cast;
    using std::chrono::nanoseconds;
    timing = {duration_cast<nanoseconds>(submit_finished - started).count(),
              duration_cast<nanoseconds>(finished - wait_started).count(),
              duration_cast<nanoseconds>(finished - started).count()};

    const auto range = mapped_range(state);
    return state.coherent || state.check(vk.InvalidateMappedMemoryRanges(state.device, 1, &range),
                                         "vkInvalidateMappedMemoryRanges");
}

bool verify_words(Workload& state) {
    std::array<std::uint32_t, word_count> actual{};
    std::memcpy(actual.data(), state.mapped, buffer_size);
    std::array<std::uint32_t, word_count> expected{};
    expected.front() = first_guard;
    expected.back() = last_guard;
    for (std::uint32_t i = 0; i < workgroup_size; ++i) expected[i + 1] = 0x12340000u ^ i;

    std::uint32_t wrong = 0;
    std::string first_mismatch = "null";
    for (std::uint32_t i = 0; i < word_count; ++i) {
        if (actual[i] == expected[i]) continue;
        if (wrong == 0) {
            first_mismatch = "{\"index\":" + std::to_string(i)
                + ",\"expected\":" + std::to_string(expected[i])
                + ",\"actual\":" + std::to_string(actual[i]) + "}";
        }
        ++wrong;
    }
    state.outcome.correctness = "{\"checked_words\":" + std::to_string(word_count)
        + ",\"output_words\":" + std::to_string(workgroup_size)
        + ",\"guard_words\":2,\"mismatch_count\":" + std::to_string(wrong)
        + ",\"first_mismatch\":" + first_mismatch + "}";
    return wrong == 0 || state.fail("FAIL", "exact readback differs from the CPU oracle");
}

bool preflight(Workload& state) {
    const auto& inventory = state.inventory;
    if (inventory.abandon) {
        return state.fail("ERROR", "Vulkan state was abandoned and requires recovery before further submission");
    }
    if (inventory.api_version < VK_API_VERSION_1_0 || inventory.properties.apiVersion < VK_API_VERSION_1_0) {
        return state.fail("UNSUPPORTED", "requires Vulkan 1.0");
    }
    if (inventory.queue_family == UINT32_MAX) {
        return state.fail("UNSUPPORTED", "requires a compute queue family with at least one queue");
    }

    const auto& limits = inventory.properties.limits;
    struct Limit {
        const char* name;
        std::uint32_t available;
        std::uint32_t required;
    };
    const Limit required_limits[] = {
        {"maxComputeWorkGroupInvocations", limits.maxComputeWorkGroupInvocations, workgroup_size},
        {"maxComputeWorkGroupSize[0]", limits.maxComputeWorkGroupSize[0], workgroup_size},
        {"maxComputeWorkGroupSize[1]", limits.maxComputeWorkGroupSize[1], 1},
        {"maxComputeWorkGroupSize[2]", limits.maxComputeWorkGroupSize[2], 1},
        {"maxComputeWorkGroupCount[0]", limits.maxComputeWorkGroupCount[0], group_count},
        {"maxComputeWorkGroupCount[1]", limits.maxComputeWorkGroupCount[1], 1},
        {"maxComputeWorkGroupCount[2]", limits.maxComputeWorkGroupCount[2], 1},
        {"maxStorageBufferRange", limits.maxStorageBufferRange, static_cast<std::uint32_t>(buffer_size)},
        {"maxMemoryAllocationCount", limits.maxMemoryAllocationCount, 1},
        {"maxBoundDescriptorSets", limits.maxBoundDescriptorSets, 1},
        {"maxPerStageDescriptorStorageBuffers", limits.maxPerStageDescriptorStorageBuffers, 1},
        {"maxDescriptorSetStorageBuffers", limits.maxDescriptorSetStorageBuffers, 1},
        {"maxPerStageResources", limits.maxPerStageResources, 1},
    };
    for (const auto& limit : required_limits) {
        if (limit.available < limit.required) {
            return state.fail("UNSUPPORTED", std::string(limit.name) + " is " + std::to_string(limit.available)
                              + " and requires at least " + std::to_string(limit.required));
        }
    }

    const auto& memory = inventory.memory;
    if (memory.memoryTypeCount > VK_MAX_MEMORY_TYPES || memory.memoryHeapCount > VK_MAX_MEMORY_HEAPS) {
        return state.fail("ERROR", "invalid physical-device memory type or heap count");
    }
    for (std::uint32_t i = 0; i < memory.memoryTypeCount; ++i) {
        if (memory.memoryTypes[i].heapIndex >= memory.memoryHeapCount) {
            return state.fail("ERROR", "invalid physical-device memory heap index");
        }
    }
    if (memory_type(memory, UINT32_MAX, buffer_size) == VK_MAX_MEMORY_TYPES) {
        return state.fail("UNSUPPORTED", "requires Vulkan 1.0 host-visible memory for the storage buffer");
    }
    return true;
}

} // namespace

Outcome compute(Inventory& inventory) {
    Outcome outcome;
    outcome.requirements = "{\"minimum_api_version\":\"1.0\",\"required_extensions\":[],\"required_features\":[],"
        "\"required_formats\":[],\"queue_flags\":\"VK_QUEUE_COMPUTE_BIT\",\"queue_count\":1,"
        "\"local_size\":[64,1,1],\"group_count\":[1,1,1],\"storage_buffer_descriptors\":1,"
        "\"bound_descriptor_sets\":1,\"storage_buffer_bytes\":" + std::to_string(buffer_size)
        + ",\"memory_property_required\":\"VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT\",\"memory_allocation_count\":1,"
        "\"max_allocation_bytes\":" + std::to_string(allocation_limit)
        + ",\"fence_timeout_ns\":" + std::to_string(fence_timeout_ns) + "}";

    // Scope ownership so Vulkan teardown completes before the terminal result is returned.
    {
        Workload state(inventory, outcome);
        if (!preflight(state)) return outcome;
        if (!inventory.resolver) {
            state.fail("ERROR", "missing vkGetInstanceProcAddr");
            return outcome;
        }
        const auto create_device = entry<PFN_vkCreateDevice>(inventory.resolver, inventory.instance, "vkCreateDevice");
        const auto resolve = entry<PFN_vkGetDeviceProcAddr>(inventory.resolver, inventory.instance, "vkGetDeviceProcAddr");
        if (!create_device || !resolve) {
            state.fail("ERROR", "missing device creation or dispatch entry point");
            return outcome;
        }

        const float priority = 1.0f;
        VkDeviceQueueCreateInfo queue_info{};
        queue_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queue_info.queueFamilyIndex = inventory.queue_family;
        queue_info.queueCount = 1;
        queue_info.pQueuePriorities = &priority;
        VkDeviceCreateInfo device_info{};
        device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
        device_info.queueCreateInfoCount = 1;
        device_info.pQueueCreateInfos = &queue_info;
        if (!state.acquire(state.device, "vkCreateDevice", create_device, inventory.physical, &device_info, nullptr)) {
            return outcome;
        }

        outcome.enabled = "{\"api_path\":\"Vulkan 1.0 core\",\"extensions\":[],\"features\":[],"
            "\"queue_family\":" + std::to_string(inventory.queue_family) + ",\"queue_count\":1}";
        state.vk.DestroyDevice = entry<PFN_vkDestroyDevice>(resolve, state.device, "vkDestroyDevice");
        if (!state.vk.DestroyDevice) {
            state.vk.DestroyDevice = entry<PFN_vkDestroyDevice>(inventory.resolver, inventory.instance, "vkDestroyDevice");
            inventory.abandon = !state.vk.DestroyDevice;
            state.fail("ERROR", "device dispatch is missing vkDestroyDevice");
            return outcome;
        }
        if (const char* missing = state.vk.load(resolve, state.device)) {
            state.fail("ERROR", std::string("device dispatch is missing ") + missing);
            return outcome;
        }

        HostTiming timing{};
        if (!prepare_buffer(state, resolve) || !prepare_pipeline(state) || !record_compute(state, inventory.queue_family)
            || !submit_compute(state, timing) || !verify_words(state)) return outcome;

        outcome.status = "PASS";
        outcome.timing = "{\"scope\":\"correctness_dispatch\",\"clock\":\"steady_clock\","
            "\"gpu_execution_ns\":null,\"gpu_timing_unavailable_reason\":\"timestamps_not_measured_by_case\","
            "\"cpu_queue_submit_ns\":" + std::to_string(timing.submission_ns)
            + ",\"cpu_fence_wait_ns\":" + std::to_string(timing.fence_wait_ns)
            + ",\"cpu_submit_to_completion_ns\":" + std::to_string(timing.completion_ns) + "}";
    }
    return outcome;
}

} // namespace m1
