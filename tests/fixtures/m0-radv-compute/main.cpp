// SPDX-License-Identifier: GPL-3.0-or-later

#include "compute.hpp"

#include <cstdio>
#include <cstdlib>

#if defined(M0_RADV_COMPUTE_PS5)
#include <vulkan/vk_icd.h>
#endif

int main() {
    if (std::fputs("{\"case_id\":\"m0.radv.compute\",\"event\":\"start\"}\n", stderr) == EOF ||
        std::fflush(stderr) == EOF) {
        std::puts("{\"case_id\":\"m0.radv.compute\",\"status\":\"ERROR\",\"stage\":\"start_marker\"}");
        return EXIT_FAILURE;
    }

#if defined(M0_RADV_COMPUTE_PS5)
    return m0_radv_compute(vk_icdGetInstanceProcAddr);
#else
    return m0_radv_compute(vkGetInstanceProcAddr);
#endif
}
