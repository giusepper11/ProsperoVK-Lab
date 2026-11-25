// SPDX-License-Identifier: GPL-3.0-or-later

#include "vkComputePipelineConstructionUtil.hpp"
#include "vktComputeBasicComputeShaderTests.hpp"
#include "vktTestPackage.hpp"

#include <memory>

namespace {

class BasicComputePackage final : public vkt::BaseTestPackage {
public:
    explicit BasicComputePackage(tcu::TestContext& context)
        : vkt::BaseTestPackage(context, "dEQP-VK") {}

    void init() override {
        auto compute = std::make_unique<tcu::TestCaseGroup>(m_testCtx, "compute");
        auto pipeline = std::make_unique<tcu::TestCaseGroup>(m_testCtx, "pipeline");
        pipeline->addChild(vkt::compute::createBasicComputeShaderTests(
            m_testCtx, vk::COMPUTE_PIPELINE_CONSTRUCTION_TYPE_PIPELINE));
        compute->addChild(pipeline.release());
        addChild(compute.release());
    }
};

tcu::TestPackage* createPackage(tcu::TestContext& context) {
    return new BasicComputePackage(context);
}

tcu::TestPackageDescriptor registrar("dEQP-VK", createPackage);

} // namespace
