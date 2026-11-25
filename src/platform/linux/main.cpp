// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/runner.hpp"
#include "build_identity.hpp"

#include <cerrno>
#include <charconv>
#include <sys/random.h>
#include <cstdio>
#include <string_view>

namespace {
int usage() {
    std::fputs("Usage: prosperovk --list | (--inventory | --case ID) [--device INDEX] --report NEW_FILE\n", stderr);
    return 2;
}
}

int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--list") {
        m1::list_cases();
        return 0;
    }
    bool inventory = false, has_device = false;
    const char* selected = nullptr;
    const char* report = nullptr;
    std::uint32_t device = 0;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg(argv[i]);
        if (arg == "--inventory" && !inventory) {
            inventory = true;
        } else if (arg == "--case" && !selected && i + 1 < argc) {
            selected = argv[++i];
        } else if (arg == "--report" && !report && i + 1 < argc) {
            report = argv[++i];
        } else if (arg == "--device" && !has_device && i + 1 < argc) {
            const std::string_view index(argv[++i]);
            const auto end = index.data() + index.size();
            const auto result = std::from_chars(index.data(), end, device);
            if (result.ec != std::errc{} || result.ptr != end) return usage();
            has_device = true;
        } else {
            return usage();
        }
    }
    if (!report || !*report || inventory == (selected != nullptr)) return usage();
    unsigned char nonce[16];
    ssize_t bytes;
    do {
        bytes = getrandom(nonce, sizeof(nonce), 0);
    } while (bytes < 0 && errno == EINTR);
    if (bytes != sizeof(nonce)) {
        std::fputs("could not generate run identity\n", stderr);
        return 2;
    }
    constexpr char hex[] = "0123456789abcdef";
    char run_id[33]{};
    for (std::size_t i = 0; i < sizeof(nonce); ++i) {
        run_id[2 * i] = hex[nonce[i] >> 4];
        run_id[2 * i + 1] = hex[nonce[i] & 15];
    }
    return m1::run(vkGetInstanceProcAddr, "linux", M1_BUILD_ID, M1_REVISION, device, selected, report, run_id);
}
