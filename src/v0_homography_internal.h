// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_V0_HOMOGRAPHY_INTERNAL_H
#define GROUP16_V0_HOMOGRAPHY_INTERNAL_H

#include "common.h"
#include <array>
#include <vector>

// Internal declarations kept accessible to focused regression tests.
namespace panorama {
namespace homography_detail {

using Matrix3 = std::array<double, 9>;
struct Point2 {
    double x, y;
    Point2(double horizontal = 0.0, double vertical = 0.0) : x(horizontal), y(vertical) {}
};
struct Correspondence {
    Point2 a, b;
};

Matrix3 multiply(const Matrix3& left, const Matrix3& right);
bool normalize_scale(Matrix3& matrix);
bool invert(const Matrix3& matrix, Matrix3& inverse);
bool project(const Matrix3& matrix, const Point2& input,
              double epsilon, Point2& output);
ErrorCode validate_matrix(Matrix3& matrix);

// Direct one-sided Jacobi SVD of a row-major matrix with nine columns.
// Rotates matrix in place; returns all nine descending singular values and
// the smallest right singular vector, including the full 8x9 nullspace.
ErrorCode smallest_right_vector(std::vector<double>& matrix, std::size_t rows,
                                std::array<double, 9>& vector,
                                std::array<double, 9>& singular_values);

// Center/RMS normalize both point sets; direct homogeneous DLT; denormalize B -> A.
// Minimal=true adds duplicate/any-three-collinear sample checks (exactly four pairs).
// No allocation exceptions are suppressed; the stage boundary owns error conversion.
ErrorCode normalized_dlt(const std::vector<Correspondence>& points, bool minimal,
                         double denominator_epsilon, Matrix3& output);

bool uniform_sample4(std::uint32_t seed, std::int32_t hypothesis_id,
                      std::int32_t count, std::array<std::int32_t,4>& sample);
std::int32_t adaptive_iteration_budget(std::int32_t inliers, std::int32_t count,
                                       std::int32_t cap);

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
