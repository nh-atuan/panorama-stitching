// Authors: Thanh Chuong (23120195)
// External source: none

#ifndef GROUP16_V1_WARP_BLEND_H
#define GROUP16_V1_WARP_BLEND_H

#include "common/common.h"

#ifdef __CUDACC__
#include <cuda_runtime.h>

namespace panorama {

// Inputs: borrowed Device RGB views, d_homography (B -> A), d_canvas_info.
// d_imageA/B must equal imageA/B.data. Strides are bytes; padding is supported.
// Setup runs on the supplied stream; only small geometry metadata returns to Host.
// This Host entry point replaces the workspace-owned cudaMalloc canvas on behalf
// of its owner. The caller must eventually cudaFree(workspace.d_canvas) once.
// d_panorama and canvas.image.data are aliases, not separate allocations.
// Success means rendering was enqueued: await this stream before consuming/freeing
// output. Async execution errors are observed by the caller's event/stream wait.
// On failure output views are empty; any retained d_canvas remains caller-owned.
// Does not copy panorama pixels to Host, log, or measure CPU time.
ErrorCode v1_warp_blend(DeviceWorkspace& workspace, const Config& config,
                       cudaStream_t stream = nullptr);

}  // namespace panorama
#endif  // __CUDACC__

#endif  // GROUP16_V1_WARP_BLEND_H
