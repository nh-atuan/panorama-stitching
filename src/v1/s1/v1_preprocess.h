// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_PREPROCESS_H
#define GROUP16_V1_PREPROCESS_H

#include "common/common.h"
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>

namespace panorama {

// Bytes of scratch S1 needs for one image (the blur temp buffer, width * height floats).
// Returns 0 when width or height is not positive or the size overflows.
// The caller takes the max over A and B and allocates d_scratch before the timed region.
std::size_t v1_preprocess_scratch_bytes(std::int32_t width, std::int32_t height);

// S1 of V1 for both images: imageA -> grayA, then imageB -> grayB, on `stream`.
// Each image: grayscale kernel, then v1_gaussian_blur in place with config.gaussian_sigma and
// config.gaussian_radius. Matches v0_preprocess bit for bit with --fmad=false.
// Views in the workspace point to Device memory, strides in bytes; padding is not touched.
// Checks, in order: images (InvalidImage), config (InvalidConfig), then d_scratch present,
// 4-byte aligned and at least the max scratch of A and B (InvalidArgument). Nothing is enqueued
// on an error, so gray outputs are left untouched. S1 has no Device-side error, so d_counts is
// not read or written. Returns CudaFailure when a launch fails. Does not allocate Device memory.
ErrorCode v1_preprocess(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V1_PREPROCESS_H
