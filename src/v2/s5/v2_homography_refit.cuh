// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: src/v1/s5/v1_homography_dlt.cuh by Le Thuong De (23120232)
// Changes: Block-parallel All-Inlier Refit solver with parallel Jacobi SVD and MSAC evaluation for V2.

#ifndef GROUP16_V2_HOMOGRAPHY_REFIT_CUH
#define GROUP16_V2_HOMOGRAPHY_REFIT_CUH

#include "v2/s5/v2_homography_workspace.cuh"

namespace panorama { namespace homography_v2 {

// Block-parallel tree reduction for arbitrary count <= leaves
__device__ inline void block_tree_reduce(double* buffer, std::size_t leaves) {
    for (std::size_t stride = 1; stride < leaves; stride *= 2) {
        for (std::size_t i = threadIdx.x * 2 * stride; i < leaves; i += blockDim.x * 2 * stride) {
            buffer[i] += buffer[i + stride];
        }
        __syncthreads();
    }
}

__device__ inline void block_tree_reduce_int(int* buffer, std::size_t leaves) {
    for (std::size_t stride = 1; stride < leaves; stride *= 2) {
        for (std::size_t i = threadIdx.x * 2 * stride; i < leaves; i += blockDim.x * 2 * stride) {
            buffer[i] += buffer[i + stride];
        }
        __syncthreads();
    }
}

// Parallel MSAC evaluation across the 256 threads of the block
__device__ inline ModelScore block_evaluate_msac(const Matrix3& matrix, const Correspondence* points,
                                                 int count, double threshold, double epsilon,
                                                 std::uint8_t* mask, Scratch& s) {
    const double threshold_squared = threshold * threshold;
    if (!isfinite(threshold) || threshold <= 0.0 || !isfinite(threshold_squared) ||
        !isfinite(epsilon) || epsilon <= 0.0 || count <= 0)
        return make_model_score(CUDART_INF, 0);

    const std::size_t leaves_count = leaf_count(static_cast<std::size_t>(count));
    for (std::size_t i = threadIdx.x; i < leaves_count; i += blockDim.x) {
        int keep = 0;
        double loss = 0.0;
        if (i < static_cast<std::size_t>(count)) {
            Point2 projected;
            if (project(matrix, points[i].b, epsilon, projected)) {
                const double dx = projected.x - points[i].a.x;
                const double dy = projected.y - points[i].a.y;
                const double error_squared = dx * dx + dy * dy;
                if (isfinite(error_squared)) {
                    if (error_squared < threshold_squared) keep = 1;
                    loss = min_value(error_squared, threshold_squared);
                } else {
                    loss = threshold_squared;
                }
            } else {
                loss = threshold_squared;
            }
            mask[i] = static_cast<std::uint8_t>(keep);
        }
        s.losses[i] = loss;
        s.inliers[i] = keep;
    }
    __syncthreads();

    block_tree_reduce(s.losses, leaves_count);
    block_tree_reduce_int(s.inliers, leaves_count);

    return make_model_score(s.losses[0], s.inliers[0]);
}

// Parallel inlier compaction preserving strictly increasing order of index i
__device__ inline int block_select_inliers(const Correspondence* points, int count,
                                           const std::uint8_t* mask, Correspondence* selected,
                                           int* temp_scan) {
    // Phase 1: local prefix scan
    int total = 0;
    for (int base = 0; base < count; base += blockDim.x) {
        const int idx = base + threadIdx.x;
        const int is_in = (idx < count && mask[idx]) ? 1 : 0;
        temp_scan[threadIdx.x] = is_in;
        __syncthreads();

        // Inclusive scan across blockDim.x in temp_scan
        for (int offset = 1; offset < blockDim.x; offset *= 2) {
            int val = 0;
            if (threadIdx.x >= offset) val = temp_scan[threadIdx.x - offset];
            __syncthreads();
            temp_scan[threadIdx.x] += val;
            __syncthreads();
        }

        if (is_in) {
            const int out_idx = total + temp_scan[threadIdx.x] - 1;
            selected[out_idx] = points[idx];
        }
        total += temp_scan[blockDim.x - 1];
        __syncthreads();
    }
    return total;
}

// Parallel point normalization matching V0/V1 ordered_sum
__device__ inline bool block_normalize_points(const Correspondence* pairs, std::size_t n, bool left,
                                              Normalization& normalized, Scratch& s) {
    if (n == 0) return false;
    const std::size_t leaves_n = leaf_count(n);
    const auto source = [&](std::size_t i) -> const Point2& { return left ? pairs[i].a : pairs[i].b; };

    // Sum x
    for (std::size_t i = threadIdx.x; i < leaves_n; i += blockDim.x)
        s.losses[i] = (i < n) ? source(i).x : 0.0;
    __syncthreads();
    block_tree_reduce(s.losses, leaves_n);
    normalized.center.x = s.losses[0] / static_cast<double>(n);

    // Sum y
    for (std::size_t i = threadIdx.x; i < leaves_n; i += blockDim.x)
        s.losses[i] = (i < n) ? source(i).y : 0.0;
    __syncthreads();
    block_tree_reduce(s.losses, leaves_n);
    normalized.center.y = s.losses[0] / static_cast<double>(n);

    // Sum radius squared
    for (std::size_t i = threadIdx.x; i < leaves_n; i += blockDim.x) {
        if (i < n) {
            const double dx = source(i).x - normalized.center.x;
            const double dy = source(i).y - normalized.center.y;
            s.losses[i] = dx * dx + dy * dy;
        } else {
            s.losses[i] = 0.0;
        }
    }
    __syncthreads();
    block_tree_reduce(s.losses, leaves_n);
    const double radius_squared = s.losses[0] / static_cast<double>(n);

    if (!isfinite(radius_squared) || radius_squared <= 0.0) return false;
    normalized.scale = sqrt(2.0) / sqrt(radius_squared);
    if (!isfinite(normalized.scale) || normalized.scale == 0.0) return false;

    normalized.points.resize(n);
    for (std::size_t i = threadIdx.x; i < n; i += blockDim.x) {
        normalized.points[i] = make_point2((source(i).x - normalized.center.x) * normalized.scale,
                                           (source(i).y - normalized.center.y) * normalized.scale);
        if (!isfinite(normalized.points[i].x) || !isfinite(normalized.points[i].y))
            return false;
    }
    __syncthreads();
    return true;
}

// Block-parallel Jacobi SVD for refit (rows = 2 * n)
__device__ inline ErrorCode block_parallel_jacobi_svd(double* matrix, std::size_t rows,
                                                      Array<double, 9>& vector,
                                                      Array<double, 9>& singular_values,
                                                      Scratch& s) {
    vector.fill(0.0);
    singular_values.fill(0.0);
    if (rows < 8 || rows > SIZE_MAX / 9) return ErrorCode::InvalidArgument;

    // Check finite
    for (std::size_t i = threadIdx.x; i < rows * 9; i += blockDim.x)
        if (!isfinite(matrix[i])) return ErrorCode::NumericalFailure;
    __syncthreads();

    // Compute norm_squared
    const std::size_t total_elements = rows * 9;
    const std::size_t leaves_total = leaf_count(total_elements);
    for (std::size_t i = threadIdx.x; i < leaves_total; i += blockDim.x)
        s.losses[i] = (i < total_elements) ? matrix[i] * matrix[i] : 0.0;
    __syncthreads();
    block_tree_reduce(s.losses, leaves_total);
    const double norm_squared = s.losses[0];

    if (!isfinite(norm_squared)) return ErrorCode::NumericalFailure;
    if (norm_squared == 0.0) return ErrorCode::DegenerateHomography;
    const double null_floor = kOrthogonalityTolerance * kOrthogonalityTolerance * norm_squared;

    __shared__ double s_right[81];
    if (threadIdx.x < 81) s_right[threadIdx.x] = 0.0;
    __syncthreads();
    if (threadIdx.x < 9) s_right[9 * threadIdx.x + threadIdx.x] = 1.0;
    __syncthreads();

    __shared__ double s_cosine, s_sine;
    __shared__ bool s_changed, s_converged;
    if (threadIdx.x == 0) s_converged = false;
    __syncthreads();

    const std::size_t leaves_rows = leaf_count(rows);

    for (int sweep = 0; sweep < kMaxSweeps; ++sweep) {
        if (threadIdx.x == 0) s_changed = false;
        __syncthreads();

        for (int p = 0; p < 8; ++p) {
            for (int q = p + 1; q < 9; ++q) {
                // Compute alpha, beta, gamma in parallel across rows
                for (std::size_t row = threadIdx.x; row < leaves_rows; row += blockDim.x) {
                    if (row < rows) {
                        const double ap = matrix[9 * row + p];
                        const double aq = matrix[9 * row + q];
                        s.losses[row] = ap * ap;
                        s.losses[leaves_rows + row] = aq * aq;
                        s.losses[2 * leaves_rows + row] = ap * aq;
                    } else {
                        s.losses[row] = 0.0;
                        s.losses[leaves_rows + row] = 0.0;
                        s.losses[2 * leaves_rows + row] = 0.0;
                    }
                }
                __syncthreads();

                block_tree_reduce(s.losses, leaves_rows);
                block_tree_reduce(s.losses + leaves_rows, leaves_rows);
                block_tree_reduce(s.losses + 2 * leaves_rows, leaves_rows);

                const double alpha = s.losses[0];
                const double beta  = s.losses[leaves_rows];
                const double gamma = s.losses[2 * leaves_rows];

                if (!isfinite(alpha) || !isfinite(beta) || !isfinite(gamma))
                    return ErrorCode::NumericalFailure;

                if (threadIdx.x == 0) {
                    if (alpha <= null_floor || beta <= null_floor ||
                        fabs(gamma) <= kOrthogonalityTolerance * sqrt(alpha) * sqrt(beta)) {
                        s_cosine = 1.0;
                        s_sine = 0.0;
                    } else {
                        const double theta = (beta - alpha) / (2.0 * gamma);
                        const double tangent = copysign(1.0 / (fabs(theta) + hypot(1.0, theta)), theta);
                        const double cosine = 1.0 / hypot(1.0, tangent);
                        const double sine = cosine * tangent;
                        if (!isfinite(theta) || !isfinite(cosine) || !isfinite(sine)) {
                            s_cosine = CUDART_NAN;
                        } else {
                            s_cosine = cosine;
                            s_sine = sine;
                            s_changed = true;
                        }
                    }
                }
                __syncthreads();

                if (!isfinite(s_cosine)) return ErrorCode::NumericalFailure;

                if (s_cosine != 1.0 || s_sine != 0.0) {
                    for (std::size_t row = threadIdx.x; row < rows; row += blockDim.x) {
                        const double a = matrix[9 * row + p], b = matrix[9 * row + q];
                        matrix[9 * row + p] = s_cosine * a - s_sine * b;
                        matrix[9 * row + q] = s_sine * a + s_cosine * b;
                    }
                    if (threadIdx.x < 9) {
                        const int row = static_cast<int>(threadIdx.x);
                        const double a = s_right[9 * row + p], b = s_right[9 * row + q];
                        s_right[9 * row + p] = s_cosine * a - s_sine * b;
                        s_right[9 * row + q] = s_sine * a + s_cosine * b;
                    }
                    __syncthreads();
                }
            }
        }

        if (threadIdx.x == 0 && !s_changed) s_converged = true;
        __syncthreads();
        if (s_converged) break;
    }

    if (!s_converged) return ErrorCode::NumericalFailure;

    // Compute column norms
    Array<double, 9> norms = {};
    for (int col = 0; col < 9; ++col) {
        for (std::size_t row = threadIdx.x; row < leaves_rows; row += blockDim.x)
            s.losses[row] = (row < rows) ? matrix[9 * row + col] * matrix[9 * row + col] : 0.0;
        __syncthreads();
        block_tree_reduce(s.losses, leaves_rows);
        if (threadIdx.x == 0) norms[col] = sqrt(s.losses[0]);
        __syncthreads();
    }

    if (threadIdx.x == 0) {
        Array<int, 9> order = {{0, 1, 2, 3, 4, 5, 6, 7, 8}};
        for (int i = 0; i < 8; ++i) {
            for (int j = i + 1; j < 9; ++j) {
                if (norms[order[j]] > norms[order[i]] ||
                    (norms[order[j]] == norms[order[i]] && order[j] < order[i])) {
                    swap_value(order[i], order[j]);
                }
            }
        }
        for (int i = 0; i < 9; ++i) {
            singular_values[i] = norms[order[i]];
            vector[i] = s_right[9 * i + order[8]];
        }
    }
    __syncthreads();

    return ErrorCode::Success;
}

// Block-parallel normalized DLT for refit
__device__ inline ErrorCode block_parallel_normalized_dlt(const Correspondence* points, std::size_t n,
                                                          double denominator_epsilon, Matrix3& output,
                                                          Scratch& s) {
    if (threadIdx.x == 0) output.fill(0.0);
    __syncthreads();

    if (n < 4) return ErrorCode::InsufficientMatches;
    if (!isfinite(denominator_epsilon) || denominator_epsilon <= 0.0)
        return ErrorCode::InvalidConfig;

    Normalization a, b;
    a.points = Buffer<Point2>(s.normalized_a, n);
    b.points = Buffer<Point2>(s.normalized_b, n);

    if (!block_normalize_points(points, n, true, a, s) ||
        !block_normalize_points(points, n, false, b, s))
        return ErrorCode::DegenerateHomography;

    const std::size_t rows = max_value<std::size_t>(9, 2 * n);
    for (std::size_t i = threadIdx.x; i < rows * 9; i += blockDim.x)
        s.design[i] = 0.0;
    __syncthreads();

    for (std::size_t i = threadIdx.x; i < n; i += blockDim.x) {
        const double x = b.points[i].x, y = b.points[i].y, u = a.points[i].x, v = a.points[i].y;
        const std::size_t r = 18 * i;
        s.design[r]      = x;  s.design[r + 1]  = y;  s.design[r + 2]  = 1.0;
        s.design[r + 6]  = -u * x; s.design[r + 7]  = -u * y; s.design[r + 8]  = -u;
        s.design[r + 12] = x;  s.design[r + 13] = y;  s.design[r + 14] = 1.0;
        s.design[r + 15] = -v * x; s.design[r + 16] = -v * y; s.design[r + 17] = -v;
    }
    __syncthreads();

    Matrix3 vector = {}, singular = {};
    const ErrorCode svd_status = block_parallel_jacobi_svd(s.design, rows, vector, singular, s);
    if (svd_status != ErrorCode::Success) return svd_status;

    __shared__ ErrorCode s_dlt_status;
    if (threadIdx.x == 0) {
        if (!isfinite(singular[0]) || singular[0] <= 0.0 ||
            singular[7] <= feature_policy::kRankEpsilon * singular[0]) {
            s_dlt_status = ErrorCode::DegenerateHomography;
        } else {
            const Matrix3 ta_inverse = {{1.0 / a.scale, 0.0, a.center.x,
                                         0.0, 1.0 / a.scale, a.center.y, 0.0, 0.0, 1.0}};
            const Matrix3 tb = {{b.scale, 0.0, -b.scale * b.center.x,
                                 0.0, b.scale, -b.scale * b.center.y, 0.0, 0.0, 1.0}};
            output = multiply(multiply(ta_inverse, vector), tb);
            s_dlt_status = validate_matrix(output);
        }
    }
    __syncthreads();
    return s_dlt_status;
}

} }  // namespace panorama::homography_v2

#endif  // GROUP16_V2_HOMOGRAPHY_REFIT_CUH
