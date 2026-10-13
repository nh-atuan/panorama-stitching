// Authors: Le Thuong De (23120232)
// Adapted from: one-sided Jacobi SVD mathematical descriptions in Drmac and Veselic,
// LAPACK Working Note 170, https://www.netlib.org/lapack/lawnspdf/lawn170.pdf,
// accessed 2026-10-13. No LAPACK implementation copied or linked.
// Changes: unpreconditioned cyclic nine-column solver, full right basis,
// deterministic tree dot products, relative null-column handling and error status.

#include "homography_svd.h"
#include "ordered_reduction.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace panorama {
namespace homography_detail {
namespace {
constexpr int kMaxSweeps = 128;
constexpr double kOrthogonalityTolerance = 16.0 * std::numeric_limits<double>::epsilon();
double column_dot(const std::vector<double>& matrix, std::size_t rows, int p, int q) {
    return ordered_sum(rows, [&](std::size_t row) {
        return matrix[9*row+p] * matrix[9*row+q];
    });
}
}  // namespace

ErrorCode smallest_right_vector(std::vector<double>& matrix, std::size_t rows,
                                std::array<double, 9>& vector,
                                std::array<double, 9>& singular_values) {
    vector.fill(0.0);
    singular_values.fill(0.0);
    if (rows < 8 || rows > std::numeric_limits<std::size_t>::max()/9 ||
        matrix.size() != rows*9) return ErrorCode::InvalidArgument;
    for (double value : matrix)
        if (!std::isfinite(value)) return ErrorCode::NumericalFailure;
    const double norm_squared = ordered_sum(matrix.size(), [&](std::size_t i) {
        return matrix[i]*matrix[i];
    });
    if (!std::isfinite(norm_squared)) return ErrorCode::NumericalFailure;
    if (norm_squared == 0.0) return ErrorCode::DegenerateHomography;
    const double null_floor = kOrthogonalityTolerance*kOrthogonalityTolerance*norm_squared;
    std::array<double, 81> right = {};
    for (int i = 0; i < 9; ++i) right[9*i+i] = 1.0;
    bool converged = false;
    for (int sweep = 0; sweep < kMaxSweeps; ++sweep) {
        bool changed = false;
        for (int p = 0; p < 8; ++p) {
            for (int q = p+1; q < 9; ++q) {
                const double alpha = column_dot(matrix,rows,p,p);
                const double beta = column_dot(matrix,rows,q,q);
                const double gamma = column_dot(matrix,rows,p,q);
                if (!std::isfinite(alpha) || !std::isfinite(beta) || !std::isfinite(gamma))
                    return ErrorCode::NumericalFailure;
                if (alpha <= null_floor || beta <= null_floor ||
                    std::abs(gamma) <= kOrthogonalityTolerance*std::sqrt(alpha)*std::sqrt(beta))
                    continue;
                const double theta = (beta-alpha)/(2.0*gamma);
                const double tangent = std::copysign(
                    1.0/(std::abs(theta) + std::hypot(1.0,theta)),theta);
                const double cosine = 1.0/std::hypot(1.0,tangent);
                const double sine = cosine*tangent;
                if (!std::isfinite(theta) || !std::isfinite(cosine) || !std::isfinite(sine))
                    return ErrorCode::NumericalFailure;
                for (std::size_t row = 0; row < rows; ++row) {
                    const double a = matrix[9*row+p], b = matrix[9*row+q];
                    matrix[9*row+p] = cosine*a - sine*b;
                    matrix[9*row+q] = sine*a + cosine*b;
                }
                for (int row = 0; row < 9; ++row) {
                    const double a = right[9*row+p], b = right[9*row+q];
                    right[9*row+p] = cosine*a - sine*b;
                    right[9*row+q] = sine*a + cosine*b;
                }
                changed = true;
            }
        }
        if (!changed) { converged = true; break; }
    }
    if (!converged) return ErrorCode::NumericalFailure;
    std::array<double, 9> norms = {};
    std::array<int, 9> order = {{0,1,2,3,4,5,6,7,8}};
    for (int column = 0; column < 9; ++column)
        norms[column] = std::sqrt(column_dot(matrix,rows,column,column));
    std::sort(order.begin(),order.end(),[&](int p, int q) {
        return norms[p] > norms[q] || (norms[p] == norms[q] && p < q);
    });
    for (int i = 0; i < 9; ++i) {
        singular_values[i] = norms[order[i]];
        vector[i] = right[9*i+order[8]];
    }
    return ErrorCode::Success;
}

}  // namespace homography_detail
}  // namespace panorama
