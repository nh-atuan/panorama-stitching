// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_HOMOGRAPHY_DLT_H
#define GROUP16_HOMOGRAPHY_DLT_H

#include "homography_math.h"
#include <vector>

namespace panorama {
namespace homography_detail {

// Center/RMS normalize both point sets; direct homogeneous DLT; denormalize B -> A.
// Minimal=true adds duplicate/any-three-collinear sample checks (exactly four pairs).
// No allocation exceptions are suppressed; the stage boundary owns error conversion.
ErrorCode normalized_dlt(const std::vector<Correspondence>& points, bool minimal,
                         double denominator_epsilon, Matrix3& output);

}  // namespace homography_detail
}  // namespace panorama

#endif
