// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/runner.hpp"
#include "core/json.hpp"
#include "core/result.hpp"
#include "suites/compute/compute.hpp"
#include "vulkan/inventory.hpp"

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>

#ifndef M1_SHADER_SHA256
#include "shader_digest.hpp"
#endif

namespace m1 {
namespace {
struct Case {
    const char* id;
    const char* shader_sha256;
    Outcome (*execute)(Inventory&);
};

constexpr Case registry[] = {{"core.compute.storage-buffer", M1_SHADER_SHA256, compute}};

FILE* create_record(const char* path) {
    const int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0) return nullptr;
    FILE* stream = fdopen(fd, "w");
    if (!stream) close(fd);
    return stream;
}

bool finish(FILE* stream, const std::string& json) {
    const bool wrote = std::fwrite(json.data(), 1, json.size(), stream) == json.size()
                       && std::fputc('\n', stream) != EOF && std::fflush(stream) == 0;
    return std::fclose(stream) == 0 && wrote;
}
}

void list_cases() {
    for (const auto& item : registry) std::puts(item.id);
}

int run(PFN_vkGetInstanceProcAddr resolver, const char* target, const char* build_id,
        const char* revision, std::uint32_t device, const char* case_id, const char* report_path,
        const char* run_id) {
    const Case* selected = nullptr;
    if (case_id) {
        for (const auto& item : registry) {
            if (std::strcmp(case_id, item.id) == 0) selected = &item;
        }
        if (!selected) {
            std::fprintf(stderr, "unknown case: %s\n", case_id);
            return 2;
        }
    }
    FILE* report = create_record(report_path);
    if (!report) {
        std::perror(report_path);
        return 2;
    }
    const std::string identity = "{\"schema_version\":1,\"target\":" + quote(target)
        + ",\"run_id\":" + quote(run_id)
        + ",\"build_id\":" + quote(build_id) + ",\"revision\":" + quote(revision)
        + ",\"device_index\":" + std::to_string(device)
        + ",\"case_id\":" + (selected ? quote(selected->id) : "null");
    Inventory inventory;
    Outcome outcome;
    bool io_error = false;
    if (!discover(inventory, resolver, device)) {
        outcome.status = selected ? "NOT_RUN" : "ERROR";
        outcome.reason = inventory.reason;
    } else if (!selected) {
        outcome.status = "PASS";
    } else {
        const auto journal_path = std::string(report_path) + ".start.json";
        FILE* journal = create_record(journal_path.c_str());
        if (!journal || !finish(journal, identity + ",\"event\":\"start\"}")) {
            outcome.status = "NOT_RUN";
            outcome.reason = "could not persist start journal: " + journal_path;
            io_error = true;
        } else {
            outcome = selected->execute(inventory);
        }
    }
    const std::string terminal = identity + ",\"status\":" + quote(outcome.status)
        + ",\"reason\":" + (outcome.reason.empty() ? "null" : quote(outcome.reason))
        + ",\"shader_sha256\":" + (selected ? quote(selected->shader_sha256) : "null")
        + ",\"inventory\":" + (inventory.json.empty() ? "null" : inventory.json)
        + ",\"requirements\":" + outcome.requirements + ",\"eligibility\":" + quote(outcome.eligibility) + ",\"enabled\":" + outcome.enabled
        + ",\"correctness\":" + outcome.correctness + ",\"timing\":" + outcome.timing + "}";
    if (!finish(report, terminal)) {
        std::fprintf(stderr, "could not finalize report: %s\n", report_path);
        return 2;
    }
    if (!outcome.reason.empty()) std::fprintf(stderr, "%s: %s\n", outcome.status.c_str(), outcome.reason.c_str());
    if (io_error) return 2;
    return outcome.status == "PASS" ? 0 : 1;
}
}
