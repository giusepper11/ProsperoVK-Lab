// SPDX-License-Identifier: GPL-3.0-or-later

#include "tcuFunctionLibrary.hpp"
#include "tcuPlatform.hpp"
#include "vkPlatform.hpp"

deFunctionPtr getM0CtsVulkanResolver();

namespace {

const tcu::StaticFunctionLibrary::Entry entry = {"vkGetInstanceProcAddr", getM0CtsVulkanResolver()};

class HeadlessLibrary final : public vk::Library {
public:
    HeadlessLibrary() : functions_(&entry, 1), driver_(functions_) {}

    const vk::PlatformInterface& getPlatformInterface() const override { return driver_; }
    const tcu::FunctionLibrary& getFunctionLibrary() const override { return functions_; }

private:
    tcu::StaticFunctionLibrary functions_;
    vk::PlatformDriver driver_;
};

class HeadlessPlatform final : public tcu::Platform, private vk::Platform {
public:
    const vk::Platform& getVulkanPlatform() const override { return *this; }

#ifdef DE_PLATFORM_USE_LIBRARY_TYPE
    vk::Library* createLibrary(LibraryType type, const char* path) const override {
        if (type != LIBRARY_TYPE_VULKAN) {
            TCU_THROW(NotSupportedError, "Unsupported CTS Vulkan library type");
        }
#else
    vk::Library* createLibrary(const char* path) const override {
#endif
        if (path && *path) {
            TCU_THROW(NotSupportedError, "The M0 CTS adapter uses the linked Vulkan resolver");
        }
        return new HeadlessLibrary();
    }
};

} // namespace

tcu::Platform* createPlatform() {
    return new HeadlessPlatform();
}
