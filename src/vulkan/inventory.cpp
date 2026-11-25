// SPDX-License-Identifier: GPL-3.0-or-later
#include "vulkan/inventory.hpp"

#include "core/json.hpp"

#include <algorithm>
#include <cstring>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <vector>

namespace m1 {
namespace {

template <typename Function>
Function resolve(Inventory& inventory, const char* name) {
    return reinterpret_cast<Function>(inventory.resolver(inventory.instance, name));
}

bool failed(Inventory& inventory, const char* operation, VkResult result) {
    inventory.reason = std::string(operation) + " returned VkResult " + std::to_string(result);
    return false;
}

template <typename Element, typename Query>
bool enumerate(Inventory& inventory, const char* name, std::vector<Element>& values, Query query) {
    constexpr uint32_t max_attempts = 4;
    for (uint32_t attempt = 0; attempt < max_attempts; ++attempt) {
        uint32_t count = 0;
        VkResult result = query(&count, nullptr);
        if (result == VK_INCOMPLETE) continue;
        if (result != VK_SUCCESS) return failed(inventory, name, result);
        values.resize(count);
        if (count == 0) return true;
        result = query(&count, values.data());
        if (result == VK_INCOMPLETE) continue;
        if (result != VK_SUCCESS) return failed(inventory, name, result);
        values.resize(count);
        return true;
    }
    return failed(inventory, name, VK_INCOMPLETE);
}

bool advertises(const std::vector<VkExtensionProperties>& extensions, const char* name) {
    return std::any_of(extensions.begin(), extensions.end(), [name](const auto& extension) {
        return std::strcmp(extension.extensionName, name) == 0;
    });
}

void write_extensions(std::ostream& out, std::vector<VkExtensionProperties>& extensions) {
    std::sort(extensions.begin(), extensions.end(), [](const auto& left, const auto& right) {
        return std::strcmp(left.extensionName, right.extensionName) < 0;
    });
    out << '[';
    const char* separator = "";
    for (const auto& extension : extensions) {
        out << separator << "{\"name\":" << quote(extension.extensionName)
            << ",\"spec_version\":" << extension.specVersion << '}';
        separator = ",";
    }
    out << ']';
}

void write_features(std::ostream& out, const VkPhysicalDeviceFeatures& features) {
    out << "{\"robustBufferAccess\":" << (features.robustBufferAccess ? "true" : "false");
#define FEATURE(name) out << ",\"" #name "\":" << (features.name ? "true" : "false")
    FEATURE(fullDrawIndexUint32);
    FEATURE(imageCubeArray);
    FEATURE(independentBlend);
    FEATURE(geometryShader);
    FEATURE(tessellationShader);
    FEATURE(sampleRateShading);
    FEATURE(dualSrcBlend);
    FEATURE(logicOp);
    FEATURE(multiDrawIndirect);
    FEATURE(drawIndirectFirstInstance);
    FEATURE(depthClamp);
    FEATURE(depthBiasClamp);
    FEATURE(fillModeNonSolid);
    FEATURE(depthBounds);
    FEATURE(wideLines);
    FEATURE(largePoints);
    FEATURE(alphaToOne);
    FEATURE(multiViewport);
    FEATURE(samplerAnisotropy);
    FEATURE(textureCompressionETC2);
    FEATURE(textureCompressionASTC_LDR);
    FEATURE(textureCompressionBC);
    FEATURE(occlusionQueryPrecise);
    FEATURE(pipelineStatisticsQuery);
    FEATURE(vertexPipelineStoresAndAtomics);
    FEATURE(fragmentStoresAndAtomics);
    FEATURE(shaderTessellationAndGeometryPointSize);
    FEATURE(shaderImageGatherExtended);
    FEATURE(shaderStorageImageExtendedFormats);
    FEATURE(shaderStorageImageMultisample);
    FEATURE(shaderStorageImageReadWithoutFormat);
    FEATURE(shaderStorageImageWriteWithoutFormat);
    FEATURE(shaderUniformBufferArrayDynamicIndexing);
    FEATURE(shaderSampledImageArrayDynamicIndexing);
    FEATURE(shaderStorageBufferArrayDynamicIndexing);
    FEATURE(shaderStorageImageArrayDynamicIndexing);
    FEATURE(shaderClipDistance);
    FEATURE(shaderCullDistance);
    FEATURE(shaderFloat64);
    FEATURE(shaderInt64);
    FEATURE(shaderInt16);
    FEATURE(shaderResourceResidency);
    FEATURE(shaderResourceMinLod);
    FEATURE(sparseBinding);
    FEATURE(sparseResidencyBuffer);
    FEATURE(sparseResidencyImage2D);
    FEATURE(sparseResidencyImage3D);
    FEATURE(sparseResidency2Samples);
    FEATURE(sparseResidency4Samples);
    FEATURE(sparseResidency8Samples);
    FEATURE(sparseResidency16Samples);
    FEATURE(sparseResidencyAliased);
    FEATURE(variableMultisampleRate);
    FEATURE(inheritedQueries);
#undef FEATURE
    out << '}';
}

void write_limits(std::ostream& out, const VkPhysicalDeviceLimits& limits) {
    out << "{\"maxComputeWorkGroupCount\":["
        << limits.maxComputeWorkGroupCount[0] << ',' << limits.maxComputeWorkGroupCount[1]
        << ',' << limits.maxComputeWorkGroupCount[2] << ']'
        << ",\"maxComputeWorkGroupSize\":["
        << limits.maxComputeWorkGroupSize[0] << ',' << limits.maxComputeWorkGroupSize[1]
        << ',' << limits.maxComputeWorkGroupSize[2] << ']';
#define LIMIT(name) out << ",\"" #name "\":" << limits.name
    LIMIT(maxComputeWorkGroupInvocations);
    LIMIT(maxComputeSharedMemorySize);
    LIMIT(maxBoundDescriptorSets);
    LIMIT(maxPerStageDescriptorStorageBuffers);
    LIMIT(maxPerStageResources);
    LIMIT(maxDescriptorSetStorageBuffers);
    LIMIT(maxStorageBufferRange);
    LIMIT(maxMemoryAllocationCount);
    LIMIT(minMemoryMapAlignment);
    LIMIT(minStorageBufferOffsetAlignment);
    LIMIT(nonCoherentAtomSize);
    LIMIT(maxImageDimension2D);
#undef LIMIT
    out << ",\"timestampPeriod\":" << std::setprecision(std::numeric_limits<float>::max_digits10)
        << limits.timestampPeriod
        << ",\"timestampComputeAndGraphics\":" << (limits.timestampComputeAndGraphics ? "true" : "false");
    out << '}';
}

void write_queues(std::ostream& out, const std::vector<VkQueueFamilyProperties>& queues) {
    out << '[';
    for (size_t i = 0; i < queues.size(); ++i) {
        const auto& queue = queues[i];
        if (i != 0) out << ',';
        out << "{\"index\":" << i << ",\"flags\":" << queue.queueFlags
            << ",\"count\":" << queue.queueCount
            << ",\"timestamp_valid_bits\":" << queue.timestampValidBits
            << ",\"min_image_transfer_granularity\":[" << queue.minImageTransferGranularity.width
            << ',' << queue.minImageTransferGranularity.height
            << ',' << queue.minImageTransferGranularity.depth << "]}";
    }
    out << ']';
}

void write_memory(std::ostream& out, const VkPhysicalDeviceMemoryProperties& memory) {
    out << "{\"types\":[";
    for (uint32_t i = 0; i < memory.memoryTypeCount; ++i) {
        if (i != 0) out << ',';
        out << "{\"index\":" << i << ",\"property_flags\":" << memory.memoryTypes[i].propertyFlags
            << ",\"heap_index\":" << memory.memoryTypes[i].heapIndex << '}';
    }
    out << "],\"heaps\":[";
    for (uint32_t i = 0; i < memory.memoryHeapCount; ++i) {
        if (i != 0) out << ',';
        out << "{\"index\":" << i << ",\"size\":" << memory.memoryHeaps[i].size
            << ",\"flags\":" << memory.memoryHeaps[i].flags << '}';
    }
    out << "]}";
}

void write_formats(std::ostream& out, VkPhysicalDevice physical, PFN_vkGetPhysicalDeviceFormatProperties query) {
    constexpr VkFormat formats[] = {VK_FORMAT_R8G8B8A8_UNORM, VK_FORMAT_B8G8R8A8_UNORM,
                                    VK_FORMAT_R32_UINT, VK_FORMAT_D32_SFLOAT};
    out << '[';
    const char* separator = "";
    for (VkFormat format : formats) {
        VkFormatProperties properties{};
        query(physical, format, &properties);
        out << separator << "{\"format\":" << format
            << ",\"linear_tiling_features\":" << properties.linearTilingFeatures
            << ",\"optimal_tiling_features\":" << properties.optimalTilingFeatures
            << ",\"buffer_features\":" << properties.bufferFeatures << '}';
        separator = ",";
    }
    out << ']';
}

std::string uuid(const uint8_t* bytes) {
    constexpr char digits[] = "0123456789abcdef";
    std::string value;
    value.reserve(VK_UUID_SIZE * 2);
    for (uint32_t i = 0; i < VK_UUID_SIZE; ++i) {
        value.push_back(digits[bytes[i] >> 4]);
        value.push_back(digits[bytes[i] & 15]);
    }
    return value;
}

void write_driver_properties(std::ostream& out, const VkPhysicalDeviceDriverProperties& driver,
                             const char* reason) {
    if (reason) {
        out << "{\"available\":false,\"reason\":" << quote(reason) << '}';
        return;
    }
    const auto& version = driver.conformanceVersion;
    out << "{\"available\":true,\"reason\":null,\"driver_id\":" << driver.driverID
        << ",\"name\":" << quote(driver.driverName) << ",\"info\":" << quote(driver.driverInfo)
        << ",\"conformance_version\":[" << static_cast<unsigned>(version.major) << ','
        << static_cast<unsigned>(version.minor) << ',' << static_cast<unsigned>(version.subminor) << ','
        << static_cast<unsigned>(version.patch) << "]}";
}

}  // namespace

Inventory::~Inventory() {
    if (instance && destroy_instance && !abandon) destroy_instance(instance, nullptr);
}

bool discover(Inventory& inventory, PFN_vkGetInstanceProcAddr resolver, uint32_t index) {
    if (inventory.instance) {
        inventory.reason = "Inventory already owns a Vulkan instance";
        return false;
    }
    inventory.reason.clear();
    inventory.resolver = resolver;
    if (!resolver) {
        inventory.reason = "Missing Vulkan instance resolver";
        return false;
    }

    auto create_instance = resolve<PFN_vkCreateInstance>(inventory, "vkCreateInstance");
    auto query_instance_extensions = resolve<PFN_vkEnumerateInstanceExtensionProperties>(
        inventory, "vkEnumerateInstanceExtensionProperties");
    if (!create_instance || !query_instance_extensions) {
        inventory.reason = !create_instance ? "Missing vkCreateInstance" : "Missing vkEnumerateInstanceExtensionProperties";
        return false;
    }
    auto query_version = resolve<PFN_vkEnumerateInstanceVersion>(inventory, "vkEnumerateInstanceVersion");
    uint32_t loader_version = VK_API_VERSION_1_0;
    if (query_version) {
        VkResult result = query_version(&loader_version);
        if (result != VK_SUCCESS) return failed(inventory, "vkEnumerateInstanceVersion", result);
    }
    const uint32_t instance_version = std::min(loader_version, VK_API_VERSION_1_2);

    std::vector<VkExtensionProperties> instance_extensions;
    if (!enumerate(inventory, "vkEnumerateInstanceExtensionProperties", instance_extensions,
                   [query_instance_extensions](uint32_t* count, VkExtensionProperties* extensions) {
                       return query_instance_extensions(nullptr, count, extensions);
                   })) return false;

    const bool properties2_extension = advertises(instance_extensions,
                                                   VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME);
    const char* properties2_name = VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME;

    VkApplicationInfo application{};
    application.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    application.pApplicationName = "ProsperoVK-Lab";
    application.apiVersion = instance_version;

    VkInstanceCreateInfo instance_info{};
    instance_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    instance_info.pApplicationInfo = &application;
    // Preserve the properties2 alias for a Vulkan 1.0 device behind a newer loader.
    if (properties2_extension) {
        instance_info.enabledExtensionCount = 1;
        instance_info.ppEnabledExtensionNames = &properties2_name;
    }
    VkInstance instance = VK_NULL_HANDLE;
    VkResult result = create_instance(&instance_info, nullptr, &instance);
    if (result != VK_SUCCESS) return failed(inventory, "vkCreateInstance", result);
    if (!instance) {
        inventory.reason = "vkCreateInstance succeeded without an instance";
        return false;
    }
    inventory.instance = instance;

#define REQUIRED(member, name) \
    auto member = resolve<PFN_##name>(inventory, #name); \
    if (!member) { \
        inventory.reason = "Missing " #name; \
        return false; \
    }
    REQUIRED(destroy, vkDestroyInstance);
    inventory.destroy_instance = destroy;
    REQUIRED(query_devices, vkEnumeratePhysicalDevices);
    REQUIRED(query_properties, vkGetPhysicalDeviceProperties);
    REQUIRED(query_extensions, vkEnumerateDeviceExtensionProperties);
    REQUIRED(query_queues, vkGetPhysicalDeviceQueueFamilyProperties);
    REQUIRED(query_memory, vkGetPhysicalDeviceMemoryProperties);
    REQUIRED(query_features, vkGetPhysicalDeviceFeatures);
    REQUIRED(query_formats, vkGetPhysicalDeviceFormatProperties);
#undef REQUIRED

    std::vector<VkPhysicalDevice> devices;
    if (!enumerate(inventory, "vkEnumeratePhysicalDevices", devices,
                   [&inventory, query_devices](uint32_t* count, VkPhysicalDevice* physical) {
                       return query_devices(inventory.instance, count, physical);
                   })) return false;
    if (devices.empty()) {
        inventory.reason = "Vulkan enumerated no physical devices";
        return false;
    }
    if (index >= devices.size()) {
        inventory.reason = "Device index " + std::to_string(index) +
                           " is out of range for " + std::to_string(devices.size()) + " physical device(s)";
        return false;
    }
    inventory.physical = devices[index];
    query_properties(inventory.physical, &inventory.properties);
    inventory.api_version = std::min(instance_version, inventory.properties.apiVersion);

    std::vector<VkExtensionProperties> device_extensions;
    if (!enumerate(inventory, "vkEnumerateDeviceExtensionProperties", device_extensions,
                   [&inventory, query_extensions](uint32_t* count, VkExtensionProperties* extensions) {
                       return query_extensions(inventory.physical, nullptr, count, extensions);
                   })) return false;

    const bool core11 = inventory.api_version >= VK_API_VERSION_1_1;
    const char* properties_path = "vkGetPhysicalDeviceProperties2";
    const char* features_path = "vkGetPhysicalDeviceFeatures2";
    auto properties2 = core11 ? resolve<PFN_vkGetPhysicalDeviceProperties2>(inventory, properties_path) : nullptr;
    auto features2 = core11 ? resolve<PFN_vkGetPhysicalDeviceFeatures2>(inventory, features_path) : nullptr;
    if (!properties2 && properties2_extension) {
        properties_path = "vkGetPhysicalDeviceProperties2KHR";
        properties2 = resolve<PFN_vkGetPhysicalDeviceProperties2>(inventory, properties_path);
    }
    if (!features2 && properties2_extension) {
        features_path = "vkGetPhysicalDeviceFeatures2KHR";
        features2 = resolve<PFN_vkGetPhysicalDeviceFeatures2>(inventory, features_path);
    }
    const char* properties_reason = core11 || properties2_extension
                                     ? "Negotiated properties2 entry point is missing"
                                     : "Requires Vulkan 1.1 or VK_KHR_get_physical_device_properties2";
    const char* features_reason = core11 || properties2_extension
                                   ? "Negotiated features2 entry point is missing"
                                   : "Requires Vulkan 1.1 or VK_KHR_get_physical_device_properties2";

    VkPhysicalDeviceDriverProperties driver{};
    driver.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES;
    const char* driver_reason = "Requires Vulkan 1.2 or VK_KHR_driver_properties";
    VkPhysicalDeviceIDProperties identifiers{};
    identifiers.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES;
    if (properties2) {
        VkPhysicalDeviceProperties2 properties{};
        properties.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
        if (inventory.api_version >= VK_API_VERSION_1_2 ||
            advertises(device_extensions, VK_KHR_DRIVER_PROPERTIES_EXTENSION_NAME)) {
            properties.pNext = &driver;
            driver_reason = nullptr;
        }
        if (core11) {
            identifiers.pNext = properties.pNext;
            properties.pNext = &identifiers;
        }
        properties2(inventory.physical, &properties);
        inventory.properties = properties.properties;
    } else {
        driver_reason = properties_reason;
    }

    VkPhysicalDeviceFeatures features{};
    if (features2) {
        VkPhysicalDeviceFeatures2 queried{};
        queried.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2;
        features2(inventory.physical, &queried);
        features = queried.features;
    } else {
        query_features(inventory.physical, &features);
    }

    uint32_t queue_count = 0;
    query_queues(inventory.physical, &queue_count, nullptr);
    std::vector<VkQueueFamilyProperties> queues(queue_count);
    if (queue_count) {
        query_queues(inventory.physical, &queue_count, queues.data());
        queues.resize(queue_count);
    }
    for (uint32_t i = 0; i < queues.size(); ++i) {
        if (queues[i].queueCount > 0 && (queues[i].queueFlags & VK_QUEUE_COMPUTE_BIT)) {
            inventory.queue_family = i;
            break;
        }
    }
    query_memory(inventory.physical, &inventory.memory);

    if (inventory.memory.memoryTypeCount > VK_MAX_MEMORY_TYPES ||
        inventory.memory.memoryHeapCount > VK_MAX_MEMORY_HEAPS) {
        inventory.reason = "Invalid Vulkan memory type or heap count";
        return false;
    }
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << "{\"instance\":{\"loader_api_version\":" << loader_version
        << ",\"loader_api_version_reason\":"
        << (query_version ? "null" : quote("vkEnumerateInstanceVersion unavailable. Using Vulkan 1.0."))
        << ",\"api_version\":" << instance_version << ",\"extensions\":";
    write_extensions(out, instance_extensions);
    out << ",\"enabled_extensions\":[";
    if (properties2_extension) out << quote(properties2_name);
    const auto& properties = inventory.properties;
    out << "]},\"device_count\":" << devices.size() << ",\"selected_device\":{\"index\":" << index
        << ",\"name\":" << quote(properties.deviceName)
        << ",\"api_version\":" << properties.apiVersion
        << ",\"negotiated_api_version\":" << inventory.api_version
        << ",\"driver_version\":" << properties.driverVersion
        << ",\"vendor_id\":" << properties.vendorID << ",\"device_id\":" << properties.deviceID
        << ",\"device_type\":" << properties.deviceType
        << ",\"pipeline_cache_uuid\":" << quote(uuid(properties.pipelineCacheUUID))
        << ",\"device_uuid\":" << (properties2 && core11 ? quote(uuid(identifiers.deviceUUID)) : "null")
        << ",\"driver_uuid\":" << (properties2 && core11 ? quote(uuid(identifiers.driverUUID)) : "null")
        << ",\"uuid_reason\":"
        << (properties2 && core11 ? "null" : quote("This inventory queries UUIDs through the Vulkan 1.1 properties2 path, which is unavailable"))
        << ",\"properties_query\":{\"entrypoint\":"
        << quote(properties2 ? properties_path : "vkGetPhysicalDeviceProperties")
        << ",\"reason\":" << (properties2 ? "null" : quote(properties_reason)) << '}'
        << ",\"features_query\":{\"entrypoint\":"
        << quote(features2 ? features_path : "vkGetPhysicalDeviceFeatures")
        << ",\"reason\":" << (features2 ? "null" : quote(features_reason)) << '}'
        << ",\"driver_properties\":";
    write_driver_properties(out, driver, driver_reason);
    out << ",\"extensions\":";
    write_extensions(out, device_extensions);
    out << ",\"features\":";
    write_features(out, features);
    out << ",\"limits\":";
    write_limits(out, properties.limits);
    out << ",\"queues\":";
    write_queues(out, queues);
    out << ",\"memory\":";
    write_memory(out, inventory.memory);
    out << ",\"formats\":";
    write_formats(out, inventory.physical, query_formats);
    out << "},\"queue_family\":";
    if (inventory.queue_family == UINT32_MAX) out << "null";
    else out << inventory.queue_family;
    out << '}';
    inventory.json = out.str();
    return true;
}

}  // namespace m1
