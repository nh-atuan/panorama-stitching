// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0_detect.h"
#include "fast_corner.h"
#include "feature_border.h"
#include "image_layout.h"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iostream>
#include <memory>
#include <new>

namespace panorama {
namespace {

static_assert(kFeatureBorder >= kFastRadius, "FAST circle must stay inside the image");

struct Candidate {
    float score;
    std::size_t raster;
};

bool valid_config(const Config& config) {
    const float t = config.fast_threshold;
    return std::isfinite(t) && t > 0.0f && t < 1.0f && config.max_keypoints >= 1 &&
           config.max_keypoints <= kMaxKeypointsLimit;
}

// scores (packed, width per row) = FAST score inside the border region, 0 elsewhere.
void compute_scores(const GrayImage& image, float threshold, float* scores) {
    const std::int32_t width = image.width;
    const std::int32_t height = image.height;
    for (std::int32_t y = kFeatureBorder; y < height - kFeatureBorder; ++y) {
        const float* rows[2 * kFastRadius + 1];
        for (std::int32_t dy = -kFastRadius; dy <= kFastRadius; ++dy) {
            rows[dy + kFastRadius] = gray_row(image, y + dy);
        }
        float* out = scores + static_cast<std::size_t>(y) * static_cast<std::size_t>(width);
        for (std::int32_t x = kFeatureBorder; x < width - kFeatureBorder; ++x) {
            float ring[kFastCircleSize];
            for (std::int32_t i = 0; i < kFastCircleSize; ++i) {
                ring[i] = rows[kFastCircle[i][1] + kFastRadius][x + kFastCircle[i][0]];
            }
            out[x] = fast_corner_score(rows[kFastRadius][x], ring, threshold);
        }
    }
}

// A neighbour earlier in raster order wins ties, so exactly one pixel of a plateau survives.
bool is_local_maximum(const float* scores, std::int32_t width, std::int32_t x, std::int32_t y) {
    const float s = scores[static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + x];
    for (std::int32_t dy = -1; dy <= 1; ++dy) {
        for (std::int32_t dx = -1; dx <= 1; ++dx) {
            if (dx == 0 && dy == 0) continue;
            const float q = scores[static_cast<std::size_t>(y + dy) * static_cast<std::size_t>(width) +
                                   (x + dx)];
            const bool earlier = dy < 0 || (dy == 0 && dx < 0);
            if (q > s || (earlier && q == s)) return false;
        }
    }
    return true;
}

// Border >= 1, so every neighbour of a candidate is inside the score map.
void collect_maxima(const float* scores, std::int32_t width, std::int32_t height,
                    std::vector<Candidate>& candidates) {
    for (std::int32_t y = kFeatureBorder; y < height - kFeatureBorder; ++y) {
        const std::size_t row = static_cast<std::size_t>(y) * static_cast<std::size_t>(width);
        for (std::int32_t x = kFeatureBorder; x < width - kFeatureBorder; ++x) {
            const float s = scores[row + x];
            if (s > 0.0f && is_local_maximum(scores, width, x, y)) {
                Candidate c;
                c.score = s;
                c.raster = row + static_cast<std::size_t>(x);
                candidates.push_back(c);
            }
        }
    }
}

bool stronger(const Candidate& a, const Candidate& b) {
    if (a.score != b.score) return a.score > b.score;
    return a.raster < b.raster;
}

void select_strongest(std::vector<Candidate>& candidates, std::int32_t limit, std::int32_t width,
                      std::vector<Keypoint>& keypoints) {
    std::sort(candidates.begin(), candidates.end(), stronger);
    const std::size_t count = std::min(candidates.size(), static_cast<std::size_t>(limit));
    keypoints.reserve(count);
    const std::size_t w = static_cast<std::size_t>(width);
    for (std::size_t i = 0; i < count; ++i) {
        Keypoint k;
        k.x = static_cast<float>(candidates[i].raster % w);
        k.y = static_cast<float>(candidates[i].raster / w);
        k.score = candidates[i].score;
        k.angle = 0.0f;
        keypoints.push_back(k);
    }
}

}  // namespace

ErrorCode v0_detect(const GrayImage& image, std::vector<Keypoint>& output,
                    const Config& config, bool debug_mode) {
    output.clear();
    if (!valid_gray_image(image)) return ErrorCode::InvalidImage;
    if (!valid_config(config)) return ErrorCode::InvalidConfig;
    std::size_t pixels = 0;
    if (!gray_pixel_count(image.width, image.height, pixels)) return ErrorCode::InvalidImage;

    std::vector<Keypoint> keypoints;
    std::size_t candidate_count = 0;
    if (image.width > 2 * kFeatureBorder && image.height > 2 * kFeatureBorder) {
        try {
            std::unique_ptr<float[]> scores(new float[pixels]());
            compute_scores(image, config.fast_threshold, scores.get());
            std::vector<Candidate> candidates;
            collect_maxima(scores.get(), image.width, image.height, candidates);
            candidate_count = candidates.size();
            select_strongest(candidates, config.max_keypoints, image.width, keypoints);
        } catch (const std::bad_alloc&) {
            return ErrorCode::AllocationFailed;
        }
    }

    output.swap(keypoints);
    if (debug_mode) {
        std::cerr << "[S2] " << image.width << "x" << image.height
                  << " threshold=" << config.fast_threshold << " maxima=" << candidate_count
                  << " keypoints=" << output.size() << '\n';
    }
    return ErrorCode::Success;
}

}  // namespace panorama
