// Authors: Tran Huu Kim Thanh (23120166)
// Adapted from: src/v3/v3_pipeline.h by Tran Huu Kim Thanh (23120166)
// Changes: Keep S5 V3 and replace S6 with the single-pass S6 V4 renderer.

#ifndef GROUP16_V4_PIPELINE_H
#define GROUP16_V4_PIPELINE_H

#include "v1/v1_pipeline.h"
#include "v3/s5/v3_homography.h"

namespace panorama {

// V4 changes no S5 code, so its debug report is the S5 V3 one.
using V4Diagnostics = GpuDiagnostics<V3HomographyDiagnostics>;

// V4 shares the owner and stream contract with V1, runs S1-S4 of V1 and S5 of V3,
// and renders the canvas with v4_warp_blend.
ErrorCode v4_prepare(const Image& left, const Image& right, const Config& config, V1DeviceOwner& owner);
ErrorCode v4_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure);
V4Diagnostics v4_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V4_PIPELINE_H
