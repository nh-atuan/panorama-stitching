// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_FEATURE_CONFIG_H
#define GROUP16_FEATURE_CONFIG_H

#include "common.h"

namespace panorama {
namespace feature_policy {

constexpr float kRatio = 0.80f;
constexpr std::int32_t kMaxIterations = 2000;
constexpr std::uint32_t kSeed = 16u;
constexpr double kConfidence = 0.99;
constexpr double kReferenceThreshold = 3.0;
constexpr double kDuplicateEpsilon = 1e-6;
constexpr double kAreaEpsilon = 1e-4;
constexpr double kRankEpsilon = 1e-10;

}  // namespace feature_policy

// Set only S4/S5 fields; preserve parameters owned by the other stages.
// A zero shared H epsilon receives the documented working value 1e-6f.
// Failure leaves config unchanged.
ErrorCode configure_v0_features(Config& config, std::int32_t width_a,
                                std::int32_t height_a);

}  // namespace panorama

#endif
