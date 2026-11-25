// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>
#include <vulkan/vulkan.h>

namespace m1 {
int run(PFN_vkGetInstanceProcAddr resolver, const char* target, const char* build_id,
        const char* revision, std::uint32_t device, const char* case_id, const char* report_path,
        const char* run_id);
void list_cases();
}
