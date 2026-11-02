// Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185)
// Adapted from: one-sided Jacobi SVD mathematical descriptions in Drmac and Veselic,
// LAPACK Working Note 170, https://www.netlib.org/lapack/lawnspdf/lawn170.pdf,
// accessed 2026-10-13. No LAPACK implementation copied or linked.
// Changes: unpreconditioned cyclic nine-column solver, full right basis,
// deterministic tree dot products, relative null-column handling and error status.
// Adapted from: Harker and O'Leary, Computation of Homographies, section 2.3,
// https://www.robots.ox.ac.uk/~phst/BMVC2005/papers/190/paper190.pdf,
// accessed 2026-10-13. No external implementation copied.
// Changes: RMS normalization with fixed reductions, direct full-basis Jacobi SVD,
// B-to-A convention, minimal geometry/rank checks and project error handling.
// Adapted from: Sebastiano Vigna's public-domain SplitMix64 reference,
// https://prng.di.unimi.it/splitmix64.c, accessed 2026-10-13;
// standard RANSAC termination described in OpenCV USAC documentation,
// https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html, accessed 2026-10-13.
// Changes: per-hypothesis stream initialization, rejection-bounded sampling,
// unique draw order, guarded confidence budget and no external RNG dependency.
// Adapted from: MSAC/error descriptions in OpenCV USAC documentation,
// https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html, accessed 2026-10-13.
// Changes: double forward B-to-A error, strict threshold, invalid projections
// capped as outliers, fixed tree reduction and deterministic score/count/ID ties.
// No external implementation copied or linked.
// Adapted from: Brown and Lowe (2007), https://www.cs.ubc.ca/~lowe/papers/07brown.pdf,
// accessed 2026-10-13; OpenCV USAC algorithm descriptions,
// https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html, accessed 2026-10-13;
// Fowler/Noll/Vo, https://www.isthe.com/chongo/tech/comp/fnv/index.html,
// accessed 2026-10-13.
// Changes: project-specific uniform sample streams, normalized DLT double,
// MSAC/prefix-adaptive selection, bounded all-inlier refits, float output validation
// and Host diagnostics separated from stage I/O. The FNV-style fingerprint hashes
// whole sample indices rather than bytes. No external estimator copied.
// Changes: consolidated translation units; original functions and arithmetic preserved.

// Changes: Device-only port using caller-owned buffers; V0 source is unchanged.

