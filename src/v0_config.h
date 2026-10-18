// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_V0_CONFIG_H
#define GROUP16_V0_CONFIG_H

#include "common.h"
#include <iosfwd>

namespace panorama {

// Parameters chosen in the stage design documents (section 3 of docs/stages/s*.md).
// Every version uses the same values so that timings stay comparable.
constexpr float kV0GaussianSigma = 1.0f;  // S1, Tuan
constexpr std::int32_t kV0GaussianRadius = 3;  // S1, Tuan
constexpr float kV0FastThreshold = 0.05f;  // S2, proposed for Thanh, not yet confirmed
constexpr std::int32_t kV0MaxKeypoints = 2000;  // S2, proposed for Thanh, not yet confirmed
constexpr std::uint64_t kV0MaxCanvasPixels = 100000000ULL;  // S6, Chuong

// Fills every algorithm field of `config` from a default Config. S4/S5 fields come from
// configure_v0_features (De), whose RANSAC threshold scales with the size of image A.
// Errors: InvalidArgument when a dimension is not positive; `config` is then unchanged.
ErrorCode make_v0_config(std::int32_t width_a, std::int32_t height_a, Config& config);

// One line "name=value ..." with every Config field, for logs outside timing regions.
void write_config(std::ostream& stream, const Config& config);

}  // namespace panorama

#endif  // GROUP16_V0_CONFIG_H
