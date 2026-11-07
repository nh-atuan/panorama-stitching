// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: src/v1/s5/v1_homography_scoring.cuh by Le Thuong De (23120232)
// Changes: MSAC model evaluation and selection logic for V2.

#ifndef GROUP16_V2_HOMOGRAPHY_SCORING_CUH
#define GROUP16_V2_HOMOGRAPHY_SCORING_CUH

#include "v2/s5/v2_homography_geometry.cuh"

namespace panorama { namespace homography_v2 {

__device__ inline ModelScore evaluate_msac(const Matrix3& matrix, const Buffer<Correspondence>& points,
                                            double threshold, double epsilon, Buffer<std::uint8_t>& mask) {
    mask.clear();
    const double threshold_squared = threshold * threshold;
    if (!isfinite(threshold) || threshold <= 0.0 || !isfinite(threshold_squared) ||
        !isfinite(epsilon) || epsilon <= 0.0 ||
        points.size() > static_cast<std::size_t>(INT32_MAX))
        return make_model_score(CUDART_INF, 0);
    mask.resize(points.size(), 0);
    std::int32_t count = 0;
    const double loss = ordered_sum(points.size(), [&](std::size_t i) {
        Point2 projected;
        if (!project(matrix, points[i].b, epsilon, projected)) return threshold_squared;
        const double dx = projected.x - points[i].a.x;
        const double dy = projected.y - points[i].a.y;
        const double error_squared = dx * dx + dy * dy;
        if (!isfinite(error_squared)) return threshold_squared;
        if (error_squared < threshold_squared) { mask[i] = 1; ++count; }
        return min_value(error_squared, threshold_squared);
    });
    return make_model_score(loss, count);
}

__device__ inline bool better_model(const ModelScore& candidate, std::int32_t candidate_id,
                                     const ModelScore& best, std::int32_t best_id) {
    if (!isfinite(candidate.loss) || candidate.inliers < 4 || candidate_id < 0) return false;
    if (best_id < 0) return true;
    if (candidate.loss != best.loss) return candidate.loss < best.loss;
    if (candidate.inliers != best.inliers) return candidate.inliers > best.inliers;
    return candidate_id < best_id;
}

} }  // namespace panorama::homography_v2

#endif  // GROUP16_V2_HOMOGRAPHY_SCORING_CUH
