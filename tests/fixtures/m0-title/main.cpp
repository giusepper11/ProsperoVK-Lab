// SPDX-License-Identifier: GPL-3.0-or-later
#include "compute.hpp"
#include "platform.h"
#include <vulkan/vk_icd.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <sys/stat.h>
#include <unistd.h>

#ifndef M0_CAPTURE_ROOT
#define M0_CAPTURE_ROOT "/app0"
#endif

// Notification ABI from ps5-payload-dev/sdk samples/hello_world (John Törnblom).
struct Notification {
    char reserved[45];
    char message[3075];
};
extern "C" int sceKernelSendNotificationRequest(int, Notification*, size_t, int);

static void announce(const char* message) {
    say("%s", message);
    Notification request{};
    std::snprintf(request.message, sizeof(request.message), "ProsperoVK Lab: %s", message);
    const int status = sceKernelSendNotificationRequest(0, &request, sizeof(request), 0);
    if (status != 0) say("notification returned %d", status);
}

static bool write_record(const char* path, const char* record) {
    FILE* file = std::fopen(path, "w");
    if (!file) return false;
    const bool wrote = std::fputs(record, file) >= 0;
    return std::fclose(file) == 0 && wrote;
}

int main() {
    platform_init("ProsperoVK Lab");
    char dir[64];
    for (unsigned index = 1; ; ++index) {
        std::snprintf(dir, sizeof(dir), M0_CAPTURE_ROOT "/run-%06u", index);
        if (mkdir(dir, 0777) == 0) break;
        if (errno != EEXIST || index >= 999999) {
            announce("ERROR creating capture directory");
            return 1;
        }
    }
    char start[96], result[96], code[96];
    std::snprintf(start, sizeof(start), "%s/start.log", dir);
    std::snprintf(result, sizeof(result), "%s/result.json", dir);
    std::snprintf(code, sizeof(code), "%s/exit-code.txt", dir);
    say("build %s, capture %s", M0_BUILD_ID, dir);
    char journal[256];
    std::snprintf(journal, sizeof(journal),
                  "build %s\n{\"case_id\":\"m0.radv.compute\",\"event\":\"start\"}\n", M0_BUILD_ID);
    if (!write_record(start, journal) || !std::freopen(result, "w", stdout)) {
        announce("ERROR opening capture files");
        return 1;
    }

    announce("Running compute smoke (4096 words)");
    const int status = m0_radv_compute(vk_icdGetInstanceProcAddr);
    if (std::ferror(stdout) || std::fflush(stdout) != 0) {
        announce("ERROR writing result.json");
        return 1;
    }
    char line[1024]{};
    FILE* report = std::fopen(result, "r");
    bool captured = report && std::fgets(line, sizeof(line), report);
    if (report) std::fclose(report);
    if (!captured || !write_record(code, status == 0 ? "0\n" : "1\n")) {
        announce("ERROR finalizing capture");
        return 1;
    }
    line[std::strcspn(line, "\r\n")] = 0;
    say("%s", line);
    if (status != 0) {
        announce(line);
        return status;
    }

    char timing[96], timing_code[96];
    std::snprintf(timing, sizeof(timing), "%s/timing.json", dir);
    std::snprintf(timing_code, sizeof(timing_code), "%s/timing-exit-code.txt", dir);
    if (!std::freopen(timing, "w", stdout)) {
        announce("ERROR opening timing.json");
        return 1;
    }
    say("Compute smoke passed. Starting timing probe.");
    const int timing_status = m0_radv_compute_timing(vk_icdGetInstanceProcAddr, false);
    if (std::ferror(stdout) || std::fflush(stdout) != 0 ||
        !write_record(timing_code, timing_status == 0 ? "0\n" : "1\n")) {
        announce("ERROR finalizing timing capture");
        return 1;
    }
    if (timing_status == 0) {
        announce("PASS. 4096 words correct per dispatch. 30 timing samples saved.");
    } else {
        FILE* failure = std::fopen(timing, "r");
        const bool read = failure && std::fgets(line, sizeof(line), failure);
        if (failure) std::fclose(failure);
        announce(read ? line : "Timing probe failed. See timing.json.");
    }
    return timing_status;
}
