// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/runner.hpp"
#include "platform.h"

#include <cinttypes>
#include <cstdarg>
#include <cstdio>
#include <cstring>

void platform_init(const char*) {}

void say(const char* format, ...) {
    va_list args;
    va_start(args, format);
    std::vfprintf(stderr, format, args);
    va_end(args);
    std::fputc('\n', stderr);
}

extern "C" VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vk_icdGetInstanceProcAddr(VkInstance, const char*) {
    return nullptr;
}

int m1::run(PFN_vkGetInstanceProcAddr resolver, const char* target, const char* build_id,
            const char* revision, std::uint32_t device, const char* case_id, const char* report_path,
            const char* run_id) {
    if (resolver != vk_icdGetInstanceProcAddr || std::strcmp(target, "ps5") != 0 ||
        std::strcmp(build_id, "host-build") != 0 || std::strcmp(revision, "host-revision") != 0) {
        return 3;
    }
    if (case_id && std::strcmp(case_id, "core.compute.storage-buffer") != 0) return 2;
    auto* file = std::fopen(report_path, "w");
    if (!file) return 3;
    const bool written = std::fprintf(file, "%s %" PRIu32 " %s\n", case_id ? case_id : "inventory", device, run_id) > 0;
    return std::fclose(file) == 0 && written ? 0 : 3;
}
