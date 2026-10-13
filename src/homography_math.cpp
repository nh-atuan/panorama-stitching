// Authors: Le Thuong De (23120232)
// External source: none

#include "homography_math.h"
#include <algorithm>
#include <cmath>

namespace panorama {
namespace homography_detail {
namespace {
constexpr double kPivotEpsilon = 1e-12;
constexpr double kConditionEpsilon = 1e-12;
double infinity_norm(const Matrix3& matrix) {
    double maximum = 0.0;
    for (int row = 0; row < 3; ++row)
        maximum = std::max(maximum, (std::abs(matrix[3*row]) +
                           std::abs(matrix[3*row+1])) + std::abs(matrix[3*row+2]));
    return maximum;
}
}  // namespace

Matrix3 multiply(const Matrix3& left, const Matrix3& right) {
    Matrix3 result = {};
    for (int row = 0; row < 3; ++row)
        for (int column = 0; column < 3; ++column)
            result[3*row+column] = (left[3*row] * right[column] +
                left[3*row+1] * right[3+column]) + left[3*row+2] * right[6+column];
    return result;
}

bool normalize_scale(Matrix3& matrix) {
    double maximum = 0.0;
    int pivot = 0;
    for (int i = 0; i < 9; ++i) {
        if (!std::isfinite(matrix[i])) return false;
        if (std::abs(matrix[i]) > maximum) {
            maximum = std::abs(matrix[i]);
            pivot = i;
        }
    }
    if (maximum == 0.0) return false;
    // Fix overall sign as well as magnitude; both represent the same projective map.
    const double divisor = matrix[pivot] < 0.0 ? -maximum : maximum;
    for (double& coefficient : matrix) coefficient /= divisor;
    return true;
}

bool invert(const Matrix3& matrix, Matrix3& inverse) {
    inverse.fill(0.0);
    double augmented[3][6] = {};
    double scales[3] = {};
    for (int row = 0; row < 3; ++row) {
        for (int column = 0; column < 3; ++column) {
            const double value = matrix[3*row+column];
            if (!std::isfinite(value)) return false;
            augmented[row][column] = value;
            scales[row] = std::max(scales[row], std::abs(value));
        }
        if (scales[row] == 0.0) return false;
        augmented[row][3+row] = 1.0;
    }
    for (int column = 0; column < 3; ++column) {
        int pivot = column;
        for (int row = column+1; row < 3; ++row)
            if (std::abs(augmented[row][column])/scales[row] >
                std::abs(augmented[pivot][column])/scales[pivot]) pivot = row;
        if (std::abs(augmented[pivot][column]) <= kPivotEpsilon * scales[pivot]) return false;
        if (pivot != column) {
            for (int i = 0; i < 6; ++i) std::swap(augmented[pivot][i], augmented[column][i]);
            std::swap(scales[pivot], scales[column]);
        }
        const double diagonal = augmented[column][column];
        for (int i = 0; i < 6; ++i) augmented[column][i] /= diagonal;
        for (int row = 0; row < 3; ++row) {
            if (row == column) continue;
            const double factor = augmented[row][column];
            for (int i = 0; i < 6; ++i)
                augmented[row][i] -= factor * augmented[column][i];
        }
    }
    for (int row = 0; row < 3; ++row)
        for (int column = 0; column < 3; ++column) {
            inverse[3*row+column] = augmented[row][3+column];
            if (!std::isfinite(inverse[3*row+column])) return false;
        }
    const double product = infinity_norm(matrix) * infinity_norm(inverse);
    return std::isfinite(product) && product > 0.0 && 1.0/product >= kConditionEpsilon;
}

bool project(const Matrix3& matrix, const Point2& input,
              double epsilon, Point2& output) {
    const double u = (matrix[0]*input.x + matrix[1]*input.y) + matrix[2];
    const double v = (matrix[3]*input.x + matrix[4]*input.y) + matrix[5];
    const double wx = matrix[6]*input.x;
    const double wy = matrix[7]*input.y;
    const double w = (wx + wy) + matrix[8];
    const double magnitude = (std::abs(wx) + std::abs(wy)) + std::abs(matrix[8]);
    if (!std::isfinite(u) || !std::isfinite(v) || !std::isfinite(w) ||
        !std::isfinite(magnitude) || magnitude == 0.0 || std::abs(w) <= epsilon*magnitude)
        return false;
    output = Point2(u/w, v/w);
    return std::isfinite(output.x) && std::isfinite(output.y);
}

ErrorCode validate_matrix(Matrix3& matrix) {
    for (double value : matrix)
        if (!std::isfinite(value)) return ErrorCode::NumericalFailure;
    if (!normalize_scale(matrix)) return ErrorCode::DegenerateHomography;
    Matrix3 inverse = {};
    return invert(matrix, inverse) ? ErrorCode::Success : ErrorCode::DegenerateHomography;
}

}  // namespace homography_detail
}  // namespace panorama
