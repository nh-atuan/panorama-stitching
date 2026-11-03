// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_BRIEF_KERNEL_CUH
#define GROUP16_V1_BRIEF_KERNEL_CUH

#include "common/brief_pattern.h"
#include "common/common.h"
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>

namespace panorama {
namespace v1_s3 {

// kBriefPattern in constant memory (1 KB): at test k every thread of a warp reads entry k.
// Filled once by v1_describe with cudaMemcpyToSymbolAsync on its first call.
static __constant__ BriefTest c_brief_pattern[kBriefTests];

// patch_centre of V0: centre rounded in double, compared with the bounds before the int cast.
__device__ inline bool patch_centre(const Keypoint& keypoint, std::int32_t width, std::int32_t height,
                                    std::int32_t& cx, std::int32_t& cy) {
    const double rx = floor(static_cast<double>(keypoint.x) + 0.5);
    const double ry = floor(static_cast<double>(keypoint.y) + 0.5);
    if (rx < kBriefPatchRadius || rx > width - 1 - kBriefPatchRadius) return false;
    if (ry < kBriefPatchRadius || ry > height - 1 - kBriefPatchRadius) return false;
    cx = static_cast<std::int32_t>(rx);
    cy = static_cast<std::int32_t>(ry);
    return true;
}

// describe_patch of V0 on the packed smoothed image: tests k = 0..255, bit k in data[k / 32].
__device__ inline Descriptor describe_patch(const float* smoothed, std::int32_t width, std::int32_t cx,
                                            std::int32_t cy) {
    const std::ptrdiff_t stride = static_cast<std::ptrdiff_t>(width);
    const float* centre = smoothed + static_cast<std::size_t>(cy) * static_cast<std::size_t>(width) + cx;
    Descriptor d;
    for (std::int32_t k = 0; k < kBriefTests; ++k) {
        const BriefTest t = c_brief_pattern[k];
        const float first = centre[t.ay * stride + t.ax];
        const float second = centre[t.by * stride + t.bx];
        if (first < second) d.data[k / 32] |= 1u << (k % 32);
    }
    return d;
}

}  // namespace v1_s3
}  // namespace panorama

#endif  // GROUP16_V1_BRIEF_KERNEL_CUH
