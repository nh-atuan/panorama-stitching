// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_HOMOGRAPHY_SAMPLING_H
#define GROUP16_HOMOGRAPHY_SAMPLING_H

#include <array>
#include <cstdint>

namespace panorama {
namespace homography_detail {

bool uniform_sample4(std::uint32_t seed, std::int32_t hypothesis_id,
                      std::int32_t count, std::array<std::int32_t,4>& sample);
std::int32_t adaptive_iteration_budget(std::int32_t inliers, std::int32_t count,
                                       std::int32_t cap);

}  // namespace homography_detail
}  // namespace panorama

#endif
