// Authors: Tran Huu Kim Thanh (23120166)
// Adapted from: Rosten and Drummond, "Machine learning for high-speed corner detection",
// ECCV 2006, https://www.edwardrosten.com/work/rosten_2006_machine.pdf, accessed 2026-10-16
// Changes: Device version of the segment test and score V of src/common/fast_corner.cpp,
// one thread per pixel; same comparisons and summation order, no learned decision tree.

#ifndef GROUP16_V1_FAST_SCORE_CUH
#define GROUP16_V1_FAST_SCORE_CUH

#include "common/fast_corner.h"
#include "common/feature_border.h"
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>

namespace panorama {
namespace v1_s2 {

// kFastCircle as (dx, dy), in Device constant memory: every thread of a warp reads the same entry.
static __constant__ std::int32_t c_fast_circle[kFastCircleSize][2] = {
    {0, -3}, {1, -3}, {2, -2}, {3, -1}, {3, 0}, {3, 1}, {2, 2}, {1, 3},
    {0, 3}, {-1, 3}, {-2, 2}, {-3, 1}, {-3, 0}, {-3, -1}, {-2, -2}, {-1, -3}};

__device__ inline float gray_at(const unsigned char* gray, std::size_t stride, std::int32_t x, std::int32_t y) {
    return reinterpret_cast<const float*>(gray + static_cast<std::size_t>(y) * stride)[x];
}

// fast_corner_score of V0 for the pixel (x, y): 0 for a non-corner, otherwise score V.
__device__ inline float fast_score_at(const unsigned char* gray, std::size_t stride, std::int32_t x,
                                      std::int32_t y, float threshold) {
    const float center = gray_at(gray, stride, x, y);
    float ring[kFastCircleSize];
    std::int32_t state[kFastCircleSize];
    for (std::int32_t i = 0; i < kFastCircleSize; ++i) {
        ring[i] = gray_at(gray, stride, x + c_fast_circle[i][0], y + c_fast_circle[i][1]);
        const float d = ring[i] - center;
        state[i] = d > threshold ? 1 : (d < -threshold ? -1 : 0);
    }
    bool corner = false;
    std::int32_t bright_run = 0, dark_run = 0;
    for (std::int32_t step = 0; step < kFastCircleSize + kFastArcLength - 1; ++step) {
        const std::int32_t s = state[step % kFastCircleSize];
        bright_run = s > 0 ? bright_run + 1 : 0;
        dark_run = s < 0 ? dark_run + 1 : 0;
        if (bright_run >= kFastArcLength || dark_run >= kFastArcLength) {
            corner = true;
            break;
        }
    }
    if (!corner) return 0.0f;
    float bright_sum = 0.0f, dark_sum = 0.0f;
    for (std::int32_t i = 0; i < kFastCircleSize; ++i) {
        const float d = ring[i] - center;
        if (state[i] > 0) bright_sum += d - threshold;
        if (state[i] < 0) dark_sum += -d - threshold;
    }
    return bright_sum > dark_sum ? bright_sum : dark_sum;
}

// scores (packed, width per row, zeroed before) = FAST score in the border region.
// Grid covers (width - 2 * border) x (height - 2 * border) pixels.
__global__ void fast_score_kernel(const unsigned char* gray, std::size_t stride, std::int32_t width,
                                  std::int32_t height, float threshold, float* scores) {
    const std::int32_t x = kFeatureBorder + static_cast<std::int32_t>(blockIdx.x * blockDim.x + threadIdx.x);
    const std::int32_t y = kFeatureBorder + static_cast<std::int32_t>(blockIdx.y * blockDim.y + threadIdx.y);
    if (x >= width - kFeatureBorder || y >= height - kFeatureBorder) return;
    scores[static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + x] =
        fast_score_at(gray, stride, x, y, threshold);
}

}  // namespace v1_s2
}  // namespace panorama

#endif  // GROUP16_V1_FAST_SCORE_CUH
