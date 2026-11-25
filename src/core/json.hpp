// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <string>

namespace m1 {
inline std::string quote(const std::string& value) {
    static constexpr char hex[] = "0123456789abcdef";
    std::string result = "\"";
    for (unsigned char ch : value) {
        if (ch == '"' || ch == '\\') {
            result += '\\';
            result += static_cast<char>(ch);
        } else if (ch < 0x20) {
            result += "\\u00";
            result += hex[ch >> 4];
            result += hex[ch & 15];
        } else {
            result += static_cast<char>(ch);
        }
    }
    return result + '"';
}
}
