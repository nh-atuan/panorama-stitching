// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0/v0_detect.h"
#include "common/fast_corner.h"
#include "common/feature_border.h"
#include "support/feature_test_support.h"
#include <algorithm>
#include <cmath>
#include <limits>

using namespace panorama;

namespace {

const float kNaN = std::numeric_limits<float>::quiet_NaN();
const float kInf = std::numeric_limits<float>::infinity();

// Circle of Rosten and Drummond (2006), Figure 1, pixels 1..16 from the top, clockwise.
const int kPaperCircle[16][2] = {{0, -3}, {1, -3}, {2, -2}, {3, -1}, {3, 0}, {3, 1},
                                 {2, 2},  {1, 3},  {0, 3},  {-1, 3}, {-2, 2}, {-3, 1},
                                 {-3, 0}, {-3, -1}, {-2, -2}, {-1, -3}};

Config detect_config(float threshold = 0.05f, std::int32_t max_keypoints = 2000) {
    Config config;
    config.fast_threshold = threshold;
    config.max_keypoints = max_keypoints;
    return config;
}

struct RefCorner {
    float score;
    std::size_t raster;
};

// Independent reference: brute-force arc search from every start, explicit NMS ordering.
std::vector<Keypoint> reference_detect(const GrayFixture& f, float t, std::int32_t limit) {
    const std::int32_t w = f.image.width;
    const std::int32_t h = f.image.height;
    std::vector<float> score(static_cast<std::size_t>(w) * h, 0.0f);
    for (std::int32_t y = kFeatureBorder; y <= h - 1 - kFeatureBorder; ++y) {
        for (std::int32_t x = kFeatureBorder; x <= w - 1 - kFeatureBorder; ++x) {
            const float c = f.at(x, y);
            float v[16];
            for (int i = 0; i < 16; ++i) v[i] = f.at(x + kPaperCircle[i][0], y + kPaperCircle[i][1]);
            bool corner = false;
            for (int start = 0; start < 16 && !corner; ++start) {
                bool all_bright = true;
                bool all_dark = true;
                for (int j = 0; j < 9; ++j) {
                    const float d = v[(start + j) % 16] - c;
                    if (!(d > t)) all_bright = false;
                    if (!(d < -t)) all_dark = false;
                }
                corner = all_bright || all_dark;
            }
            if (!corner) continue;
            float sb = 0.0f;
            float sd = 0.0f;
            for (int i = 0; i < 16; ++i) {
                const float d = v[i] - c;
                if (d > t) sb += d - t;
                else if (d < -t) sd += -d - t;
            }
            score[static_cast<std::size_t>(y) * w + x] = std::max(sb, sd);
        }
    }
    std::vector<RefCorner> kept;
    for (std::int32_t y = 1; y < h - 1; ++y) {
        for (std::int32_t x = 1; x < w - 1; ++x) {
            const std::size_t p = static_cast<std::size_t>(y) * w + x;
            if (score[p] <= 0.0f) continue;
            bool maximum = true;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    const std::size_t q = static_cast<std::size_t>(y + dy) * w + (x + dx);
                    if (q == p) continue;
                    // p survives only if it beats q on (score, then earlier raster index).
                    if (!(score[q] < score[p] || (score[q] == score[p] && q > p))) maximum = false;
                }
            }
            if (maximum) kept.push_back(RefCorner{score[p], p});
        }
    }
    std::sort(kept.begin(), kept.end(), [](const RefCorner& a, const RefCorner& b) {
        return a.score > b.score || (a.score == b.score && a.raster < b.raster);
    });
    std::vector<Keypoint> out;
    for (std::size_t i = 0; i < kept.size() && i < static_cast<std::size_t>(limit); ++i) {
        Keypoint k;
        k.x = static_cast<float>(kept[i].raster % w);
        k.y = static_cast<float>(kept[i].raster / w);
        k.score = kept[i].score;
        out.push_back(k);
    }
    return out;
}

bool same_keypoints(const std::vector<Keypoint>& a, const std::vector<Keypoint>& b) {
    if (a.size() != b.size()) return false;
    for (std::size_t i = 0; i < a.size(); ++i) {
        if (a[i].x != b[i].x || a[i].y != b[i].y || a[i].score != b[i].score ||
            a[i].angle != b[i].angle) {
            return false;
        }
    }
    return true;
}

