// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_HOMOGRAPHY_SCORING_H
#define GROUP16_HOMOGRAPHY_SCORING_H

#include "homography_math.h"
#include <vector>

namespace panorama {
namespace homography_detail {

struct ModelScore {
    double loss;
    std::int32_t inliers;
    ModelScore(double value=0.0,std::int32_t count=0) : loss(value),inliers(count) {}
};
ModelScore evaluate_msac(const Matrix3& matrix, const std::vector<Correspondence>& points,
                         double threshold, double epsilon, std::vector<std::uint8_t>& mask);
bool better_model(const ModelScore& candidate,std::int32_t candidate_id,
                   const ModelScore& best,std::int32_t best_id);

}  // namespace homography_detail
}  // namespace panorama

#endif
