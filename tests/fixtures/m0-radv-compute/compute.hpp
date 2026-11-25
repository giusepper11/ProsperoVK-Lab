// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <vulkan/vulkan.h>

int m0_radv_compute(PFN_vkGetInstanceProcAddr resolver);

#if !defined(M0_RADV_COMPUTE_PS5) && !defined(M0_RADV_COMPUTE_TIMING)
#define M0_RADV_COMPUTE_TIMING
#endif

#if defined(M0_RADV_COMPUTE_TIMING)
int m0_radv_compute_timing(PFN_vkGetInstanceProcAddr resolver, bool verbose);
#endif
