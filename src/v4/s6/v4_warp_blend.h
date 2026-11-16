// Authors: Le Ha Thanh Chuong (23120195)
// External source: none

#ifndef GROUP16_V4_WARP_BLEND_H
#define GROUP16_V4_WARP_BLEND_H

#include "common/common.h"

#ifdef __CUDACC__
#include <cuda_runtime.h>

namespace panorama {

// Pitched, interleaved RGB Device inputs. imageA/B.data must match d_imageA/B.
// Supply Device storage for d_canvas_info and d_homography (B -> A), with inputs
// ready on stream. Setup reads back geometry metadata before allocating output.
// The entry point may replace d_canvas and updates canvas_capacity_bytes.
// The workspace owner frees d_canvas once. d_panorama and canvas.image.data
// are borrowed aliases. On failure both output views are empty, and any
// retained allocation remains owned by the workspace owner.
// Success publishes the dimensions, byte stride and A-to-canvas offsets on
// the Host after enqueue. Order Device consumers on stream or via an event,
// and wait for completion before Host access, reusing or freeing the workspace.
// Deferred CUDA errors surface at the caller's wait. The caller owns pixel D2H.
ErrorCode v4_warp_blend(DeviceWorkspace& workspace, const Config& config,
                        cudaStream_t stream = nullptr);

}  // namespace panorama
#endif  // __CUDACC__

#endif  // GROUP16_V4_WARP_BLEND_H