ErrorCode detect(const GrayFixture& f, std::vector<Keypoint>& out, const Config& config) {
    return v0_detect(f.image, out, config);
}

void test_circle_table() {
    for (int i = 0; i < 16; ++i) {
        require(kFastCircle[i][0] == kPaperCircle[i][0] && kFastCircle[i][1] == kPaperCircle[i][1],
                "circle offsets follow the paper");
        const int r2 = kFastCircle[i][0] * kFastCircle[i][0] + kFastCircle[i][1] * kFastCircle[i][1];
        require(r2 >= 8 && r2 <= 10, "circle offsets lie on the radius-3 Bresenham circle");
    }
}

void fill_ring(float ring[16], float value) {
    for (int i = 0; i < 16; ++i) ring[i] = value;
}

void test_segment_test() {
    const float c = 0.5f;
    const float t = 0.125f;
    float ring[16];
    fill_ring(ring, c);
    require(fast_corner_score(c, ring, t) == 0.0f, "flat ring is not a corner");

    for (int start = 0; start < 16; ++start) {
        for (int length = 1; length <= 16; ++length) {
            for (int sign = -1; sign <= 1; sign += 2) {
                fill_ring(ring, c);
                for (int j = 0; j < length; ++j) ring[(start + j) % 16] = c + sign * 0.375f;
                const float s = fast_corner_score(c, ring, t);
                if (length < 9) {
                    require(s == 0.0f, "arc shorter than 9 is not a corner");
                } else {
                    require(s == 0.25f * static_cast<float>(length), "arc of 9+ scores sum(|d| - t)");
                }
            }
        }
    }

    // Two bright arcs of 7 separated by similar pixels 0 and 8: never 9 in a row.
    fill_ring(ring, c);
    for (int j = 1; j <= 7; ++j) ring[j] = 0.9f;
    for (int j = 9; j <= 15; ++j) ring[j] = 0.9f;
    require(fast_corner_score(c, ring, t) == 0.0f, "interrupted arcs are not a corner");

    // |d| exactly equal to the threshold is neither bright nor dark (0.75 - 0.5 == 0.25).
    fill_ring(ring, 0.75f);
    require(fast_corner_score(0.5f, ring, 0.25f) == 0.0f, "difference equal to t is not bright");
    fill_ring(ring, 0.25f);
    require(fast_corner_score(0.5f, ring, 0.25f) == 0.0f, "difference equal to -t is not dark");

    // Score V by hand: 9 bright (d = 0.375) and 3 dark (d = -0.5) with t = 0.125.
    fill_ring(ring, c);
    for (int j = 0; j < 9; ++j) ring[j] = 0.875f;
    for (int j = 9; j < 12; ++j) ring[j] = 0.0f;
    require(fast_corner_score(c, ring, t) == 2.25f, "V = max(9 * 0.25, 3 * 0.375)");
    // Dark side wins when its sum is larger: 9 dark (d = -0.5) and 4 bright (d = 0.375).
    fill_ring(ring, c);
    for (int j = 3; j < 12; ++j) ring[j] = 0.0f;
    for (int j = 12; j < 16; ++j) ring[j] = 0.875f;
    require(fast_corner_score(c, ring, t) == 3.375f, "V = max(4 * 0.25, 9 * 0.375)");
}

void test_matches_reference() {
    TestRandom random(16);
    std::size_t compared = 0;
    const std::int32_t sizes[][2] = {{64, 48}, {100, 37}, {37, 90}, {31, 31}, {80, 80}};
    const float thresholds[] = {0.02f, 0.05f, 0.1f, 0.3f};
    for (const auto& size : sizes) {
        for (float t : thresholds) {
            for (int variant = 0; variant < 3; ++variant) {
                GrayFixture f(size[0], size[1]);
                if (variant == 0) {
                    paint_rectangles(f, random, 40);
                } else {
                    // Values from {0, 0.5, 1}: many equal scores exercise the tie rules.
                    for (std::int32_t y = 0; y < size[1]; ++y)
                        for (std::int32_t x = 0; x < size[0]; ++x)
                            f.at(x, y) = 0.5f * static_cast<float>(random.below(3));
                }
                const std::int32_t limits[] = {2000, 7, 1};
                for (std::int32_t limit : limits) {
                    std::vector<Keypoint> out;
                    require(detect(f, out, detect_config(t, limit)) == ErrorCode::Success,
                            "random image succeeds");
                    require(same_keypoints(out, reference_detect(f, t, limit)),
                            "v0_detect equals the brute-force reference");
                    compared += out.size();
                }
            }
        }
    }
    require(compared > 1000, "reference comparison covers many keypoints");
}

