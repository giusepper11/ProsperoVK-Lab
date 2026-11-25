// SPDX-License-Identifier: GPL-3.0-or-later

#include "platform.h"

#include <cerrno>
#include <cstdio>
#include <sys/stat.h>
#include <unistd.h>

#ifndef M0_CAPTURE_ROOT
#define M0_CAPTURE_ROOT "/app0"
#endif

#ifdef M0_CTS_USE_RADV
// libc++ queries _PC_PATH_MAX before getcwd when glslang formats diagnostic paths.
// The title SDK exposes no usable pathconf import. Report an indeterminate limit
// for this supported query, so libc++ can use its own getcwd fallback.
extern "C" long __wrap_pathconf(const char* path, int name) {
    if (name != _PC_PATH_MAX) {
        errno = ENOSYS;
        return -1;
    }
    const int saved_errno = errno;
    struct stat status;
    if (stat(path, &status) == 0) errno = saved_errno;
    return -1;
}
#endif

int m0_cts_main(int argc, char** argv);

constexpr char case_id[] = M0_CTS_CASE_ID;

int main() {
    platform_init("ProsperoVK Lab CTS");
    char dir[sizeof(M0_CAPTURE_ROOT) + 16];
    for (unsigned index = 1; ; ++index) {
        std::snprintf(dir, sizeof(dir), M0_CAPTURE_ROOT "/run-%06u", index);
        if (mkdir(dir, 0777) == 0) break;
        if (errno != EEXIST || index == 999999) {
            say("CTS capture directory could not be created");
            return 1;
        }
    }
    say("CTS build %s, capture %s", M0_BUILD_ID, dir);

    char start[sizeof(dir) + 16];
    std::snprintf(start, sizeof(start), "%s/start.log", dir);
    FILE* journal = std::fopen(start, "w");
    if (!journal) {
        say("CTS start journal could not be opened");
        return 1;
    }
    const bool wrote_journal = std::fprintf(journal, "build %s\ntitle %s\ncase %s\n",
                                            M0_BUILD_ID, M0_TITLE_ID, case_id) >= 0;
    if (std::fclose(journal) != 0 || !wrote_journal) {
        say("CTS start journal could not be written");
        return 1;
    }

    char diagnostics[sizeof(dir) + 16];
    std::snprintf(diagnostics, sizeof(diagnostics), "%s/title.log", dir);
    if (!std::freopen(diagnostics, "a", stdout)) {
        say("CTS diagnostics could not be opened");
        return 1;
    }
    if (!std::freopen(diagnostics, "a", stderr)) {
        std::fputs("CTS error diagnostics could not be opened\n", stdout);
        std::fflush(stdout);
        return 1;
    }
    std::setvbuf(stderr, nullptr, _IONBF, 0);

    char program[] = "deqp-vk";
    char selected[sizeof(case_id) + 16];
    std::snprintf(selected, sizeof(selected), "--deqp-case=%s", case_id);
    char log[sizeof(dir) + 48];
    std::snprintf(log, sizeof(log), "--deqp-log-filename=%s/TestResults.qpa", dir);
    char archive[] = "--deqp-archive-dir=" M0_CAPTURE_ROOT;
    char no_images[] = "--deqp-log-images=disable";
    char no_shader_cache[] = "--deqp-shadercache=disable";
    char* argv[] = {program, selected, log, archive, no_images, no_shader_cache, nullptr};
    const int status = m0_cts_main(sizeof(argv) / sizeof(argv[0]) - 1, argv);

    char exit_path[sizeof(dir) + 24];
    std::snprintf(exit_path, sizeof(exit_path), "%s/exit-code.txt", dir);
    FILE* code = std::fopen(exit_path, "w");
    if (!code) {
        say("CTS exit record could not be opened");
        return 1;
    }
    const bool wrote_code = std::fprintf(code, "%d\n", status) >= 0;
    if (std::fclose(code) != 0 || !wrote_code) {
        say("CTS exit record could not be written");
        return 1;
    }
    say("CTS runner returned %d", status);
    return status;
}
