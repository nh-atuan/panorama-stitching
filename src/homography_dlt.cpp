// Authors: Le Thuong De (23120232)
// Adapted from: Harker and O'Leary, Computation of Homographies, section 2.3,
// https://www.robots.ox.ac.uk/~phst/BMVC2005/papers/190/paper190.pdf,
// accessed 2026-10-13. No external implementation copied.
// Changes: RMS normalization with fixed reductions, direct full-basis Jacobi SVD,
// B-to-A convention, minimal geometry/rank checks and project error handling.

#include "homography_dlt.h"
#include "feature_support.h"
#include "homography_svd.h"
#include "ordered_reduction.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace panorama {
namespace homography_detail {
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

}  // namespace homography_detail
}  // namespace panorama
