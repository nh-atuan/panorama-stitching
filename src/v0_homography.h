// Authors: Le Thuong De (23120232)
// Adapted from: Fowler/Noll/Vo hash parameters,
// https://www.isthe.com/chongo/tech/comp/fnv/index.html, accessed 2026-10-13.
// Changes: diagnostic fingerprint over whole sample indices, not byte-stream FNV.

#ifndef GROUP16_V0_HOMOGRAPHY_H
#define GROUP16_V0_HOMOGRAPHY_H

#include "feature_views.h"
#include <iosfwd>
#include <vector>

namespace panorama {

// Host-only diagnostics, never a CUDA transfer payload.
struct HomographyReport {
    bool success = false;
    std::uint32_t seed = 0;
    std::int32_t max_iterations = 0;
    float threshold = 0.0f;
    std::int32_t attempts = 0;
    std::int32_t valid_hypotheses = 0;
    std::int32_t rejected_samples = 0;
    std::int32_t best_hypothesis = -1;
    std::int32_t adaptive_budget = 0;
    std::int32_t best_inliers = 0;
    std::int32_t first_refit_inliers = 0;
    std::int32_t final_inliers = 0;
    std::int32_t refit_passes = 0;
    std::uint64_t sample_hash = UINT64_C(14695981039346656037);
    double best_loss = 0.0;
    double first_refit_loss = 0.0;
    double refit_loss = 0.0;
    double final_loss = 0.0;
    std::vector<std::uint8_t> inlier_mask;
};

// Borrowed Host inputs; matches must have strictly increasing indexA, as S4 emits.
// H maps B -> A, float32/max-abs normalized, and is invalid/zero on failure.
// Reports retain progress counters on failure but no successful output mask.
// The stage performs no I/O. Call write_homography_report OUTSIDE timing regions.
ErrorCode v0_homography(FeatureView<Keypoint> left, FeatureView<Keypoint> right,
                        FeatureView<Match> matches, Homography& output,
                        const Config& config, HomographyReport* report = nullptr);
void write_homography_report(std::ostream& stream, const HomographyReport& report);

}  // namespace panorama

#endif
