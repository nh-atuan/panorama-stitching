// Authors: Tran Huu Kim Thanh (23120166)
// Adapted from: src/v2/v2_pipeline.cu by Le Ha Thanh Chuong (23120195)
// Changes: Size the shared scratch for S5 V3 and run v3_homography in the S5 slot.

#include "v3/v3_pipeline.h"

namespace panorama {
namespace {

// Uses the default S5 V3 batch size, the same one v3_homography launches with.
std::size_t v3_s5_scratch(std::size_t capacity) {
    return v3_homography_scratch_bytes(capacity);
}

}  // namespace

ErrorCode v3_prepare(const Image& left, const Image& right, const Config& config, V1DeviceOwner& owner) {
    return prepare_gpu_pipeline(left, right, config, owner, v3_s5_scratch);
}

ErrorCode v3_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure) {
    return run_gpu_stages(workspace, config, stream, trace, failure, v3_homography);
}

V3Diagnostics v3_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream) {
    return collect_gpu_diagnostics(workspace, stream, v3_homography_diagnostics(workspace));
}

}  // namespace panorama
