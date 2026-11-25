# SPDX-License-Identifier: GPL-3.0-or-later

cmake_minimum_required(VERSION 3.24)

# Script mode shares shader generation between the Linux and target builds.
if(CMAKE_SCRIPT_MODE_FILE)
    if(DEFINED SMOKE_SHADER_SOURCE)
        execute_process(
            COMMAND "${SMOKE_GLSLANG}" -V --target-env vulkan1.0
                    -o "${SMOKE_SHADER_BINARY}.tmp" "${SMOKE_SHADER_SOURCE}"
            COMMAND_ERROR_IS_FATAL ANY
        )
        execute_process(
            COMMAND "${SMOKE_SPIRV_VAL}" --target-env vulkan1.0 "${SMOKE_SHADER_BINARY}.tmp"
            COMMAND_ERROR_IS_FATAL ANY
        )
        execute_process(
            COMMAND "${SMOKE_GLSLANG}" -V --target-env vulkan1.0 --vn m0_radv_compute_spv
                    -o "${SMOKE_SHADER_HEADER}.tmp" "${SMOKE_SHADER_SOURCE}"
            COMMAND_ERROR_IS_FATAL ANY
        )

        # Convert the embedded 32-bit words to little-endian bytes for comparison.
        file(READ "${SMOKE_SHADER_HEADER}.tmp" shader_header_text)
        file(READ "${SMOKE_SHADER_BINARY}.tmp" shader_binary_hex HEX)
        set(byte "[0-9a-fA-F][0-9a-fA-F]")
        string(REGEX MATCHALL "0x${byte}${byte}${byte}${byte}" shader_words "${shader_header_text}")
        string(REGEX REPLACE "0x(${byte})(${byte})(${byte})(${byte})" "\\4\\3\\2\\1" shader_bytes "${shader_words}")
        string(REPLACE ";" "" shader_header_hex "${shader_bytes}")
        string(TOLOWER "${shader_header_hex}" shader_header_hex)
        if(NOT shader_header_hex STREQUAL shader_binary_hex)
            message(FATAL_ERROR "Embedded shader words differ from the validated SPIR-V")
        endif()
        file(RENAME "${SMOKE_SHADER_BINARY}.tmp" "${SMOKE_SHADER_BINARY}")
        file(RENAME "${SMOKE_SHADER_HEADER}.tmp" "${SMOKE_SHADER_HEADER}")
        return()
    endif()

    # Check both process exit and the single flat result record in CTest.
    if(DEFINED SMOKE_MISSING_ICD)
        if(EXISTS "${SMOKE_MISSING_ICD}")
            message(FATAL_ERROR "Expected an absent ICD manifest at ${SMOKE_MISSING_ICD}")
        endif()
        set(ENV{VK_DRIVER_FILES} "${SMOKE_MISSING_ICD}")
        set(ENV{VK_ICD_FILENAMES} "${SMOKE_MISSING_ICD}")
    endif()

    execute_process(
        COMMAND "${SMOKE_EXECUTABLE}"
        RESULT_VARIABLE smoke_exit
        OUTPUT_VARIABLE smoke_output
        OUTPUT_STRIP_TRAILING_WHITESPACE
        TIMEOUT 15
    )
    message(STATUS "Compute smoke exit ${smoke_exit}, output ${smoke_output}")

    if(NOT smoke_output MATCHES "^[{][^{}\r\n]*[}]$")
        message(FATAL_ERROR "Expected a single result record on stdout")
    endif()
    string(JSON smoke_case GET "${smoke_output}" case_id)
    string(JSON smoke_status GET "${smoke_output}" status)
    if(NOT smoke_case STREQUAL "m0.radv.compute")
        message(FATAL_ERROR "Unexpected compute smoke case ID")
    endif()

    if(DEFINED SMOKE_MISSING_ICD)
        if(NOT smoke_exit MATCHES "^[1-9][0-9]*$" OR NOT smoke_status STREQUAL "ERROR")
            message(FATAL_ERROR "Expected a nonzero exit and ERROR result for a missing ICD")
        endif()
    else()
        if(NOT smoke_exit STREQUAL "0" OR NOT smoke_status STREQUAL "PASS")
            message(FATAL_ERROR "Expected a zero exit and PASS result")
        endif()
        string(JSON smoke_words GET "${smoke_output}" checked_words)
        string(JSON smoke_words_type TYPE "${smoke_output}" checked_words)
        if(NOT smoke_words STREQUAL "4096" OR NOT smoke_words_type STREQUAL "NUMBER")
            message(FATAL_ERROR "Expected the compute smoke to check all 4096 words")
        endif()
    endif()
    return()
