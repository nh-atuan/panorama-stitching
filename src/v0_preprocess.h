// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_V0_PREPROCESS_H
#define GROUP16_V0_PREPROCESS_H

#include "common.h"

namespace panorama {

// Converts one packed-or-padded RGB image to a blurred gray image in [0, 1].
// `output` is allocated by the caller before the timed region: non-null data, same width and
// height as `input`, channels 1, stride in bytes >= width * sizeof(float) and a multiple of
// sizeof(float). Padding bytes of both images are neither read nor written.
// S1 allocates one temporary float buffer (width * height) per call; that time counts as S1.
// Uses config.gaussian_sigma and config.gaussian_radius. On error `output` is left untouched.
// Errors: InvalidImage, InvalidConfig, AllocationFailed.
// Pass debug_mode=false inside benchmark timing regions; debug only logs to stderr.
ErrorCode v0_preprocess(const Image& input, GrayImage& output,
                        const Config& config, bool debug_mode = false);

}  // namespace panorama

#endif  // GROUP16_V0_PREPROCESS_H
