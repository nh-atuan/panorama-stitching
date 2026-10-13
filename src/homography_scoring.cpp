// Authors: Le Thuong De (23120232)
// Adapted from: MSAC/error descriptions in OpenCV USAC documentation,
// https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html, accessed 2026-10-13.
// Changes: double forward B-to-A error, strict threshold, invalid projections
// capped as outliers, fixed tree reduction and deterministic score/count/ID ties.
// No external implementation copied or linked.

#include "homography_scoring.h"
#include "ordered_reduction.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace panorama {
namespace homography_detail {

ModelScore evaluate_msac(const Matrix3& matrix, const std::vector<Correspondence>& points,
                         double threshold, double epsilon, std::vector<std::uint8_t>& mask) {
    mask.clear();
    const double threshold_squared=threshold*threshold;
    if(!std::isfinite(threshold) || threshold<=0.0 || !std::isfinite(threshold_squared) ||
       !std::isfinite(epsilon) || epsilon<=0.0 ||
       points.size()>static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max()))
        return ModelScore(std::numeric_limits<double>::infinity(),0);
    mask.resize(points.size(),0);
    std::int32_t count=0;
    const double loss=ordered_sum(points.size(),[&](std::size_t i) {
        Point2 projected;
        if(!project(matrix,points[i].b,epsilon,projected)) return threshold_squared;
        const double dx=projected.x-points[i].a.x;
        const double dy=projected.y-points[i].a.y;
        const double error_squared=dx*dx+dy*dy;
        if(!std::isfinite(error_squared)) return threshold_squared;
        if(error_squared<threshold_squared) {mask[i]=1;++count;}
        return std::min(error_squared,threshold_squared);
    });
    return ModelScore(loss,count);
}

bool better_model(const ModelScore& candidate,std::int32_t candidate_id,
                   const ModelScore& best,std::int32_t best_id) {
    if(!std::isfinite(candidate.loss) || candidate.inliers<4 || candidate_id<0) return false;
    if(best_id<0) return true;
    if(candidate.loss!=best.loss) return candidate.loss<best.loss;
    if(candidate.inliers!=best.inliers) return candidate.inliers>best.inliers;
    return candidate_id<best_id;
}

}  // namespace homography_detail
}  // namespace panorama
