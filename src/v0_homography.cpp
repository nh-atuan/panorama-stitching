// Authors: Le Thuong De (23120232)
// Adapted from: Brown and Lowe (2007), https://www.cs.ubc.ca/~lowe/papers/07brown.pdf,
// accessed 2026-10-13; OpenCV USAC algorithm descriptions,
// https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html, accessed 2026-10-13;
// Fowler/Noll/Vo, https://www.isthe.com/chongo/tech/comp/fnv/index.html,
// accessed 2026-10-13.
// Changes: project-specific uniform sample streams, normalized DLT double,
// MSAC/prefix-adaptive selection, bounded all-inlier refits, float output validation
// and Host diagnostics separated from stage I/O. The FNV-style fingerprint hashes
// whole sample indices rather than bytes. No external estimator copied.

#include "v0_homography.h"
#include "feature_config.h"
#include "homography_dlt.h"
#include "homography_sampling.h"
#include "homography_scoring.h"
#include <cmath>
#include <new>
#include <ostream>
#include <stdexcept>

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
