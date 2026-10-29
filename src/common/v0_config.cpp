// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "common/v0_config.h"
#include "common/feature_support.h"
#include <ostream>

namespace panorama {

ErrorCode make_v0_config(std::int32_t width_a, std::int32_t height_a, Config& config) {
    Config candidate;
    candidate.gaussian_sigma = kV0GaussianSigma;
    candidate.gaussian_radius = kV0GaussianRadius;
    candidate.fast_threshold = kV0FastThreshold;
    candidate.max_keypoints = kV0MaxKeypoints;
    candidate.max_canvas_pixels = kV0MaxCanvasPixels;
    const ErrorCode status = configure_v0_features(candidate, width_a, height_a);
    if (status != ErrorCode::Success) return status;
    config = candidate;
    return ErrorCode::Success;
}

void write_config(std::ostream& stream, const Config& config) {
    stream << "gaussian_sigma=" << config.gaussian_sigma
           << " gaussian_radius=" << config.gaussian_radius
           << " fast_threshold=" << config.fast_threshold
           << " max_keypoints=" << config.max_keypoints
           << " match_ratio_threshold=" << config.match_ratio_threshold
           << " match_cross_check=" << config.match_cross_check
           << " ransac_iters=" << config.ransac_iters
           << " ransac_threshold=" << config.ransac_threshold
           << " seed=" << config.seed
           << " homography_epsilon=" << config.homography_epsilon
           << " max_canvas_pixels=" << config.max_canvas_pixels << '\n';
}

}  // namespace panorama
