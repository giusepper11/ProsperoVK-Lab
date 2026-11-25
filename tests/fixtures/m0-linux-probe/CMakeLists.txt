# SPDX-License-Identifier: GPL-3.0-or-later

cmake_minimum_required(VERSION 3.24)
project(m0_linux_probe LANGUAGES CXX)

find_package(Vulkan REQUIRED COMPONENTS glslangValidator)
find_program(SPIRV_VAL NAMES spirv-val REQUIRED)

add_executable(m0_linux_probe main.cpp)
target_compile_features(m0_linux_probe PRIVATE cxx_std_20)
target_link_libraries(m0_linux_probe PRIVATE Vulkan::Vulkan)

set(probe_spv "${CMAKE_CURRENT_BINARY_DIR}/probe.spv")
add_custom_command(
    OUTPUT "${probe_spv}"
    COMMAND Vulkan::glslangValidator -V --target-env vulkan1.0
            -o "${probe_spv}" "${CMAKE_CURRENT_SOURCE_DIR}/probe.comp"
    DEPENDS probe.comp
    VERBATIM
)
add_custom_target(m0_linux_probe_shader ALL DEPENDS "${probe_spv}")

enable_testing()
add_test(NAME m0_loader_and_queue COMMAND m0_linux_probe)
set_tests_properties(m0_loader_and_queue PROPERTIES TIMEOUT 15)
add_test(NAME m0_shader_toolchain COMMAND "${SPIRV_VAL}" --target-env vulkan1.0 "${probe_spv}")
