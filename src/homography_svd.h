// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_HOMOGRAPHY_SVD_H
#define GROUP16_HOMOGRAPHY_SVD_H

#include "common.h"
#include <array>
#include <vector>

namespace panorama {
namespace homography_detail {

// Direct one-sided Jacobi SVD of a row-major matrix with nine columns.
// Rotates matrix in place; returns all nine descending singular values and
// the smallest right singular vector, including the full 8x9 nullspace.
ErrorCode smallest_right_vector(std::vector<double>& matrix, std::size_t rows,
                                std::array<double, 9>& vector,
                                std::array<double, 9>& singular_values);

}  // namespace homography_detail
}  // namespace panorama

#endif
