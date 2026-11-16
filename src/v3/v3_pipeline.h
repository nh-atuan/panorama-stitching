// Authors: Tran Huu Kim Thanh (23120166)
// Adapted from: src/v2/v2_pipeline.h by Le Ha Thanh Chuong (23120195)
// Changes: Select the S5 V3 homography and its diagnostics instead of S5 V2.

#ifndef GROUP16_V3_PIPELINE_H
#define GROUP16_V3_PIPELINE_H

#include "v1/v1_pipeline.h"
#include "v3/s5/v3_homography.h"

namespace panorama {

using V3Diagnostics = GpuDiagnostics<V3HomographyDiagnostics>;

// V3 shares the owner, stream contract and unchanged stages with V1; only S5 differs.
ErrorCode v3_prepare(const Image& left, const Image& right, const Config& config, V1DeviceOwner& owner);
ErrorCode v3_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure);
V3Diagnostics v3_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V3_PIPELINE_H
