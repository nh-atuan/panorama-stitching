// Authors: Le Ha Thanh Chuong (23120195)
// External source: none

#include "v2/v2_pipeline.h"

namespace panorama {
namespace {

std::size_t v2_s5_scratch(std::size_t capacity) {
    return v2_homography_scratch_bytes(capacity);
}

}  // namespace

ErrorCode v2_prepare(const Image& left, const Image& right, const Config& config, V1DeviceOwner& owner) {
    return prepare_gpu_pipeline(left, right, config, owner, v2_s5_scratch);
}

ErrorCode v2_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure) {
    return run_gpu_stages(workspace, config, stream, trace, failure, v2_homography);
}

V2Diagnostics v2_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream) {
    return collect_gpu_diagnostics(workspace, stream, v2_homography_diagnostics(workspace));
}

}  // namespace panorama
