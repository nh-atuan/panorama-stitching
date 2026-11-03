// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_NMS_CUH
#define GROUP16_V1_NMS_CUH

#include "common/feature_border.h"
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>

namespace panorama {
namespace v1_s2 {

// Sort key of a candidate: ascending key order = score descending, then raster ascending.
// Scores are positive, so their bit patterns order like the floats; the high word is inverted.
// A real key is always below kPaddingKey, since ~bits(score) <= 0xFFFFFFFE for score > 0.
constexpr unsigned long long kPaddingKey = ~0ULL;

__device__ inline unsigned long long candidate_key(float score, std::uint32_t raster) {
    const std::uint32_t high = ~static_cast<std::uint32_t>(__float_as_uint(score));
    return (static_cast<unsigned long long>(high) << 32) | raster;
}

__device__ inline float key_score(unsigned long long key) {
    return __uint_as_float(~static_cast<std::uint32_t>(key >> 32));
}

__device__ inline std::uint32_t key_raster(unsigned long long key) {
    return static_cast<std::uint32_t>(key & 0xFFFFFFFFULL);
}

// 3 x 3 NMS like is_local_maximum of V0: a neighbour with a higher score, or the same score
// and an earlier raster position, suppresses the pixel. Survivors get a slot by atomicAdd;
// their order in `keys` depends on scheduling, but keys are unique so the sorted result is not.
// Grid covers the border region; the score map is 0 outside it.
__global__ void nms_kernel(const float* scores, std::int32_t width, std::int32_t height,
                           std::uint32_t* count, unsigned long long* keys, std::uint32_t capacity) {
    const std::int32_t x = kFeatureBorder + static_cast<std::int32_t>(blockIdx.x * blockDim.x + threadIdx.x);
    const std::int32_t y = kFeatureBorder + static_cast<std::int32_t>(blockIdx.y * blockDim.y + threadIdx.y);
    if (x >= width - kFeatureBorder || y >= height - kFeatureBorder) return;
    const std::size_t w = static_cast<std::size_t>(width);
    const float s = scores[static_cast<std::size_t>(y) * w + x];
    if (!(s > 0.0f)) return;
    for (std::int32_t dy = -1; dy <= 1; ++dy) {
        for (std::int32_t dx = -1; dx <= 1; ++dx) {
            if (dx == 0 && dy == 0) continue;
            const float q = scores[static_cast<std::size_t>(y + dy) * w + (x + dx)];
            const bool earlier = dy < 0 || (dy == 0 && dx < 0);
            if (q > s || (earlier && q == s)) return;
        }
    }
    const std::uint32_t slot = atomicAdd(count, 1u);
    // Survivors are never 8-adjacent, so capacity ceil(W/2) * ceil(H/2) cannot overflow.
    const std::uint32_t raster =
        static_cast<std::uint32_t>(y) * static_cast<std::uint32_t>(width) + static_cast<std::uint32_t>(x);
    if (slot < capacity) keys[slot] = candidate_key(s, raster);
}

}  // namespace v1_s2
}  // namespace panorama

#endif  // GROUP16_V1_NMS_CUH
