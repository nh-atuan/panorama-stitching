// Authors: Group 16
// External source: none

#ifndef GROUP16_V0_WARP_BLEND_H
#define GROUP16_V0_WARP_BLEND_H

#include "common.h"

namespace panorama {

// Input images are borrowed RGB views; H maps B into A.
// Output must be empty on entry. On success its new[] buffer belongs to the caller,
// who must delete[] output.image.data and reset output before calling again.
// On failure an initially empty output remains empty.
// Pass debug_mode=false inside benchmark timing regions.
ErrorCode v0_warp_blend(const Image& left, const Image& right,
                       const Homography& homography, Panorama& output,
                       const Config& config, bool debug_mode = false);

}  // namespace panorama

#endif  // GROUP16_V0_WARP_BLEND_H
