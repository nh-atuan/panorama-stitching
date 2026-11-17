// Authors: Tran Huu Kim Thanh (23120166)
// Adapted from: src/v3/v3_pipeline.cu by Tran Huu Kim Thanh (23120166)
// Changes: Run v4_warp_blend in the S6 slot; S5 and its scratch stay on V3.

#include "v4/v4_pipeline.h"
#include "v4/s6/v4_warp_blend.h"

namespace panorama {
namespace {

// S6 V4 allocates its canvas outside the shared scratch, so only S5 V3 sizes it.
std::size_t v4_s5_scratch(std::size_t capacity) {
    return v3_homography_scratch_bytes(capacity);
}

}  // namespace

ErrorCode v4_prepare(const Image& left, const Image& right, const Config& config, V1DeviceOwner& owner) {
    return prepare_gpu_pipeline(left, right, config, owner, v4_s5_scratch);
}

ErrorCode v4_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure) {
    return run_gpu_stages(workspace, config, stream, trace, failure, v3_homography, v4_warp_blend);
}

V4Diagnostics v4_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream) {
    return collect_gpu_diagnostics(workspace, stream, v3_homography_diagnostics(workspace));
}

}  // namespace panorama