void test_square_corners() {
    GrayFixture f(120, 120, 0, 0.1f);
    f.rect(40, 40, 79, 79, 0.9f);
    std::vector<Keypoint> out;
    require(detect(f, out, detect_config(0.05f)) == ErrorCode::Success, "square succeeds");
    const float corners[4][2] = {{40, 40}, {79, 40}, {40, 79}, {79, 79}};
    bool found[4] = {false, false, false, false};
    for (const Keypoint& k : out) {
        bool near_corner = false;
        for (int c = 0; c < 4; ++c) {
            if (std::fabs(k.x - corners[c][0]) <= 2.0f && std::fabs(k.y - corners[c][1]) <= 2.0f) {
                near_corner = true;
                found[c] = true;
            }
        }
        require(near_corner, "square keypoints lie within 2 px of a corner");
        require(k.angle == 0.0f && k.score > 0.0f, "keypoint has score > 0 and angle 0");
    }
    for (int c = 0; c < 4; ++c) require(found[c], "each square corner has a keypoint");
}

void test_flat_and_small_images() {
    GrayFixture flat(64, 64, 0, 0.4f);
    std::vector<Keypoint> out(3);
    require(detect(flat, out, detect_config()) == ErrorCode::Success && out.empty(),
            "constant image has no keypoints");

    const std::int32_t sizes[][2] = {{1, 1}, {30, 30}, {30, 200}, {200, 30}, {2, 2}};
    for (const auto& size : sizes) {
        GrayFixture f(size[0], size[1], 0, 0.0f);
        TestRandom random(3);
        paint_rectangles(f, random, 10);
        out.assign(2, Keypoint());
        require(detect(f, out, detect_config()) == ErrorCode::Success && out.empty(),
                "image without a border region gives an empty Success");
    }

    // 31 x 31: the only candidate is (15, 15); a dark dot on bright ground is a corner.
    GrayFixture dot(31, 31, 0, 0.9f);
    dot.at(15, 15) = 0.1f;
    require(detect(dot, out, detect_config()) == ErrorCode::Success && out.size() == 1 &&
                out[0].x == 15.0f && out[0].y == 15.0f,
            "31 x 31 image detects its single candidate");
}

void test_border_order_and_nms() {
    TestRandom random(99);
    GrayFixture f(160, 120);
    paint_rectangles(f, random, 120);
    std::vector<Keypoint> all;
    require(detect(f, all, detect_config(0.02f, kMaxKeypointsLimit)) == ErrorCode::Success,
            "dense image succeeds");
    require(all.size() > 50, "dense image has many keypoints");
    for (std::size_t i = 0; i < all.size(); ++i) {
        const Keypoint& k = all[i];
        require(k.x >= kFeatureBorder && k.x <= 160 - 1 - kFeatureBorder &&
                    k.y >= kFeatureBorder && k.y <= 120 - 1 - kFeatureBorder,
                "keypoint inside the border");
        require(k.x == std::floor(k.x) && k.y == std::floor(k.y), "integer coordinates");
        if (i > 0) {
            const Keypoint& p = all[i - 1];
            const bool ordered = p.score > k.score ||
                                 (p.score == k.score && (p.y < k.y || (p.y == k.y && p.x < k.x)));
            require(ordered, "sorted by score descending, then raster ascending");
        }
        for (std::size_t j = 0; j < i; ++j) {
            const bool adjacent = std::fabs(all[j].x - k.x) <= 1.0f && std::fabs(all[j].y - k.y) <= 1.0f;
            require(!adjacent, "NMS leaves no two 8-neighbours");
        }
    }
    for (std::int32_t limit = 1; limit <= 20; ++limit) {
        std::vector<Keypoint> top;
        require(detect(f, top, detect_config(0.02f, limit)) == ErrorCode::Success &&
                    top.size() == static_cast<std::size_t>(limit),
                "max_keypoints caps the count");
        require(std::equal(top.begin(), top.end(), all.begin(),
                           [](const Keypoint& a, const Keypoint& b) {
                               return a.x == b.x && a.y == b.y && a.score == b.score;
                           }),
                "capped result is a prefix of the full ranking");
    }
}

