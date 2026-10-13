// Authors: Le Thuong De (23120232)
// External source: none

#include "feature_support.h"
#include <cmath>

namespace panorama {

ErrorCode configure_v0_features(Config& config, std::int32_t width_a,
                                std::int32_t height_a) {
    if (width_a <= 0 || height_a <= 0) return ErrorCode::InvalidArgument;
    if (!std::isfinite(config.homography_epsilon) || config.homography_epsilon < 0.0f)
        return ErrorCode::InvalidConfig;
    Config candidate = config;
    candidate.match_ratio_threshold = feature_policy::kRatio;
    candidate.match_cross_check = 0u;
    candidate.ransac_iters = feature_policy::kMaxIterations;
    candidate.seed = feature_policy::kSeed;
    candidate.ransac_threshold = static_cast<float>(
        feature_policy::kReferenceThreshold *
        std::hypot(static_cast<double>(width_a), static_cast<double>(height_a)) /
        std::hypot(1920.0, 1080.0));
    if (candidate.homography_epsilon == 0.0f) candidate.homography_epsilon = 1e-6f;
    config = candidate;
    return ErrorCode::Success;
}

}  // namespace panorama
