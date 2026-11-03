// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_DESCRIBE_H
#define GROUP16_V1_DESCRIBE_H

#include "common/common.h"
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>

namespace panorama {

// Bytes of scratch S3 needs for one image: smoothed image and blur temp (W*H floats each),
// a 16-byte counter, then keep flags and compacted keypoints for `keypoint_capacity` entries.
// Returns 0 when a dimension is not positive or the size overflows. The caller takes the
// max over A and B and allocates d_scratch (16-byte aligned) before the timed region.
std::size_t v1_describe_scratch_bytes(std::int32_t width, std::int32_t height, std::size_t keypoint_capacity);

// S3 of V1 for both images: BRIEF-256 of d_keypointsA on grayA, then of d_keypointsB on grayB.
// Same result as v0_describe bit for bit: kept keypoints in their input order, compacted in place,
// and descriptors[i] for keypoints[i]. Input counts come from d_counts->keypointsA/B; on success
// keypointsA/B and descriptorsA/B are both set to the kept count. The gray images are not written.
// Host checks, in order: gray images (InvalidImage), then the workspace (InvalidArgument):
// d_counts, keypoint and descriptor buffers present, descriptor capacity >= keypoint capacity,
// keypoint capacity <= INT32_MAX, scratch present, 16-byte aligned and large enough.
// Device checks write d_counts->status like S4: a count above the keypoint capacity or a
// non-finite coordinate gives InvalidArgument, keypoints unchanged and descriptor counts 0.
// Does nothing on the Device when d_counts->status already holds an error.
// The first call copies kBriefPattern to constant memory and synchronizes `stream` once, so
// it belongs in the warm-up run. Returns CudaFailure when a CUDA call fails.
ErrorCode v1_describe(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V1_DESCRIBE_H
