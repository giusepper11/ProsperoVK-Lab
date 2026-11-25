// SPDX-License-Identifier: GPL-3.0-or-later

#include "deDefs.h"

// The CTS framework has its own generated Vulkan definitions. Keep the
// standard Vulkan headers in this translation unit.
#if defined(M0_CTS_USE_RADV)
#include <vulkan/vk_icd.h>
#else
#include <vulkan/vulkan.h>
#endif

deFunctionPtr getM0CtsVulkanResolver() {
#if defined(M0_CTS_USE_RADV)
    return reinterpret_cast<deFunctionPtr>(vk_icdGetInstanceProcAddr);
#else
    return reinterpret_cast<deFunctionPtr>(vkGetInstanceProcAddr);
#endif
}
