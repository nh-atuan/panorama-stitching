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

#ifndef GROUP16_V1_HOMOGRAPHY_DLT_CUH
#define GROUP16_V1_HOMOGRAPHY_DLT_CUH
#include "v1/s5/v1_homography_geometry.cuh"
namespace panorama { namespace homography_gpu {
// Direct Jacobi SVD.
namespace {
constexpr int kMaxSweeps = 128;
constexpr double kOrthogonalityTolerance = 16.0 * std::numeric_limits<double>::epsilon();
__device__ inline double column_dot(const Buffer<double>& matrix, std::size_t rows, int p, int q) {
    return ordered_sum(rows, [&](std::size_t row) {
        return matrix[9*row+p] * matrix[9*row+q];
    });
}
}  // namespace

__device__ inline ErrorCode smallest_right_vector(Buffer<double>& matrix, std::size_t rows,
                                Array<double, 9>& vector,
                                Array<double, 9>& singular_values) {
    vector.fill(0.0);
    singular_values.fill(0.0);
    if (rows < 8 || rows > SIZE_MAX/9 ||
        matrix.size() != rows*9) return ErrorCode::InvalidArgument;
    for (double value : matrix)
        if (!isfinite(value)) return ErrorCode::NumericalFailure;
    const double norm_squared = ordered_sum(matrix.size(), [&](std::size_t i) {
        return matrix[i]*matrix[i];
    });
    if (!isfinite(norm_squared)) return ErrorCode::NumericalFailure;
    if (norm_squared == 0.0) return ErrorCode::DegenerateHomography;
    const double null_floor = kOrthogonalityTolerance*kOrthogonalityTolerance*norm_squared;
    Array<double, 81> right = {};
    for (int i = 0; i < 9; ++i) right[9*i+i] = 1.0;
    bool converged = false;
    for (int sweep = 0; sweep < kMaxSweeps; ++sweep) {
        bool changed = false;
        for (int p = 0; p < 8; ++p) {
            for (int q = p+1; q < 9; ++q) {
                const double alpha = column_dot(matrix,rows,p,p);
                const double beta = column_dot(matrix,rows,q,q);
                const double gamma = column_dot(matrix,rows,p,q);
                if (!isfinite(alpha) || !isfinite(beta) || !isfinite(gamma))
                    return ErrorCode::NumericalFailure;
                if (alpha <= null_floor || beta <= null_floor ||
                    fabs(gamma) <= kOrthogonalityTolerance*sqrt(alpha)*sqrt(beta))
                    continue;
                const double theta = (beta-alpha)/(2.0*gamma);
                const double tangent = copysign(
                    1.0/(fabs(theta) + hypot(1.0,theta)),theta);
                const double cosine = 1.0/hypot(1.0,tangent);
                const double sine = cosine*tangent;
                if (!isfinite(theta) || !isfinite(cosine) || !isfinite(sine))
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
    Array<double, 9> norms = {};
    Array<int, 9> order = {{0,1,2,3,4,5,6,7,8}};
    for (int column = 0; column < 9; ++column)
        norms[column] = sqrt(column_dot(matrix,rows,column,column));
    for (int i=0;i<8;++i) for (int j=i+1;j<9;++j)
        if (norms[order[j]] > norms[order[i]] ||
            (norms[order[j]] == norms[order[i]] && order[j] < order[i]))
            swap_value(order[i],order[j]);
    for (int i = 0; i < 9; ++i) {
        singular_values[i] = norms[order[i]];
        vector[i] = right[9*i+order[8]];
    }
    return ErrorCode::Success;
}

// Normalized DLT.
namespace {
struct Normalization {
    Point2 center;
    double scale;
    Buffer<Point2> points;
};

__device__ inline bool normalize_points(const Buffer<Correspondence>& pairs, bool left,
                       Normalization& normalized) {
    const std::size_t n = pairs.size();
    const auto source = [&](std::size_t i) -> const Point2& { return left ? pairs[i].a : pairs[i].b; };
    normalized.center.x = ordered_sum(n,[&](std::size_t i) { return source(i).x; })/n;
    normalized.center.y = ordered_sum(n,[&](std::size_t i) { return source(i).y; })/n;
    const double radius_squared = ordered_sum(n,[&](std::size_t i) {
        const double dx = source(i).x-normalized.center.x;
        const double dy = source(i).y-normalized.center.y;
        return dx*dx + dy*dy;
    })/n;
    if (!isfinite(radius_squared) || radius_squared <= 0.0) return false;
    normalized.scale = sqrt(2.0)/sqrt(radius_squared);
    if (!isfinite(normalized.scale) || normalized.scale == 0.0) return false;
    normalized.points.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        normalized.points[i] = Point2((source(i).x-normalized.center.x)*normalized.scale,
                                     (source(i).y-normalized.center.y)*normalized.scale);
        if (!isfinite(normalized.points[i].x) || !isfinite(normalized.points[i].y))
            return false;
    }
    return true;
}

__device__ inline bool minimal_geometry_valid(const Buffer<Point2>& points) {
    for (int i = 0; i < 4; ++i)
        for (int j = i+1; j < 4; ++j) {
            const double dx = points[j].x-points[i].x;
            const double dy = points[j].y-points[i].y;
            if (hypot(dx,dy) <= feature_policy::kDuplicateEpsilon) return false;
            for (int k = j+1; k < 4; ++k) {
                const double area = dx*(points[k].y-points[i].y) - dy*(points[k].x-points[i].x);
                if (fabs(area) <= feature_policy::kAreaEpsilon) return false;
            }
        }
    return true;
}
}  // namespace

__device__ inline ErrorCode normalized_dlt(const Buffer<Correspondence>& points, bool minimal,
                         double denominator_epsilon, Matrix3& output,
                         double* design_storage, Point2* normalized_a, Point2* normalized_b) {
    output.fill(0.0);
    if (points.size() < 4) return ErrorCode::InsufficientMatches;
    if (minimal && points.size() != 4) return ErrorCode::InvalidArgument;
    if (!isfinite(denominator_epsilon) || denominator_epsilon <= 0.0)
        return ErrorCode::InvalidConfig;
    for (const Correspondence& pair : points)
        if (!isfinite(pair.a.x) || !isfinite(pair.a.y) ||
            !isfinite(pair.b.x) || !isfinite(pair.b.y))
            return ErrorCode::NumericalFailure;
    Normalization a, b;
    a.points = Buffer<Point2>(normalized_a, points.size());
    b.points = Buffer<Point2>(normalized_b, points.size());
    if (!normalize_points(points,true,a) || !normalize_points(points,false,b))
        return ErrorCode::DegenerateHomography;
    if (minimal && (!minimal_geometry_valid(a.points) || !minimal_geometry_valid(b.points)))
        return ErrorCode::DegenerateHomography;
    if (points.size() > SIZE_MAX/18)
        return ErrorCode::AllocationFailed;
    const std::size_t rows = max_value<std::size_t>(9,2*points.size());
    Buffer<double> design(design_storage, rows*9);
    for (std::size_t i=0;i<rows*9;++i) design[i]=0.0;
    for (std::size_t i = 0; i < points.size(); ++i) {
        const double x=b.points[i].x, y=b.points[i].y, u=a.points[i].x, v=a.points[i].y;
        const std::size_t r = 18*i;
        design[r]=x; design[r+1]=y; design[r+2]=1.0;
        design[r+6]=-u*x; design[r+7]=-u*y; design[r+8]=-u;
        design[r+12]=x; design[r+13]=y; design[r+14]=1.0;
        design[r+15]=-v*x; design[r+16]=-v*y; design[r+17]=-v;
    }
    Matrix3 vector = {}, singular = {};
    const ErrorCode svd_status = smallest_right_vector(design,rows,vector,singular);
    if (svd_status != ErrorCode::Success) return svd_status;
    if (!isfinite(singular[0]) || singular[0] <= 0.0 ||
        singular[7] <= feature_policy::kRankEpsilon*singular[0])
        return ErrorCode::DegenerateHomography;
    const Matrix3 ta_inverse = {{1.0/a.scale,0.0,a.center.x,
                                0.0,1.0/a.scale,a.center.y,0.0,0.0,1.0}};
    const Matrix3 tb = {{b.scale,0.0,-b.scale*b.center.x,
                        0.0,b.scale,-b.scale*b.center.y,0.0,0.0,1.0}};
    Matrix3 candidate = multiply(multiply(ta_inverse,vector),tb);
    const ErrorCode matrix_status = validate_matrix(candidate);
    if (matrix_status != ErrorCode::Success) return matrix_status;
    // A refit may include points that become outliers; only minimal sample projections
    // must all be valid here. The scorer evaluates every refit correspondence later.
    if (minimal) {
        for (const Correspondence& pair : points) {
            Point2 projected;
            if (!project(candidate,pair.b,denominator_epsilon,projected))
                return ErrorCode::NumericalFailure;
        }
    }
    output = candidate;
    return ErrorCode::Success;
}


} }
#endif
