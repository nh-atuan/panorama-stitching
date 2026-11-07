// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: src/v1/s5/v1_homography.cu by Le Thuong De (23120232)
// Changes: V2 parallel all-inlier refit, parallel Jacobi SVD and optimized shared-memory hypothesis scoring.

#include "v2/s5/v2_homography_workspace.cuh"
#include "v2/s5/v2_homography_refit.cuh"
#include "v1/common/v1_nvtx.cuh"
#include <cmath>
#include <limits>

namespace panorama {
namespace {
using namespace homography_v2;

__device__ double residual(const Matrix3& h, const Correspondence& p, double tau2, double epsilon, int& inlier) {
    Point2 q;
    inlier = 0;
    if (!project(h, p.b, epsilon, q)) return tau2;
    const double dx = q.x - p.a.x, dy = q.y - p.a.y;
    const double e = dx * dx + dy * dy;
    if (!isfinite(e)) return tau2;
    inlier = e < tau2;
    return min_value(e, tau2);
}

__global__ void prepare_homography(DeviceWorkspace w, Scratch s, Config config) {
    if (threadIdx.x == 0) {
        *s.state = State();
        *w.d_homography = Homography();
    }
    __syncthreads();

    if (w.d_counts->status != ErrorCode::Success) {
        if (threadIdx.x == 0) s.state->done = 1;
        return;
    }

    const DeviceCounts c = *w.d_counts;
    __shared__ ErrorCode s_status;
    if (threadIdx.x == 0) s_status = ErrorCode::Success;
    __syncthreads();

    if (c.keypointsA > w.keypoint_capacityA || c.keypointsB > w.keypoint_capacityB ||
        c.matches > w.match_capacity) {
        if (threadIdx.x == 0) s_status = ErrorCode::InvalidArgument;
    }
    __syncthreads();

    if (s_status == ErrorCode::Success) {
        for (unsigned i = threadIdx.x; i < c.keypointsA; i += blockDim.x) {
            if (!isfinite(w.d_keypointsA[i].x) || !isfinite(w.d_keypointsA[i].y))
                s_status = ErrorCode::NumericalFailure;
        }
        for (unsigned i = threadIdx.x; i < c.keypointsB; i += blockDim.x) {
            if (!isfinite(w.d_keypointsB[i].x) || !isfinite(w.d_keypointsB[i].y))
                s_status = ErrorCode::NumericalFailure;
        }
    }
    __syncthreads();

    if (s_status == ErrorCode::Success) {
        for (unsigned i = threadIdx.x; i < c.matches; i += blockDim.x) {
            const Match m = w.d_matches[i];
            if (m.indexA >= static_cast<int>(c.keypointsA) ||
                m.indexB < 0 || m.indexB >= static_cast<int>(c.keypointsB) || m.distance > 256u) {
                s_status = ErrorCode::InvalidArgument;
            }
            if (i > 0) {
                const Match prev = w.d_matches[i - 1];
                if (m.indexA <= prev.indexA) s_status = ErrorCode::InvalidArgument;
            }
        }
        __syncthreads();
        if (s_status == ErrorCode::Success && c.matches < 4) s_status = ErrorCode::InsufficientMatches;
    }
    __syncthreads();

    if (threadIdx.x == 0) {
        s.state->count = static_cast<int>(c.matches);
        if (s_status != ErrorCode::Success) {
            w.d_counts->status = s_status;
            s.state->done = 1;
        } else {
            s.state->report.adaptive_budget = config.ransac_iters;
        }
    }
}

__global__ void gather_points(DeviceWorkspace w, Scratch s) {
    const unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
    if (w.d_counts->status != ErrorCode::Success || i >= static_cast<unsigned>(s.state->count)) return;
    const Match m = w.d_matches[i];
    const Keypoint a = w.d_keypointsA[m.indexA], b = w.d_keypointsB[m.indexB];
    s.points[i].a = make_point2(a.x, a.y);
    s.points[i].b = make_point2(b.x, b.y);
}

__global__ void compute_hypotheses(DeviceWorkspace w, Scratch s, Config config, int first) {
    if (w.d_counts->status != ErrorCode::Success || s.state->done) return;
    Hypothesis& result = s.hypotheses[blockIdx.x];

    __shared__ Correspondence s_sample[4];
    __shared__ Point2 s_a[4], s_b[4];
    __shared__ double s_design[81];

    if (threadIdx.x == 0) {
        Array<std::int32_t, 4> indices;
        uniform_sample4(config.seed, first + static_cast<int>(blockIdx.x), s.state->count, indices);
        for (int i = 0; i < 4; ++i) {
            result.sample[i] = indices[i];
            s_sample[i] = s.points[indices[i]];
        }
        result.status = normalized_dlt(Buffer<Correspondence>(s_sample, 4), true, config.homography_epsilon,
                                       result.matrix, s_design, s_a, s_b);
    }
    __syncthreads();

    double* losses = s.losses + blockIdx.x * s.leaves;
    int* inliers = s.inliers + blockIdx.x * s.leaves;
    for (std::size_t i = threadIdx.x; i < s.leaves; i += blockDim.x) {
        int keep = 0;
        double loss = 0.0;
        if (i < static_cast<std::size_t>(s.state->count) && result.status == ErrorCode::Success)
            loss = residual(result.matrix, s.points[i],
                            static_cast<double>(config.ransac_threshold) * config.ransac_threshold,
                            config.homography_epsilon, keep);
        losses[i] = loss;
        inliers[i] = keep;
    }
    __syncthreads();

    for (std::size_t stride = 1; stride < s.leaves; stride *= 2) {
        for (std::size_t i = threadIdx.x * 2 * stride; i < s.leaves; i += blockDim.x * 2 * stride) {
            losses[i] += losses[i + stride];
            inliers[i] += inliers[i + stride];
        }
        __syncthreads();
    }
    if (threadIdx.x == 0) {
        result.loss = losses[0];
        result.inliers = inliers[0];
    }
}

__global__ void commit_prefix(DeviceWorkspace w, Scratch s, Config config, int first, int computed) {
    if (w.d_counts->status != ErrorCode::Success || s.state->done) return;
    V2HomographyDiagnostics& r = s.state->report;
    r.computed_hypotheses += computed;
    for (int i = 0; i < computed; ++i) {
        const Hypothesis& h = s.hypotheses[i];
        ++r.attempts;
        for (int k = 0; k < 4; ++k)
            r.sample_hash = (r.sample_hash ^ static_cast<std::uint64_t>(h.sample[k])) * UINT64_C(1099511628211);
        if (h.status == ErrorCode::Success) {
            ++r.valid_hypotheses;
            if (better_model(make_model_score(h.loss, h.inliers), first + i,
                             make_model_score(r.best_loss, r.best_inliers), r.best_hypothesis)) {
                r.best_hypothesis = first + i;
                r.best_loss = h.loss;
                r.best_inliers = h.inliers;
                s.state->best = h.matrix;
                r.adaptive_budget = adaptive_iteration_budget(h.inliers, s.state->count, config.ransac_iters);
            }
        } else {
            ++r.rejected_samples;
        }
        if (r.attempts >= r.adaptive_budget) {
            s.state->done = 1;
            break;
        }
    }
}

__global__ void refit_homography(DeviceWorkspace w, Scratch s, Config config) {
    if (w.d_counts->status != ErrorCode::Success) return;
    V2HomographyDiagnostics& r = s.state->report;
    if (r.best_hypothesis < 0) {
        if (threadIdx.x == 0) w.d_counts->status = ErrorCode::DegenerateHomography;
        return;
    }

    __shared__ int temp_scan[256];
    __shared__ Matrix3 s_refined;
    __shared__ ModelScore s_score;
    __shared__ int s_inlier_count;
    __shared__ bool s_changed;

    // Pass 1: MSAC evaluation with best hypothesis
    s_score = block_evaluate_msac(s.state->best, s.points, s.state->count,
                                  config.ransac_threshold, config.homography_epsilon,
                                  s.best_mask, s);
    __syncthreads();

    // Select inliers
    s_inlier_count = block_select_inliers(s.points, s.state->count, s.best_mask,
                                          s.selected, temp_scan);
    __syncthreads();

    // First refit
    ErrorCode status = block_parallel_normalized_dlt(s.selected, s_inlier_count,
                                                     config.homography_epsilon,
                                                     s_refined, s);
    if (status != ErrorCode::Success) {
        if (threadIdx.x == 0) w.d_counts->status = status;
        return;
    }
    if (threadIdx.x == 0) r.refit_passes = 1;
    __syncthreads();

    // Re-evaluate with refined model
    s_score = block_evaluate_msac(s_refined, s.points, s.state->count,
                                  config.ransac_threshold, config.homography_epsilon,
                                  s.mask, s);
    __syncthreads();

    if (threadIdx.x == 0) {
        r.first_refit_loss = s_score.loss;
        r.first_refit_inliers = s_score.inliers;
        r.refit_loss = s_score.loss;
    }
    if (s_score.inliers < 4) {
        if (threadIdx.x == 0) w.d_counts->status = ErrorCode::InsufficientMatches;
        return;
    }

    if (threadIdx.x == 0) s_changed = false;
    __syncthreads();

    for (int i = threadIdx.x; i < s.state->count; i += blockDim.x) {
        if (s.mask[i] != s.best_mask[i]) s_changed = true;
    }
    __syncthreads();

    // Pass 2: Refit if inlier mask changed
    if (s_changed) {
        s_inlier_count = block_select_inliers(s.points, s.state->count, s.mask,
                                              s.selected, temp_scan);
        __syncthreads();

        status = block_parallel_normalized_dlt(s.selected, s_inlier_count,
                                              config.homography_epsilon,
                                              s_refined, s);
        if (status != ErrorCode::Success) {
            if (threadIdx.x == 0) w.d_counts->status = status;
            return;
        }
        if (threadIdx.x == 0) r.refit_passes = 2;
        __syncthreads();

        s_score = block_evaluate_msac(s_refined, s.points, s.state->count,
                                      config.ransac_threshold, config.homography_epsilon,
                                      s.mask, s);
        __syncthreads();
        if (threadIdx.x == 0) r.refit_loss = s_score.loss;
    }

    // Publication check
    __shared__ Matrix3 s_stored;
    if (threadIdx.x == 0) {
        Homography candidate;
        for (int i = 0; i < 9; ++i) {
            candidate.data[i] = static_cast<float>(s_refined[i]);
            s_stored[i] = candidate.data[i];
        }
        status = validate_matrix(s_stored);
        if (status != ErrorCode::Success) {
            w.d_counts->status = status;
        }
    }
    __syncthreads();
    if (w.d_counts->status != ErrorCode::Success) return;

    s_score = block_evaluate_msac(s_stored, s.points, s.state->count,
                                  config.ransac_threshold, config.homography_epsilon,
                                  s.mask, s);
    __syncthreads();

    if (!isfinite(s_score.loss)) {
        if (threadIdx.x == 0) w.d_counts->status = ErrorCode::NumericalFailure;
        return;
    }
    if (s_score.inliers < 4) {
        if (threadIdx.x == 0) w.d_counts->status = ErrorCode::InsufficientMatches;
        return;
    }

    if (threadIdx.x == 0) {
        r.final_loss = s_score.loss;
        r.final_inliers = s_score.inliers;
        Homography candidate;
        for (int i = 0; i < 9; ++i) candidate.data[i] = static_cast<float>(s_stored[i]);
        *w.d_homography = candidate;
    }
}
}  // namespace

std::size_t v2_homography_scratch_bytes(std::size_t cap, int batch) {
    if (batch < 1 || batch > 256 || cap > static_cast<std::size_t>(INT32_MAX) || cap > SIZE_MAX / 65536u)
        return 0;
    std::size_t bytes = 0;
    homography_v2::layout(nullptr, cap, batch, bytes);
    return bytes;
}

const V2HomographyDiagnostics* v2_homography_diagnostics(const DeviceWorkspace& w) {
    return reinterpret_cast<const V2HomographyDiagnostics*>(w.d_scratch);
}

const std::uint8_t* v2_homography_inlier_mask(const DeviceWorkspace& w, int batch) {
    if (!v2_homography_scratch_bytes(w.match_capacity, batch)) return nullptr;
    std::size_t bytes = 0;
    return homography_v2::layout(w.d_scratch, w.match_capacity, batch, bytes).mask;
}

ErrorCode v2_homography_with_batch_size(DeviceWorkspace& w, const Config& c, cudaStream_t stream, int batch) {
    V1NvtxRange stage("S5_V2.homography");
    std::size_t stack_bytes = 0;
    if (cudaDeviceGetLimit(&stack_bytes, cudaLimitStackSize) == cudaSuccess && stack_bytes < 32768) {
        cudaDeviceSetLimit(cudaLimitStackSize, 32768);
    }
    if (c.ransac_iters <= 0 || c.ransac_iters > feature_policy::kMaxIterations ||
        !std::isfinite(c.ransac_threshold) || c.ransac_threshold <= 0 ||
        !std::isfinite(c.homography_epsilon) || c.homography_epsilon <= 0)
        return ErrorCode::InvalidConfig;
    if (batch < 1 || batch > 256 || !w.d_counts || !w.d_homography || !w.d_matches ||
        !w.d_keypointsA || !w.d_keypointsB || w.keypoint_capacityA > static_cast<std::size_t>(INT32_MAX) ||
        w.keypoint_capacityB > static_cast<std::size_t>(INT32_MAX))
        return ErrorCode::InvalidArgument;

    const std::size_t required = v2_homography_scratch_bytes(w.match_capacity, batch);
    if (!required || !w.d_scratch || w.scratch_capacity_bytes < required ||
        reinterpret_cast<std::uintptr_t>(w.d_scratch) % 16u)
        return ErrorCode::AllocationFailed;

    std::size_t bytes = 0;
    const homography_v2::Scratch s = homography_v2::layout(w.d_scratch, w.match_capacity, batch, bytes);

    prepare_homography<<<1, 256, 0, stream>>>(w, s, c);
    if (w.match_capacity)
        gather_points<<<static_cast<unsigned>((w.match_capacity + 127) / 128), 128, 0, stream>>>(w, s);

    for (int first = 0; first < c.ransac_iters; first += batch) {
        const int computed = std::min(batch, c.ransac_iters - first);
        {
            V1NvtxRange range("S5_V2.fit_score");
            compute_hypotheses<<<computed, 128, 0, stream>>>(w, s, c, first);
        }
        {
            V1NvtxRange range("S5_V2.commit_prefix");
            commit_prefix<<<1, 1, 0, stream>>>(w, s, c, first, computed);
        }
    }

    {
        V1NvtxRange range("S5_V2.refit");
        refit_homography<<<1, 256, 0, stream>>>(w, s, c);
    }

    return cudaGetLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

ErrorCode v2_homography(DeviceWorkspace& w, const Config& c, cudaStream_t stream) {
    return v2_homography_with_batch_size(w, c, stream, 32);
}

}  // namespace panorama
