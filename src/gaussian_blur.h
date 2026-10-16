// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_GAUSSIAN_BLUR_H
#define GROUP16_GAUSSIAN_BLUR_H

#include "common.h"

namespace panorama {

// Separable blur of a valid gray image in place, borders clamped (repeat the edge pixel).
// Pass 1: image -> temp horizontally; pass 2: temp -> image vertically.
// `temp` holds width * height packed floats; `weights` holds 2 * radius + 1 values,
// index i for offset i - radius. Each pixel sums its taps from -radius to +radius in order,
// so repeated runs are bit-identical. Padding bytes of `image` are neither read nor written.
void gaussian_blur_in_place(GrayImage& image, float* temp, const float* weights,
                            std::int32_t radius);

}  // namespace panorama

#endif  // GROUP16_GAUSSIAN_BLUR_H
