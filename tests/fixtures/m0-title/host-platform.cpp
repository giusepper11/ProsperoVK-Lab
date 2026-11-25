// SPDX-License-Identifier: GPL-3.0-or-later
// Linux-only title capture test. The shared workload uses the Linux Vulkan loader.
#include "platform.h"
#include <vulkan/vk_icd.h>
#include <cstdarg>
#include <cstdio>

void platform_init(const char*) {}

void say(const char* format, ...) {
    va_list args;
    va_start(args, format);
    std::vfprintf(stderr, format, args);
    va_end(args);
    std::fputc('\n', stderr);
}

struct Notification;
extern "C" int sceKernelSendNotificationRequest(int, Notification*, size_t, int) { return 0; }

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vk_icdGetInstanceProcAddr(VkInstance instance, const char* name) {
    return vkGetInstanceProcAddr(instance, name);
}
