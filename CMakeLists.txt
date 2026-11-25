# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.24)
project(prosperovk_lab LANGUAGES CXX)
find_package(Vulkan REQUIRED COMPONENTS glslangValidator)
find_program(SPIRV_VAL spirv-val REQUIRED)
set(generator "${PROJECT_SOURCE_DIR}/tests/fixtures/m0-radv-compute/CMakeLists.txt")
add_custom_command(OUTPUT compute.spv compute_spv.hpp
    COMMAND "${CMAKE_COMMAND}" "-DSMOKE_SHADER_SOURCE=${PROJECT_SOURCE_DIR}/suites/compute/storage.comp"
        "-DSMOKE_SHADER_BINARY=${PROJECT_BINARY_DIR}/compute.spv"
        "-DSMOKE_SHADER_HEADER=${PROJECT_BINARY_DIR}/compute_spv.hpp"
        "-DSMOKE_GLSLANG=$<TARGET_FILE:Vulkan::glslangValidator>" "-DSMOKE_SPIRV_VAL=${SPIRV_VAL}"
        -P "${generator}"
    DEPENDS suites/compute/storage.comp "${generator}" VERBATIM)
string(TOUPPER "${CMAKE_BUILD_TYPE}" build_type)
add_custom_target(m1_identity
    COMMAND "${CMAKE_COMMAND}" "-DSOURCE=${PROJECT_SOURCE_DIR}" "-DBINARY=${PROJECT_BINARY_DIR}"
        "-DCOMPILER=${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}"
        "-DFLAGS=${CMAKE_BUILD_TYPE} ${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${build_type}}"
        -P "${PROJECT_SOURCE_DIR}/tools/m1-identity.cmake"
    DEPENDS compute.spv BYPRODUCTS build_identity.hpp shader_digest.hpp VERBATIM)
add_library(m1_core STATIC src/core/runner.cpp src/vulkan/inventory.cpp suites/compute/compute.cpp)
add_dependencies(m1_core m1_identity)
target_compile_features(m1_core PUBLIC cxx_std_20)
target_include_directories(m1_core PUBLIC src "${PROJECT_SOURCE_DIR}" PRIVATE "${PROJECT_BINARY_DIR}")
target_link_libraries(m1_core PUBLIC Vulkan::Vulkan)
add_executable(prosperovk src/platform/linux/main.cpp)
add_dependencies(prosperovk m1_identity)
target_include_directories(prosperovk PRIVATE "${PROJECT_BINARY_DIR}")
target_link_libraries(prosperovk PRIVATE m1_core)
install(TARGETS prosperovk RUNTIME DESTINATION bin)
install(FILES schemas/run-v1.schema.json DESTINATION share/prosperovk)
include(CTest)
if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME m1_runner COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/m1/runner.py" "$<TARGET_FILE:prosperovk>")
    set_tests_properties(m1_runner PROPERTIES TIMEOUT 45)
    add_executable(m1_inventory_test tests/m1/inventory.cpp)
    target_link_libraries(m1_inventory_test PRIVATE m1_core)
    add_test(NAME m1_inventory_paths COMMAND m1_inventory_test)
    add_executable(m1_compute_injected tests/m1/compute-injected.cpp)
    target_link_libraries(m1_compute_injected PRIVATE m1_core)
    add_test(NAME m1_compute_persistence COMMAND "${Python3_EXECUTABLE}"
        "${PROJECT_SOURCE_DIR}/tests/m1/compute-persistence.py" "$<TARGET_FILE:m1_compute_injected>")
    set_tests_properties(m1_compute_persistence PROPERTIES TIMEOUT 30)
    foreach(scenario IN ITEMS pass left-guard right-guard output noncoherent flush-error invalidate-error
            missing-entry no-compute-queue local-size allocation-ceiling memory-bits submit-error
            device-lost timeout wait-error)
        add_test(NAME m1_compute_${scenario} COMMAND m1_compute_injected ${scenario})
        set_tests_properties(m1_compute_${scenario} PROPERTIES TIMEOUT 15)
    endforeach()
endif()
