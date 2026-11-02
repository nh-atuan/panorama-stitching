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

#ifndef GROUP16_V1_HOMOGRAPHY_SCORING_CUH
#define GROUP16_V1_HOMOGRAPHY_SCORING_CUH
#include "v1/s5/v1_homography_geometry.cuh"
namespace panorama { namespace homography_gpu {
// MSAC scoring.
__device__ inline ModelScore evaluate_msac(const Matrix3& matrix, const Buffer<Correspondence>& points,
                         double threshold, double epsilon, Buffer<std::uint8_t>& mask) {
    mask.clear();
    const double threshold_squared=threshold*threshold;
    if(!isfinite(threshold) || threshold<=0.0 || !isfinite(threshold_squared) ||
       !isfinite(epsilon) || epsilon<=0.0 ||
       points.size()>static_cast<std::size_t>(INT32_MAX))
        return ModelScore(CUDART_INF,0);
    mask.resize(points.size(),0);
    std::int32_t count=0;
    const double loss=ordered_sum(points.size(),[&](std::size_t i) {
        Point2 projected;
        if(!project(matrix,points[i].b,epsilon,projected)) return threshold_squared;
        const double dx=projected.x-points[i].a.x;
        const double dy=projected.y-points[i].a.y;
        const double error_squared=dx*dx+dy*dy;
        if(!isfinite(error_squared)) return threshold_squared;
        if(error_squared<threshold_squared) {mask[i]=1;++count;}
        return min_value(error_squared,threshold_squared);
    });
    return ModelScore(loss,count);
}

__device__ inline bool better_model(const ModelScore& candidate,std::int32_t candidate_id,
                   const ModelScore& best,std::int32_t best_id) {
    if(!isfinite(candidate.loss) || candidate.inliers<4 || candidate_id<0) return false;
    if(best_id<0) return true;
    if(candidate.loss!=best.loss) return candidate.loss<best.loss;
    if(candidate.inliers!=best.inliers) return candidate.inliers>best.inliers;
    return candidate_id<best_id;
}



} }
#endif
