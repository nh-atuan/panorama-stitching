// Authors: Le Ha Thanh Chuong (23120195)
// External source: none

#ifndef GROUP16_V2_PIPELINE_H
#define GROUP16_V2_PIPELINE_H

#include "v1/v1_pipeline.h"
#include "v2/s5/v2_homography.h"

namespace panorama {

using V2Diagnostics = GpuDiagnostics<V2HomographyDiagnostics>;

// V2 shares the owner, stream contract and unchanged stages with V1.
ErrorCode v2_prepare(const Image& left, const Image& right, const Config& config, V1DeviceOwner& owner);
ErrorCode v2_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure);
V2Diagnostics v2_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V2_PIPELINE_H
