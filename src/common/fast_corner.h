// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: Rosten and Drummond, "Machine learning for high-speed corner detection",
// ECCV 2006, https://www.edwardrosten.com/work/rosten_2006_machine.pdf, accessed 2026-10-16
// Changes: only the full segment test and the score V of the paper; no learned decision tree.

#ifndef GROUP16_FAST_CORNER_H
#define GROUP16_FAST_CORNER_H

#include <cstdint>

namespace panorama {

constexpr std::int32_t kFastCircleSize = 16;
constexpr std::int32_t kFastArcLength = 9;
constexpr std::int32_t kFastRadius = 3;

// Bresenham circle of radius 3 as (dx, dy), starting at the top and going clockwise on screen.
constexpr std::int32_t kFastCircle[kFastCircleSize][2] = {
    {0, -3}, {1, -3}, {2, -2}, {3, -1}, {3, 0}, {3, 1}, {2, 2}, {1, 3},
    {0, 3}, {-1, 3}, {-2, 2}, {-3, 1}, {-3, 0}, {-3, -1}, {-2, -2}, {-1, -3}};

// FAST-9 on one pixel. `ring[i]` is the intensity at kFastCircle[i] around a center of
// intensity `center`. With d_i = ring[i] - center (float), pixel i is bright when
// d_i > threshold and dark when d_i < -threshold. The pixel is a corner when at least
// kFastArcLength consecutive ring pixels (wrapping 15 -> 0) are all bright or all dark.
// Returns 0 for a non-corner, otherwise the score
//   V = max(sum over bright of (d_i - threshold), sum over dark of (-d_i - threshold)),
// summed in ring order; V > 0 for every corner.
float fast_corner_score(float center, const float ring[kFastCircleSize], float threshold);

}  // namespace panorama

#endif  // GROUP16_FAST_CORNER_H
