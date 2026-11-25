// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/runner.hpp"
#include "platform.h"

#include <vulkan/vk_icd.h>

#include <cerrno>
#include <charconv>
#include <cstdio>
#include <cinttypes>
#include <string_view>
#include <sys/stat.h>

#ifndef M1_CAPTURE_ROOT
#define M1_CAPTURE_ROOT "/app0"
#endif

namespace {
constexpr char default_case[] = "core.compute.storage-buffer";

struct Selection {
    char input[64]{};
    const char* case_id = default_case;
    std::uint32_t device = 0;
};

bool read_selection(Selection& selection) {
    auto* file = std::fopen(M1_CAPTURE_ROOT "/selection.txt", "rb");
    if (!file) return errno == ENOENT;
    const auto size = std::fread(selection.input, 1, sizeof(selection.input), file);
    const bool readable = !std::ferror(file);
    const bool closed = std::fclose(file) == 0;
    if (!readable || !closed || size == sizeof(selection.input)) return false;

    std::string_view text(selection.input, size);
    if (text.ends_with('\n')) {
        text.remove_suffix(1);
        if (text.ends_with('\r')) text.remove_suffix(1);
    }
    const auto separator = text.find(' ');
    const auto name = text.substr(0, separator);
    if (name.empty() || name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789.-") != name.npos) {
        return false;
    }
    if (separator != text.npos) {
        const auto device = text.substr(separator + 1);
        const auto end = device.data() + device.size();
        const auto result = std::from_chars(device.data(), end, selection.device);
        if (result.ec != std::errc{} || result.ptr != end) return false;
    }
    selection.case_id = name == "inventory" ? nullptr : selection.input;
    selection.input[name.size()] = '\0';
    return true;
}

bool write_record(const char* path, const char* record) {
    auto* file = std::fopen(path, "w");
    if (!file) return false;
    const bool written = std::fputs(record, file) >= 0;
    return std::fclose(file) == 0 && written;
}
} // namespace

int main() {
    platform_init("ProsperoVK Lab M1");
    Selection selection;
    if (!read_selection(selection)) {
        say("ERROR reading selection.txt. Expected inventory or a case ID, optionally followed by a device index.");
        return 2;
    }
    char directory[64], run_id[16];
    for (unsigned index = 1; ; ++index) {
        std::snprintf(run_id, sizeof(run_id), "run-%06u", index);
        std::snprintf(directory, sizeof(directory), M1_CAPTURE_ROOT "/%s", run_id);
        if (mkdir(directory, 0777) == 0) break;
        if (errno != EEXIST || index >= 999999) {
            say("ERROR creating capture directory");
            return 1;
        }
    }

    char start[96], report[96], code[96], journal[512];
    std::snprintf(start, sizeof(start), "%s/start.log", directory);
    std::snprintf(report, sizeof(report), "%s/report.json", directory);
    std::snprintf(code, sizeof(code), "%s/exit-code.txt", directory);
    std::snprintf(journal, sizeof(journal),
                  "build %s\nrevision %s\ntitle %s\ncase %s\ndevice %" PRIu32 "\npath %s\n",
                  M1_BUILD_ID, M1_REVISION, M1_TITLE_ID,
                  selection.case_id ? selection.case_id : "inventory", selection.device, directory);
    if (!write_record(start, journal)) {
        say("ERROR opening capture journal");
        return 1;
    }

    say("build %s, capture %s", M1_BUILD_ID, directory);
    const int status = m1::run(vk_icdGetInstanceProcAddr, "ps5", M1_BUILD_ID,
                               M1_REVISION, selection.device, selection.case_id, report, run_id);
    char value[16];
    std::snprintf(value, sizeof(value), "%d\n", status);
    if (!write_record(code, value)) {
        say("ERROR writing runner return code");
        return 1;
    }
    say("Runner returned %d. See %s", status, report);
    return status;
}
