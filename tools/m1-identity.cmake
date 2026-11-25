# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.24)
execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY "${SOURCE}"
                OUTPUT_VARIABLE revision OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
file(SHA256 "${BINARY}/compute.spv" shader)
file(CONFIGURE OUTPUT "${BINARY}/shader_digest.hpp" CONTENT "#define M1_SHADER_SHA256 \"@shader@\"\n" @ONLY)
file(GLOB_RECURSE sources RELATIVE "${SOURCE}" "${SOURCE}/src/core/*" "${SOURCE}/src/vulkan/*"
     "${SOURCE}/src/platform/linux/*" "${SOURCE}/suites/compute/*")
list(APPEND sources CMakeLists.txt tools/m1-identity.cmake tests/fixtures/m0-radv-compute/CMakeLists.txt)
set(inputs "${revision}\n${shader}\n${COMPILER}\n${FLAGS}\n")
foreach(path IN LISTS sources)
    file(SHA256 "${SOURCE}/${path}" digest)
    string(APPEND inputs "${path} ${digest}\n")
endforeach()
string(SHA256 identity "${inputs}")
file(CONFIGURE OUTPUT "${BINARY}/build_identity.hpp" CONTENT "#define M1_REVISION \"@revision@\"\n#define M1_BUILD_ID \"@identity@\"\n" @ONLY)
