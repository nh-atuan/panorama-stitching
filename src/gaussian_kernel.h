// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_GAUSSIAN_KERNEL_H
#define GROUP16_GAUSSIAN_KERNEL_H

#include "common.h"

namespace panorama {

// Largest supported kernel radius; bounds the halo of the shared-memory tiles in V2.
constexpr std::int32_t kMaxGaussianRadius = 16;

// Valid when sigma is finite and > 0, 1 <= radius <= kMaxGaussianRadius and
// radius >= ceil(2 * sigma). Returns InvalidConfig otherwise.
ErrorCode validate_gaussian_params(float sigma, std::int32_t radius);

// Writes 2 * radius + 1 normalized weights (sum 1) to `weights`, index i for offset i - radius.
// Weights are computed in double and rounded to float, so every version shares the same values.
// Returns InvalidConfig (and writes nothing) when the parameters are invalid.
ErrorCode make_gaussian_weights(float sigma, std::int32_t radius, float* weights);

}  // namespace panorama

#endif  // GROUP16_GAUSSIAN_KERNEL_H
