// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <string>

namespace m1 {
struct Outcome {
    std::string status = "ERROR";
    std::string reason;
    std::string eligibility = "not_evaluated";
    std::string requirements = "{}";
    std::string enabled = "null";
    std::string correctness = "null";
    std::string timing = "null";
};
}
