// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_FEATURE_BORDER_H
#define GROUP16_FEATURE_BORDER_H

#include <cstdint>

namespace panorama {

// Keypoints keep this many pixels to every image edge: 15 <= x <= width - 16, same for y.
// Covers the FAST circle (radius 3) and the 31 x 31 BRIEF patch (radius 15), so S3 never
// drops a keypoint produced by S2.
constexpr std::int32_t kFeatureBorder = 15;

}  // namespace panorama

#endif  // GROUP16_FEATURE_BORDER_H
