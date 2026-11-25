// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>
#include <string>
#include <vulkan/vulkan.h>

namespace m1 {

struct Inventory {
    Inventory() = default;
    Inventory(const Inventory&) = delete;
    Inventory& operator=(const Inventory&) = delete;
    ~Inventory();

    VkInstance instance = VK_NULL_HANDLE;
    PFN_vkDestroyInstance destroy_instance = nullptr;
    VkPhysicalDevice physical = VK_NULL_HANDLE;
    VkPhysicalDeviceProperties properties{};
    VkPhysicalDeviceMemoryProperties memory{};
    uint32_t queue_family = UINT32_MAX;
    uint32_t api_version = VK_API_VERSION_1_0;
    PFN_vkGetInstanceProcAddr resolver = nullptr;
    bool abandon = false;
    std::string json = "null";
    std::string reason;
};

bool discover(Inventory& inventory, PFN_vkGetInstanceProcAddr resolver, uint32_t index);

}  // namespace m1
