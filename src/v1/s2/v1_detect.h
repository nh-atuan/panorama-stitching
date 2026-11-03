// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_DETECT_H
#define GROUP16_V1_DETECT_H

#include "common/common.h"
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>

namespace panorama {

// Bytes of scratch S2 needs for one image: score map (W*H floats), candidate counter and
// candidate keys (ceil(W/2) * ceil(H/2) rounded up to a power of two, 8 bytes each).
// Returns 0 when the image has no candidate region (a side <= 30), when a dimension is not
// positive, or when W*H does not fit in 32 bits. The caller takes the max over A and B and
// allocates d_scratch (16-byte aligned) before the timed region.
std::size_t v1_detect_scratch_bytes(std::int32_t width, std::int32_t height);

// S2 of V1 for both images: grayA -> d_keypointsA, then grayB -> d_keypointsB, on `stream`.
// Same result as v0_detect bit for bit: coordinates, score bits and order. Writes
// d_counts->keypointsA and keypointsB; d_counts->status is neither read nor written,
// since S2 has no Device-side error. An image with a side <= 30 gives 0 keypoints.
// Checks, in order: gray images (InvalidImage), config (InvalidConfig), then the workspace
// (InvalidArgument): d_counts present, d_keypoints present with capacity >= max_keypoints,
// W*H < 2^32, scratch present, 16-byte aligned and large enough. Nothing is enqueued on an error.
// Synchronizes `stream` once per image to read the candidate count. Returns CudaFailure when a
// CUDA call fails. Does not allocate Device memory.
ErrorCode v1_detect(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V1_DETECT_H