void test_padding_and_repeat() {
    TestRandom random(5);
    GrayFixture packed(90, 70);
    paint_rectangles(packed, random, 50);
    GrayFixture padded(90, 70, 7);
    for (std::int32_t y = 0; y < 70; ++y)
        for (std::int32_t x = 0; x < 90; ++x) padded.at(x, y) = packed.at(x, y);
    const std::vector<float> padded_before = padded.storage;
    std::vector<Keypoint> a;
    std::vector<Keypoint> b;
    std::vector<Keypoint> c;
    require(detect(packed, a, detect_config()) == ErrorCode::Success, "packed succeeds");
    require(detect(padded, b, detect_config()) == ErrorCode::Success, "padded succeeds");
    require(!a.empty() && same_keypoints(a, b), "row padding does not change the result");
    require(padded.storage == padded_before, "input image and padding are untouched");
    require(detect(packed, c, detect_config()) == ErrorCode::Success && same_keypoints(a, c),
            "repeated runs are identical");
}

void test_invalid_inputs() {
    GrayFixture f(64, 64);
    const Config ok = detect_config();
    std::vector<Keypoint> out;
    auto expect = [&](const GrayImage& image, const Config& config, ErrorCode code,
                      const char* message) {
        out.assign(4, Keypoint());
        require(v0_detect(image, out, config) == code && out.empty(), message);
    };

    GrayImage bad = f.image;
    bad.data = nullptr;
    expect(bad, ok, ErrorCode::InvalidImage, "null data");
    bad = f.image;
    bad.channels = 3;
    expect(bad, ok, ErrorCode::InvalidImage, "three channels");
    bad = f.image;
    bad.width = 0;
    expect(bad, ok, ErrorCode::InvalidImage, "zero width");
    bad = f.image;
    bad.height = -2;
    expect(bad, ok, ErrorCode::InvalidImage, "negative height");
    bad = f.image;
    bad.stride = 64;  // elements instead of bytes
    expect(bad, ok, ErrorCode::InvalidImage, "stride in elements");
    bad = f.image;
    bad.stride = 64 * 4 + 2;
    expect(bad, ok, ErrorCode::InvalidImage, "stride not a multiple of 4");
    bad = f.image;
    bad.data = reinterpret_cast<float*>(reinterpret_cast<unsigned char*>(f.storage.data()) + 1);
    expect(bad, ok, ErrorCode::InvalidImage, "misaligned data");
    bad = f.image;
    bad.stride = std::numeric_limits<std::size_t>::max() / 2 / 4 * 4;
    expect(bad, ok, ErrorCode::InvalidImage, "stride * height overflows");

    const float thresholds[] = {0.0f, 1.0f, -0.1f, 1.5f, kNaN, kInf, -kInf};
    for (float t : thresholds) expect(f.image, detect_config(t), ErrorCode::InvalidConfig, "threshold");
    const std::int32_t counts[] = {0, -1, kMaxKeypointsLimit + 1};
    for (std::int32_t n : counts)
        expect(f.image, detect_config(0.05f, n), ErrorCode::InvalidConfig, "max_keypoints");
    expect(f.image, Config(), ErrorCode::InvalidConfig, "unset Config");
    bad = f.image;
    bad.data = nullptr;
    expect(bad, Config(), ErrorCode::InvalidImage, "image error reported before config error");
    expect(f.image, detect_config(0.05f, kMaxKeypointsLimit), ErrorCode::Success, "limit accepted");
}

void test_allocation_failure() {
    TestRandom random(8);
    GrayFixture f(80, 80);
    paint_rectangles(f, random, 30);
    std::vector<Keypoint> out(5);
    out.reserve(64);
    fail_allocations = true;
    const ErrorCode status = v0_detect(f.image, out, detect_config());
    fail_allocations = false;
    require(status == ErrorCode::AllocationFailed && out.empty(), "bad_alloc maps to AllocationFailed");
}

}  // namespace

int main() {
    try {
        test_circle_table();
        test_segment_test();
        test_matches_reference();
        test_square_corners();
        test_flat_and_small_images();
        test_border_order_and_nms();
        test_padding_and_repeat();
        test_invalid_inputs();
        test_allocation_failure();
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " assertions: " << error.what() << '\n';
        return 1;
    }
    std::cout << "PASS: " << checks << " assertions for S2 FAST-9 detection" << '\n';
    return 0;
}
