// SPDX-License-Identifier: GPL-3.0-or-later
#include "vulkan/inventory.hpp"

#include <cstring>
#include <iostream>
#include <type_traits>

namespace {

template <typename Handle>
Handle fake_handle() {
    if constexpr (std::is_pointer_v<Handle>) {
        static int storage;
        return reinterpret_cast<Handle>(&storage);
    } else {
        return static_cast<Handle>(1);
    }
}

bool advertise_properties2;
bool compute_queue;
unsigned destroy_calls;
unsigned baseline_feature_calls;
unsigned extended_property_calls;
unsigned extended_feature_calls;
bool enabled_properties2;

VKAPI_ATTR VkResult VKAPI_CALL create(const VkInstanceCreateInfo* info, const VkAllocationCallbacks*,
                                      VkInstance* instance) {
    enabled_properties2 = info->enabledExtensionCount == 1 &&
                          std::strcmp(info->ppEnabledExtensionNames[0],
                                      VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME) == 0;
    *instance = fake_handle<VkInstance>();
    return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL destroy(VkInstance, const VkAllocationCallbacks*) {
    ++destroy_calls;
}

VKAPI_ATTR VkResult VKAPI_CALL enumerate_instance(const char*, uint32_t* count, VkExtensionProperties* items) {
    *count = advertise_properties2 ? 1 : 0;
    if (items && *count) {
        std::strcpy(items[0].extensionName, VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME);
        items[0].specVersion = 2;
    }
    return VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL enumerate_devices(VkInstance, uint32_t* count, VkPhysicalDevice* items) {
    *count = 1;
    if (items) *items = fake_handle<VkPhysicalDevice>();
    return VK_SUCCESS;
}

VKAPI_ATTR VkResult VKAPI_CALL enumerate_device_extensions(VkPhysicalDevice, const char*, uint32_t* count,
                                                          VkExtensionProperties*) {
    *count = 0;
    return VK_SUCCESS;
}

VKAPI_ATTR void VKAPI_CALL properties(VkPhysicalDevice, VkPhysicalDeviceProperties* value) {
    value->apiVersion = VK_API_VERSION_1_0;
    std::strcpy(value->deviceName, "injected");
}

VKAPI_ATTR void VKAPI_CALL properties2(VkPhysicalDevice physical, VkPhysicalDeviceProperties2* value) {
    ++extended_property_calls;
    properties(physical, &value->properties);
}

VKAPI_ATTR void VKAPI_CALL features(VkPhysicalDevice, VkPhysicalDeviceFeatures* value) {
    ++baseline_feature_calls;
    value->robustBufferAccess = VK_TRUE;
}

VKAPI_ATTR void VKAPI_CALL features2(VkPhysicalDevice, VkPhysicalDeviceFeatures2* value) {
    ++extended_feature_calls;
    value->features.robustBufferAccess = VK_TRUE;
}

VKAPI_ATTR void VKAPI_CALL queues(VkPhysicalDevice, uint32_t* count, VkQueueFamilyProperties* items) {
    *count = 1;
    if (!items) return;
    items[0].queueCount = 1;
    items[0].queueFlags = compute_queue ? VK_QUEUE_COMPUTE_BIT : VK_QUEUE_GRAPHICS_BIT;
}

VKAPI_ATTR void VKAPI_CALL memory(VkPhysicalDevice, VkPhysicalDeviceMemoryProperties*) {}
VKAPI_ATTR void VKAPI_CALL formats(VkPhysicalDevice, VkFormat, VkFormatProperties*) {}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL resolver(VkInstance, const char* name) {
#define ENTRY(entrypoint, function) if (std::strcmp(name, "vk" #entrypoint) == 0) return reinterpret_cast<PFN_vkVoidFunction>(function)
    ENTRY(CreateInstance, create);
    ENTRY(DestroyInstance, destroy);
    ENTRY(EnumerateInstanceExtensionProperties, enumerate_instance);
    ENTRY(EnumeratePhysicalDevices, enumerate_devices);
    ENTRY(EnumerateDeviceExtensionProperties, enumerate_device_extensions);
    ENTRY(GetPhysicalDeviceProperties, properties);
    ENTRY(GetPhysicalDeviceProperties2KHR, properties2);
    ENTRY(GetPhysicalDeviceFeatures, features);
    ENTRY(GetPhysicalDeviceFeatures2KHR, features2);
    ENTRY(GetPhysicalDeviceQueueFamilyProperties, queues);
    ENTRY(GetPhysicalDeviceMemoryProperties, memory);
    ENTRY(GetPhysicalDeviceFormatProperties, formats);
#undef ENTRY
    return nullptr;
}

bool check_baseline() {
    m1::Inventory inventory;
    return m1::discover(inventory, resolver, 0) &&
           inventory.api_version == VK_API_VERSION_1_0 && inventory.queue_family == UINT32_MAX &&
           inventory.json.find("\"robustBufferAccess\":true") != std::string::npos &&
           inventory.json.find("\"queue_family\":null") != std::string::npos &&
           inventory.json.find("Requires Vulkan 1.1 or VK_KHR_get_physical_device_properties2") != std::string::npos &&
           !enabled_properties2 && baseline_feature_calls == 1 &&
           extended_property_calls == 0 && extended_feature_calls == 0;
}

bool check_extension() {
    advertise_properties2 = true;
    compute_queue = true;
    m1::Inventory inventory;
    return m1::discover(inventory, resolver, 0) &&
           inventory.api_version == VK_API_VERSION_1_0 && inventory.queue_family == 0 &&
           inventory.json.find("\"entrypoint\":\"vkGetPhysicalDeviceProperties2KHR\",\"reason\":null") != std::string::npos &&
           inventory.json.find("\"entrypoint\":\"vkGetPhysicalDeviceFeatures2KHR\",\"reason\":null") != std::string::npos &&
           inventory.json.find("\"robustBufferAccess\":true") != std::string::npos &&
           enabled_properties2 && baseline_feature_calls == 1 &&
           extended_property_calls == 1 && extended_feature_calls == 1;
}

bool check_index() {
    m1::Inventory inventory;
    return !m1::discover(inventory, resolver, 1) && inventory.physical == VK_NULL_HANDLE &&
           inventory.reason.find("Device index 1 is out of range") != std::string::npos;
}

}  // namespace

int main() {
    if (!check_baseline() || !check_extension() || !check_index() || destroy_calls != 3) {
        std::cerr << "Unexpected Vulkan inventory query path, selection, or cleanup\n";
        return 1;
    }
}
