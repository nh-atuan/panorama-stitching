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

#include "v0/v0_homography.h"
#include "v0/v0_homography_internal.h"
#include "common/feature_support.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <new>
#include <ostream>
#include <stdexcept>

namespace panorama {
namespace homography_detail {

// Ordered reduction.
// Fixed binary tree with leaves in input order and zero padding.
template <typename Getter>
double sum_subtree(const Getter& get, std::size_t count,
                   std::size_t first, std::size_t width) {
    if (first >= count) return 0.0;
    if (width == 1) return get(first);
    const std::size_t half = width / 2;
    const double left = sum_subtree(get, count, first, half);
    const double right = sum_subtree(get, count, first + half, half);
    return left + right;
}

template <typename Getter>
double ordered_sum(std::size_t count, const Getter& get) {
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

// Direct Jacobi SVD.
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

// Normalized DLT.
namespace {
struct Normalization {
    Point2 center;
    double scale;
    std::vector<Point2> points;
};

bool normalize_points(const std::vector<Correspondence>& pairs, bool left,
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
    if (!std::isfinite(radius_squared) || radius_squared <= 0.0) return false;
    normalized.scale = std::sqrt(2.0)/std::sqrt(radius_squared);
    if (!std::isfinite(normalized.scale) || normalized.scale == 0.0) return false;
    normalized.points.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        normalized.points[i] = Point2((source(i).x-normalized.center.x)*normalized.scale,
                                     (source(i).y-normalized.center.y)*normalized.scale);
        if (!std::isfinite(normalized.points[i].x) || !std::isfinite(normalized.points[i].y))
            return false;
    }
    return true;
}

bool minimal_geometry_valid(const std::vector<Point2>& points) {
    for (int i = 0; i < 4; ++i)
        for (int j = i+1; j < 4; ++j) {
            const double dx = points[j].x-points[i].x;
            const double dy = points[j].y-points[i].y;
            if (std::hypot(dx,dy) <= feature_policy::kDuplicateEpsilon) return false;
            for (int k = j+1; k < 4; ++k) {
                const double area = dx*(points[k].y-points[i].y) - dy*(points[k].x-points[i].x);
                if (std::abs(area) <= feature_policy::kAreaEpsilon) return false;
            }
        }
    return true;
}
}  // namespace

ErrorCode normalized_dlt(const std::vector<Correspondence>& points, bool minimal,
                         double denominator_epsilon, Matrix3& output) {
    output.fill(0.0);
    if (points.size() < 4) return ErrorCode::InsufficientMatches;
    if (minimal && points.size() != 4) return ErrorCode::InvalidArgument;
    if (!std::isfinite(denominator_epsilon) || denominator_epsilon <= 0.0)
        return ErrorCode::InvalidConfig;
    for (const Correspondence& pair : points)
        if (!std::isfinite(pair.a.x) || !std::isfinite(pair.a.y) ||
            !std::isfinite(pair.b.x) || !std::isfinite(pair.b.y))
            return ErrorCode::NumericalFailure;
    Normalization a, b;
    if (!normalize_points(points,true,a) || !normalize_points(points,false,b))
        return ErrorCode::DegenerateHomography;
    if (minimal && (!minimal_geometry_valid(a.points) || !minimal_geometry_valid(b.points)))
        return ErrorCode::DegenerateHomography;
    if (points.size() > std::numeric_limits<std::size_t>::max()/18)
        return ErrorCode::AllocationFailed;
    const std::size_t rows = std::max<std::size_t>(9,2*points.size());
    std::vector<double> design(rows*9,0.0);
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
    if (!std::isfinite(singular[0]) || singular[0] <= 0.0 ||
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

// Uniform sampling and adaptive termination.
namespace {
std::uint64_t mix64(std::uint64_t value) {
    value = (value ^ (value >> 30))*UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27))*UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

struct SampleStream {
    std::uint64_t state;
    std::uint64_t next() {
        state += UINT64_C(0x9e3779b97f4a7c15);
        return mix64(state);
    }
    std::uint64_t bounded(std::uint64_t count) {
        const std::uint64_t floor = (std::uint64_t(0)-count)%count;
        std::uint64_t value;
        do { value=next(); } while(value<floor);
        return value%count;
    }
};
}  // namespace

bool uniform_sample4(std::uint32_t seed, std::int32_t hypothesis_id,
                      std::int32_t count, std::array<std::int32_t,4>& sample) {
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

std::int32_t adaptive_iteration_budget(std::int32_t inliers, std::int32_t count,
                                       std::int32_t cap) {
    if(cap<=0) return 0;
    if(count<=0 || inliers<=0 || inliers>count) return cap;
    if(inliers==count) return 1;
    const double ratio=static_cast<double>(inliers)/static_cast<double>(count);
    const double squared=ratio*ratio;
    const double all_inliers=squared*squared;
    const double denominator=std::log1p(-all_inliers);
    if(!std::isfinite(denominator) || denominator>=0.0) return cap;
    const double needed=std::ceil(std::log1p(-feature_policy::kConfidence)/denominator);
    if(!std::isfinite(needed) || needed>=static_cast<double>(cap)) return cap;
    return static_cast<std::int32_t>(std::max(1.0,needed));
}

// MSAC scoring.
ModelScore evaluate_msac(const Matrix3& matrix, const std::vector<Correspondence>& points,
                         double threshold, double epsilon, std::vector<std::uint8_t>& mask) {
    mask.clear();
    const double threshold_squared=threshold*threshold;
    if(!std::isfinite(threshold) || threshold<=0.0 || !std::isfinite(threshold_squared) ||
       !std::isfinite(epsilon) || epsilon<=0.0 ||
       points.size()>static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max()))
        return ModelScore(std::numeric_limits<double>::infinity(),0);
    mask.resize(points.size(),0);
    std::int32_t count=0;
    const double loss=ordered_sum(points.size(),[&](std::size_t i) {
        Point2 projected;
        if(!project(matrix,points[i].b,epsilon,projected)) return threshold_squared;
        const double dx=projected.x-points[i].a.x;
        const double dy=projected.y-points[i].a.y;
        const double error_squared=dx*dx+dy*dy;
        if(!std::isfinite(error_squared)) return threshold_squared;
        if(error_squared<threshold_squared) {mask[i]=1;++count;}
        return std::min(error_squared,threshold_squared);
    });
    return ModelScore(loss,count);
}

bool better_model(const ModelScore& candidate,std::int32_t candidate_id,
                   const ModelScore& best,std::int32_t best_id) {
    if(!std::isfinite(candidate.loss) || candidate.inliers<4 || candidate_id<0) return false;
    if(best_id<0) return true;
    if(candidate.loss!=best.loss) return candidate.loss<best.loss;
    if(candidate.inliers!=best.inliers) return candidate.inliers>best.inliers;
    return candidate_id<best_id;
}

}  // namespace homography_detail
}  // namespace panorama

// Stage estimation, refit and diagnostics.
namespace panorama {
namespace {
using homography_detail::Correspondence;
using homography_detail::Matrix3;
using homography_detail::ModelScore;
using homography_detail::Point2;

bool valid_config(const Config& config) {
    return config.ransac_iters > 0 && config.ransac_iters <= feature_policy::kMaxIterations &&
           std::isfinite(config.ransac_threshold) && config.ransac_threshold > 0.0f &&
           std::isfinite(config.homography_epsilon) && config.homography_epsilon > 0.0f;
}

ErrorCode validate_inputs(FeatureView<Keypoint> left, FeatureView<Keypoint> right,
                          FeatureView<Match> matches) {
    if (!valid_feature_view(left) || !valid_feature_view(right) || !valid_feature_view(matches))
        return ErrorCode::InvalidArgument;
    for (std::int32_t i=0;i<left.count;++i)
        if (!std::isfinite(left.data[i].x) || !std::isfinite(left.data[i].y))
            return ErrorCode::NumericalFailure;
    for (std::int32_t i=0;i<right.count;++i)
        if (!std::isfinite(right.data[i].x) || !std::isfinite(right.data[i].y))
            return ErrorCode::NumericalFailure;
    std::int32_t previous=-1;
    for (std::int32_t i=0;i<matches.count;++i) {
        const Match& match=matches.data[i];
        if (match.indexA<=previous || match.indexA>=left.count ||
            match.indexB<0 || match.indexB>=right.count || match.distance>256u)
            return ErrorCode::InvalidArgument;
        previous=match.indexA;
    }
    return matches.count<4 ? ErrorCode::InsufficientMatches : ErrorCode::Success;
}

std::vector<Correspondence> selected_points(const std::vector<Correspondence>& points,
                                            const std::vector<std::uint8_t>& mask) {
    std::vector<Correspondence> selected;
    selected.reserve(points.size());
    for (std::size_t i=0;i<points.size();++i)
        if (mask[i]) selected.push_back(points[i]);
    return selected;
}

ErrorCode run_estimator(const std::vector<Correspondence>& points, Homography& output,
                        const Config& config, HomographyReport& report) {
    using namespace homography_detail;
    const double tau=static_cast<double>(config.ransac_threshold);
    const double epsilon=static_cast<double>(config.homography_epsilon);
    const std::int32_t count=static_cast<std::int32_t>(points.size());
    std::vector<Correspondence> sample_points(4);
    std::vector<std::uint8_t> mask, best_mask;
    mask.reserve(points.size());
    best_mask.reserve(points.size());
    ModelScore best_score;
    std::int32_t budget=config.ransac_iters;
    for (std::int32_t id=0;id<config.ransac_iters;++id) {
        std::array<std::int32_t,4> sample;
        if (!uniform_sample4(config.seed,id,count,sample)) return ErrorCode::InvalidArgument;
        ++report.attempts;
        for (int i=0;i<4;++i) {
            sample_points[i]=points[static_cast<std::size_t>(sample[i])];
            report.sample_hash=(report.sample_hash ^ static_cast<std::uint64_t>(sample[i]))*
                               UINT64_C(1099511628211);
        }
        Matrix3 matrix={};
        if (normalized_dlt(sample_points,true,epsilon,matrix)==ErrorCode::Success) {
            ++report.valid_hypotheses;
            const ModelScore score=evaluate_msac(matrix,points,tau,epsilon,mask);
            if (better_model(score,id,best_score,report.best_hypothesis)) {
                best_score=score;
                best_mask=mask;
                report.best_hypothesis=id;
                report.best_loss=score.loss;
                report.best_inliers=score.inliers;
                budget=adaptive_iteration_budget(score.inliers,count,config.ransac_iters);
            }
        } else {
            ++report.rejected_samples;
        }
        report.adaptive_budget=budget;
        if (report.attempts>=budget) break;
    }
    if (report.best_hypothesis<0) return ErrorCode::DegenerateHomography;
    Matrix3 refined={};
    const ErrorCode first_fit=normalized_dlt(selected_points(points,best_mask),false,epsilon,refined);
    if (first_fit!=ErrorCode::Success) return first_fit;
    report.refit_passes=1;
    ModelScore score=evaluate_msac(refined,points,tau,epsilon,mask);
    report.first_refit_loss=score.loss;
    report.first_refit_inliers=score.inliers;
    report.refit_loss=score.loss;
    if (score.inliers<4) return ErrorCode::InsufficientMatches;
    if (mask!=best_mask) {
        const ErrorCode second_fit=normalized_dlt(selected_points(points,mask),false,epsilon,refined);
        if (second_fit!=ErrorCode::Success) return second_fit;
        report.refit_passes=2;
        score=evaluate_msac(refined,points,tau,epsilon,mask);
        report.refit_loss=score.loss;
        // This is diagnostic evaluation, never another refit.
    }
    Homography candidate;
    Matrix3 stored={};
    for (int i=0;i<9;++i) {
        candidate.data[i]=static_cast<float>(refined[i]);
        stored[i]=static_cast<double>(candidate.data[i]);
    }
    const ErrorCode stored_status=validate_matrix(stored);
    if (stored_status!=ErrorCode::Success) return stored_status;
    // Float rounding can introduce a new max-absolute tie; keep the published
    // float matrix in exactly the gauge used for final evaluation.
    for (int i=0;i<9;++i) candidate.data[i]=static_cast<float>(stored[i]);
    score=evaluate_msac(stored,points,tau,epsilon,mask);
    if (!std::isfinite(score.loss)) return ErrorCode::NumericalFailure;
    if (score.inliers<4) return ErrorCode::InsufficientMatches;
    report.final_loss=score.loss;
    report.final_inliers=score.inliers;
    report.inlier_mask.swap(mask);
    report.success=true;
    output=candidate;
    return ErrorCode::Success;
}
}  // namespace

ErrorCode v0_homography(FeatureView<Keypoint> left, FeatureView<Keypoint> right,
                        FeatureView<Match> matches, Homography& output,
                        const Config& config, HomographyReport* diagnostics) {
    output=Homography();
    HomographyReport local;
    HomographyReport& report=diagnostics ? *diagnostics : local;
    report=HomographyReport();
    report.seed=config.seed;
    report.max_iterations=config.ransac_iters;
    report.threshold=config.ransac_threshold;
    if (!valid_config(config)) return ErrorCode::InvalidConfig;
    const ErrorCode input_status=validate_inputs(left,right,matches);
    if (input_status!=ErrorCode::Success) return input_status;
    try {
        std::vector<Correspondence> points(static_cast<std::size_t>(matches.count));
        for (std::int32_t i=0;i<matches.count;++i) {
            const Match& match=matches.data[i];
            const Keypoint& a=left.data[match.indexA];
            const Keypoint& b=right.data[match.indexB];
            points[i].a=Point2(a.x,a.y);
            points[i].b=Point2(b.x,b.y);
        }
        return run_estimator(points,output,config,report);
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    } catch (const std::length_error&) {
        return ErrorCode::AllocationFailed;
    }
}

void write_homography_report(std::ostream& stream, const HomographyReport& report) {
    stream << "S5 seed=" << report.seed << " max_iters=" << report.max_iterations
           << " threshold_px=" << report.threshold << " confidence=" << feature_policy::kConfidence
           << " attempts=" << report.attempts << " valid=" << report.valid_hypotheses
           << " rejected=" << report.rejected_samples << " best_id=" << report.best_hypothesis
           << " budget=" << report.adaptive_budget << " sample_hash=" << report.sample_hash;
    if (report.best_hypothesis>=0)
        stream << " best_inliers=" << report.best_inliers << " best_msac=" << report.best_loss;
    if (report.success)
        stream << " refits=" << report.refit_passes << " first_refit_msac=" << report.first_refit_loss
               << " refit_msac=" << report.refit_loss << " final_inliers=" << report.final_inliers
               << " final_msac=" << report.final_loss;
    stream << " success=" << (report.success ? 1 : 0) << '\n';
}

}  // namespace panorama
