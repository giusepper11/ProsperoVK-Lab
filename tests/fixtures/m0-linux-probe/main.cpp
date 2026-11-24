// SPDX-License-Identifier: GPL-3.0-or-later

#include <vulkan/vulkan.h>

#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void check(VkResult result, const char* operation) {
    if (result != VK_SUCCESS) {
        throw std::runtime_error(std::string(operation) + " returned " +
                                 std::to_string(result));
    }
}

struct Session {
    VkInstance instance = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;

    ~Session() {
        if (fence != VK_NULL_HANDLE) {
            vkDestroyFence(device, fence, nullptr);
        }
        if (device != VK_NULL_HANDLE) {
            vkDestroyDevice(device, nullptr);
        }
        if (instance != VK_NULL_HANDLE) {
            vkDestroyInstance(instance, nullptr);
        }
    }
};

int probe() {
    Session session;
    const VkInstanceCreateInfo instance_info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    VkInstance instance = VK_NULL_HANDLE;
    check(vkCreateInstance(&instance_info, nullptr, &instance), "vkCreateInstance");
    session.instance = instance;

    uint32_t device_count = 0;
    check(vkEnumeratePhysicalDevices(session.instance, &device_count, nullptr),
          "vkEnumeratePhysicalDevices(count)");
    std::vector<VkPhysicalDevice> devices(device_count);
    if (!devices.empty()) {
        check(vkEnumeratePhysicalDevices(session.instance, &device_count, devices.data()),
              "vkEnumeratePhysicalDevices(list)");
        devices.resize(device_count);
    }

    for (const VkPhysicalDevice physical_device : devices) {
        uint32_t queue_count = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(physical_device, &queue_count, nullptr);
        if (queue_count == 0) {
            continue;
        }
        std::vector<VkQueueFamilyProperties> families(queue_count);
        vkGetPhysicalDeviceQueueFamilyProperties(physical_device, &queue_count, families.data());
        for (uint32_t index = 0; index < queue_count; ++index) {
            if (families[index].queueCount == 0 || !(families[index].queueFlags & VK_QUEUE_COMPUTE_BIT)) {
                continue;
            }

            constexpr float priority = 1.0f;
            VkDeviceQueueCreateInfo queue_info{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
            queue_info.queueFamilyIndex = index;
            queue_info.queueCount = 1;
            queue_info.pQueuePriorities = &priority;
            VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
            device_info.queueCreateInfoCount = 1;
            device_info.pQueueCreateInfos = &queue_info;
            VkDevice device = VK_NULL_HANDLE;
            check(vkCreateDevice(physical_device, &device_info, nullptr, &device), "vkCreateDevice");
            session.device = device;

            VkQueue queue = VK_NULL_HANDLE;
            vkGetDeviceQueue(session.device, index, 0, &queue);
            const VkFenceCreateInfo fence_info{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
            VkFence fence = VK_NULL_HANDLE;
            check(vkCreateFence(session.device, &fence_info, nullptr, &fence), "vkCreateFence");
            session.fence = fence;
            const VkSubmitInfo submit_info{VK_STRUCTURE_TYPE_SUBMIT_INFO};
            check(vkQueueSubmit(queue, 1, &submit_info, session.fence), "vkQueueSubmit");
            const VkResult wait = vkWaitForFences(session.device, 1, &session.fence, VK_TRUE,
                                                  5'000'000'000ULL);
            if (wait != VK_SUCCESS) {
                // A failed wait can leave the fence in use. Exit this probe without touching it.
                std::fprintf(stderr, "vkWaitForFences returned %d\n", static_cast<int>(wait));
                std::fflush(stderr);
                std::_Exit(EXIT_FAILURE);
            }

            VkPhysicalDeviceProperties props{};
            vkGetPhysicalDeviceProperties(physical_device, &props);
            std::printf("device=%s api=%u.%u.%u type=%d queue=%u empty_submit=PASS\n",
                        props.deviceName, VK_API_VERSION_MAJOR(props.apiVersion),
                        VK_API_VERSION_MINOR(props.apiVersion), VK_API_VERSION_PATCH(props.apiVersion),
                        static_cast<int>(props.deviceType), index);
            return EXIT_SUCCESS;
        }
    }
    throw std::runtime_error("no compute-capable Vulkan queue found");
}

}  // namespace

int main() {
    try {
        return probe();
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what());
        return EXIT_FAILURE;
    }
}
