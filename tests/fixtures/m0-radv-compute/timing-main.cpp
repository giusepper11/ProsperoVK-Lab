// SPDX-License-Identifier: GPL-3.0-or-later

#include "compute.hpp"

#include <cstdio>
#include <cstring>

#if defined(M0_RADV_COMPUTE_PS5)
#include <vulkan/vk_icd.h>
#endif

int main(int argc, char** argv) {
    const bool verbose = argc == 2 && std::strcmp(argv[1], "--verbose") == 0;
    if (argc != 1 && !verbose) {
        std::fputs("Usage: m0_radv_compute_timing [--verbose]\n", stderr);
        return 2;
    }
    if (std::fputs("{\"case_id\":\"m0.radv.compute\",\"event\":\"start\",\"mode\":\"host_timing\"}\n", stderr) == EOF
        || std::fflush(stderr) == EOF) {
        std::puts("{\"case_id\":\"m0.radv.compute\",\"status\":\"ERROR\",\"stage\":\"start_marker\"}");
        return 1;
    }
#if defined(M0_RADV_COMPUTE_PS5)
    return m0_radv_compute_timing(vk_icdGetInstanceProcAddr, verbose);
#else
    return m0_radv_compute_timing(vkGetInstanceProcAddr, verbose);
#endif
}
