// SPDX-License-Identifier: GPL-3.0-or-later

#include "compute.hpp"

#include <cstdint>
#include <cstring>

namespace {

// The second measured dispatch follows one initial check and five warm-ups.
constexpr int fault_dispatch = 8;
int submissions = 0;
bool inject_timeout = false;
PFN_vkGetDeviceProcAddr get_device_proc = nullptr;
PFN_vkQueueSubmit queue_submit = nullptr;
PFN_vkWaitForFences wait_for_fences = nullptr;

VKAPI_ATTR VkResult VKAPI_CALL submit(VkQueue queue, std::uint32_t count, const VkSubmitInfo* info, VkFence fence) {
    ++submissions;
    if (!inject_timeout && submissions == fault_dispatch) {
        // Signal the fence without writing the storage buffer.
        return queue_submit(queue, 0, nullptr, fence);
    }
    return queue_submit(queue, count, info, fence);
}

VKAPI_ATTR VkResult VKAPI_CALL wait(VkDevice device, std::uint32_t count, const VkFence* fences,
                                   VkBool32 wait_all, std::uint64_t timeout) {
    const VkResult result = wait_for_fences(device, count, fences, wait_all, timeout);
    return inject_timeout && submissions == fault_dispatch && result == VK_SUCCESS ? VK_TIMEOUT : result;
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL device_proc(VkDevice device, const char* name) {
    const auto proc = get_device_proc(device, name);
    if (!proc) return nullptr;
    if (std::strcmp(name, "vkQueueSubmit") == 0) {
        queue_submit = reinterpret_cast<PFN_vkQueueSubmit>(proc);
        return reinterpret_cast<PFN_vkVoidFunction>(submit);
    }
    if (std::strcmp(name, "vkWaitForFences") == 0) {
        wait_for_fences = reinterpret_cast<PFN_vkWaitForFences>(proc);
        return reinterpret_cast<PFN_vkVoidFunction>(wait);
    }
    return proc;
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL instance_proc(VkInstance instance, const char* name) {
    const auto proc = vkGetInstanceProcAddr(instance, name);
    if (proc && std::strcmp(name, "vkGetDeviceProcAddr") == 0) {
        get_device_proc = reinterpret_cast<PFN_vkGetDeviceProcAddr>(proc);
        return reinterpret_cast<PFN_vkVoidFunction>(device_proc);
    }
    return proc;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    inject_timeout = std::strcmp(argv[1], "timeout") == 0;
    const int result = m0_radv_compute_timing(instance_proc, false);
    return submissions == fault_dispatch ? result : 2;
}