endif()

project(m0_radv_compute LANGUAGES CXX)

find_package(Vulkan REQUIRED COMPONENTS glslangValidator)
find_program(SPIRV_VAL NAMES spirv-val REQUIRED)

set(shader_source "${CMAKE_CURRENT_SOURCE_DIR}/compute.comp")
set(shader_binary "${CMAKE_CURRENT_BINARY_DIR}/compute.spv")
set(shader_header "${CMAKE_CURRENT_BINARY_DIR}/compute_spv.hpp")
add_custom_command(
    OUTPUT "${shader_binary}" "${shader_header}"
    COMMAND "${CMAKE_COMMAND}" "-DSMOKE_SHADER_SOURCE=${shader_source}"
            "-DSMOKE_SHADER_BINARY=${shader_binary}" "-DSMOKE_SHADER_HEADER=${shader_header}"
            "-DSMOKE_GLSLANG=$<TARGET_FILE:Vulkan::glslangValidator>" "-DSMOKE_SPIRV_VAL=${SPIRV_VAL}"
            -P "${CMAKE_CURRENT_LIST_FILE}"
    DEPENDS "${shader_source}" "${CMAKE_CURRENT_LIST_FILE}"
    VERBATIM
)

add_library(m0_radv_compute_workload STATIC compute.cpp "${shader_header}")
target_compile_features(m0_radv_compute_workload PUBLIC cxx_std_20)
target_include_directories(m0_radv_compute_workload PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(m0_radv_compute_workload PUBLIC Vulkan::Vulkan)

add_executable(m0_radv_compute main.cpp)
target_link_libraries(m0_radv_compute PRIVATE m0_radv_compute_workload)

add_executable(m0_radv_compute_timing timing-main.cpp)
target_link_libraries(m0_radv_compute_timing PRIVATE m0_radv_compute_workload)

include(CTest)
if(NOT BUILD_TESTING)
    return()
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_executable(m0_radv_timing_injected timing-injected.cpp)
target_link_libraries(m0_radv_timing_injected PRIVATE m0_radv_compute_workload)
add_test(
    NAME m0_radv_compute
    COMMAND "${CMAKE_COMMAND}" "-DSMOKE_EXECUTABLE=$<TARGET_FILE:m0_radv_compute>"
            -P "${CMAKE_CURRENT_LIST_FILE}"
)
add_test(
    NAME m0_radv_compute_missing_icd
    COMMAND "${CMAKE_COMMAND}" "-DSMOKE_EXECUTABLE=$<TARGET_FILE:m0_radv_compute>"
            "-DSMOKE_MISSING_ICD=${CMAKE_CURRENT_BINARY_DIR}/missing-icd.json"
            -P "${CMAKE_CURRENT_LIST_FILE}"
)
set_tests_properties(m0_radv_compute m0_radv_compute_missing_icd PROPERTIES TIMEOUT 20)
add_test(
    NAME m0_radv_compute_timing
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/check-timing.py"
            "$<TARGET_FILE:m0_radv_compute_timing>" "$<TARGET_FILE:m0_radv_timing_injected>"
)
set_tests_properties(m0_radv_compute_timing PROPERTIES TIMEOUT 30)

if(DEFINED M0_TEMPLATE_SRC)
    add_executable(m0_title_capture ../m0-title/main.cpp ../m0-title/host-platform.cpp)
    target_include_directories(m0_title_capture PRIVATE "${M0_TEMPLATE_SRC}/ps5/src" "${CMAKE_CURRENT_SOURCE_DIR}")
    target_compile_definitions(m0_title_capture PRIVATE M0_CAPTURE_ROOT="capture" M0_BUILD_ID="linux-test")
    target_link_libraries(m0_title_capture PRIVATE m0_radv_compute_workload)
    add_test(NAME m0_title_capture COMMAND "${Python3_EXECUTABLE}"
             "${CMAKE_CURRENT_SOURCE_DIR}/../m0-title/check-host.py" "$<TARGET_FILE:m0_title_capture>"
             "${CMAKE_CURRENT_SOURCE_DIR}/../../../tools/verify-m0-radv-compute.py")
endif()
