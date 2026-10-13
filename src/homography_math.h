// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_HOMOGRAPHY_MATH_H
#define GROUP16_HOMOGRAPHY_MATH_H

#include "common.h"
#include <array>

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

}  // namespace homography_detail
}  // namespace panorama

#endif