#ifndef GROUP16_V1_HOMOGRAPHY_GEOMETRY_CUH
#define GROUP16_V1_HOMOGRAPHY_GEOMETRY_CUH
#include "common/common.h"
#include "common/feature_support.h"
#include <cuda_runtime.h>
#include <math_constants.h>
#include <cmath>
#include <limits>
namespace panorama { namespace homography_gpu {
template<class T, std::size_t N> struct Array {
    T values[N];
    __device__ T& operator[](std::size_t i) { return values[i]; }
    __device__ const T& operator[](std::size_t i) const { return values[i]; }
    __device__ T* begin() { return values; }
    __device__ T* end() { return values+N; }
    __device__ const T* begin() const { return values; }
    __device__ const T* end() const { return values+N; }
    __device__ void fill(T value) { for(std::size_t i=0;i<N;++i) values[i]=value; }
};
template<class T> struct Buffer {
    T* data; std::size_t count;
    __device__ Buffer(T* p=nullptr, std::size_t n=0) : data(p),count(n) {}
    __device__ std::size_t size() const { return count; }
    __device__ void clear() { count=0; }
    __device__ void resize(std::size_t n) { count=n; }
    __device__ void resize(std::size_t n, T value) { count=n; for(std::size_t i=0;i<n;++i) data[i]=value; }
    __device__ T& operator[](std::size_t i) { return data[i]; }
    __device__ const T& operator[](std::size_t i) const { return data[i]; }
    __device__ T* begin() const { return data; }
    __device__ T* end() const { return data+count; }
};
template<class T> __device__ inline T max_value(T a,T b) { return a<b?b:a; }
template<class T> __device__ inline T min_value(T a,T b) { return b<a?b:a; }
template<class T> __device__ inline void swap_value(T& a,T& b) { T c=a;a=b;b=c; }
using Matrix3=Array<double,9>;
struct Point2 {
    double x,y;
    __host__ __device__ Point2(double a=0,double b=0) : x(a),y(b) {}
};
struct Correspondence { Point2 a,b; };
struct ModelScore {
    double loss; std::int32_t inliers;
    __device__ ModelScore(double v=0,std::int32_t n=0) : loss(v),inliers(n) {}
};
// Ordered reduction.
// Fixed binary tree with leaves in input order and zero padding.
template <typename Getter>
__device__ inline double sum_subtree(const Getter& get, std::size_t count,
                   std::size_t first, std::size_t width) {
    if (first >= count) return 0.0;
    if (width == 1) return get(first);
    const std::size_t half = width / 2;
    const double left = sum_subtree(get, count, first, half);
    const double right = sum_subtree(get, count, first + half, half);
    return left + right;
}

template <typename Getter>
__device__ inline double ordered_sum(std::size_t count, const Getter& get) {
    if (count == 0) return 0.0;
    // Feature counts are int32; DLT uses at most twice that count.
    std::size_t width = 1;
    while (width < count) width *= 2;
    return sum_subtree(get, count, 0, width);
}

// Matrix geometry.
namespace {
constexpr double kPivotEpsilon = 1e-12;
constexpr double kConditionEpsilon = 1e-12;
__device__ inline double infinity_norm(const Matrix3& matrix) {
    double maximum = 0.0;
    for (int row = 0; row < 3; ++row)
        maximum = max_value(maximum, (fabs(matrix[3*row]) +
                           fabs(matrix[3*row+1])) + fabs(matrix[3*row+2]));
    return maximum;
}
}  // namespace

__device__ inline Matrix3 multiply(const Matrix3& left, const Matrix3& right) {
    Matrix3 result = {};
    for (int row = 0; row < 3; ++row)
        for (int column = 0; column < 3; ++column)
            result[3*row+column] = (left[3*row] * right[column] +
                left[3*row+1] * right[3+column]) + left[3*row+2] * right[6+column];
    return result;
}

__device__ inline bool normalize_scale(Matrix3& matrix) {
    double maximum = 0.0;
    int pivot = 0;
    for (int i = 0; i < 9; ++i) {
        if (!isfinite(matrix[i])) return false;
        if (fabs(matrix[i]) > maximum) {
            maximum = fabs(matrix[i]);
            pivot = i;
        }
    }
    if (maximum == 0.0) return false;
    // Fix overall sign as well as magnitude; both represent the same projective map.
    const double divisor = matrix[pivot] < 0.0 ? -maximum : maximum;
    for (double& coefficient : matrix) coefficient /= divisor;
    return true;
}

__device__ inline bool invert(const Matrix3& matrix, Matrix3& inverse) {
    inverse.fill(0.0);
    double augmented[3][6] = {};
    double scales[3] = {};
    for (int row = 0; row < 3; ++row) {
        for (int column = 0; column < 3; ++column) {
            const double value = matrix[3*row+column];
            if (!isfinite(value)) return false;
            augmented[row][column] = value;
            scales[row] = max_value(scales[row], fabs(value));
        }
        if (scales[row] == 0.0) return false;
        augmented[row][3+row] = 1.0;
    }
    for (int column = 0; column < 3; ++column) {
        int pivot = column;
        for (int row = column+1; row < 3; ++row)
            if (fabs(augmented[row][column])/scales[row] >
                fabs(augmented[pivot][column])/scales[pivot]) pivot = row;
        if (fabs(augmented[pivot][column]) <= kPivotEpsilon * scales[pivot]) return false;
        if (pivot != column) {
            for (int i = 0; i < 6; ++i) swap_value(augmented[pivot][i], augmented[column][i]);
            swap_value(scales[pivot], scales[column]);
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
            if (!isfinite(inverse[3*row+column])) return false;
        }
    const double product = infinity_norm(matrix) * infinity_norm(inverse);
    return isfinite(product) && product > 0.0 && 1.0/product >= kConditionEpsilon;
}

__device__ inline bool project(const Matrix3& matrix, const Point2& input,
              double epsilon, Point2& output) {
    const double u = (matrix[0]*input.x + matrix[1]*input.y) + matrix[2];
    const double v = (matrix[3]*input.x + matrix[4]*input.y) + matrix[5];
    const double wx = matrix[6]*input.x;
    const double wy = matrix[7]*input.y;
    const double w = (wx + wy) + matrix[8];
    const double magnitude = (fabs(wx) + fabs(wy)) + fabs(matrix[8]);
    if (!isfinite(u) || !isfinite(v) || !isfinite(w) ||
        !isfinite(magnitude) || magnitude == 0.0 || fabs(w) <= epsilon*magnitude)
        return false;
    output = Point2(u/w, v/w);
    return isfinite(output.x) && isfinite(output.y);
}

__device__ inline ErrorCode validate_matrix(Matrix3& matrix) {
    for (double value : matrix)
        if (!isfinite(value)) return ErrorCode::NumericalFailure;
    if (!normalize_scale(matrix)) return ErrorCode::DegenerateHomography;
    Matrix3 inverse = {};
    return invert(matrix, inverse) ? ErrorCode::Success : ErrorCode::DegenerateHomography;
}


} }
#endif
