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

#ifndef GROUP16_V1_HOMOGRAPHY_SAMPLING_CUH
#define GROUP16_V1_HOMOGRAPHY_SAMPLING_CUH
#include "v1/s5/v1_homography_geometry.cuh"
namespace panorama { namespace homography_gpu {
// Uniform sampling and adaptive termination.
namespace {
__device__ inline std::uint64_t mix64(std::uint64_t value) {
    value = (value ^ (value >> 30))*UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27))*UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

struct SampleStream {
    std::uint64_t state;
    __device__ std::uint64_t next() {
        state += UINT64_C(0x9e3779b97f4a7c15);
        return mix64(state);
    }
    __device__ std::uint64_t bounded(std::uint64_t count) {
        const std::uint64_t floor = (std::uint64_t(0)-count)%count;
        std::uint64_t value;
        do { value=next(); } while(value<floor);
        return value%count;
    }
};
}  // namespace

__device__ inline bool uniform_sample4(std::uint32_t seed, std::int32_t hypothesis_id,
                      std::int32_t count, Array<std::int32_t,4>& sample) {
    sample.fill(-1);
    if (hypothesis_id<0 || count<4) return false;
    SampleStream stream={mix64(static_cast<std::uint64_t>(seed) ^
                              static_cast<std::uint64_t>(hypothesis_id))};
    for(int slot=0;slot<4;++slot) {
        bool repeated;
        do {
            sample[slot]=static_cast<std::int32_t>(stream.bounded(static_cast<std::uint64_t>(count)));
            repeated=false;
            for(int previous=0;previous<slot;++previous)
                if(sample[previous]==sample[slot]) repeated=true;
        } while(repeated);
    }
    return true;
}

__device__ inline std::int32_t adaptive_iteration_budget(std::int32_t inliers, std::int32_t count,
                                       std::int32_t cap) {
    if(cap<=0) return 0;
    if(count<=0 || inliers<=0 || inliers>count) return cap;
    if(inliers==count) return 1;
    const double ratio=static_cast<double>(inliers)/static_cast<double>(count);
    const double squared=ratio*ratio;
    const double all_inliers=squared*squared;
    const double denominator=log1p(-all_inliers);
    if(!isfinite(denominator) || denominator>=0.0) return cap;
    const double needed=ceil(log1p(-feature_policy::kConfidence)/denominator);
    if(!isfinite(needed) || needed>=static_cast<double>(cap)) return cap;
    return static_cast<std::int32_t>(max_value(1.0,needed));
}


} }
#endif
