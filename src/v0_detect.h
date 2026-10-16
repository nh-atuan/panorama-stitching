// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_V0_DETECT_H
#define GROUP16_V0_DETECT_H

#include "common.h"
#include <vector>

namespace panorama {

// Upper bound accepted for config.max_keypoints.
constexpr std::int32_t kMaxKeypointsLimit = 1000000;

// FAST-9 keypoints of one gray image in [0, 1] (S1 output).
// Candidates lie in [kFeatureBorder, width - 1 - kFeatureBorder] x [same for y]; 3 x 3
// non-maximum suppression keeps a pixel unless a neighbour has a higher score, or the same
// score and a smaller raster index (y * width + x). Survivors are sorted by score descending,
// then raster index ascending, and the first config.max_keypoints are returned.
// Keypoints have integer coordinates (pixel centres), score = FAST score V, angle = 0.
// Uses config.fast_threshold (finite, 0 < t < 1) and config.max_keypoints
// (1 <= n <= kMaxKeypointsLimit). An image too small for the border gives an empty result.
// `output` is cleared on entry and filled only on Success.
// Errors: InvalidImage, InvalidConfig, AllocationFailed.
// Pass debug_mode=false inside benchmark timing regions; debug only logs to stderr.
ErrorCode v0_detect(const GrayImage& image, std::vector<Keypoint>& output,
                    const Config& config, bool debug_mode = false);

}  // namespace panorama

#endif  // GROUP16_V0_DETECT_H
