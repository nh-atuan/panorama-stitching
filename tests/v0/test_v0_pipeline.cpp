// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// The whole V0 pipeline (S1..S6 through v0_prepare/v0_run) on a synthetic pair:
// A and B are cut from one textured scene, B shifted by an integer offset, so the
// homography, canvas and panorama pixels have known answers.

#include "v0/v0_pipeline.h"
#include "common/v0_config.h"
#include "support/feature_test_support.h"
#include <cmath>
#include <cstring>

using namespace panorama;

namespace {

const std::int32_t kWidth = 480;
const std::int32_t kHeight = 320;
const std::int32_t kShiftX = 37;  // B(x, y) = A(x + kShiftX, y + kShiftY)
const std::int32_t kShiftY = -11;
const std::int32_t kLeft = 20;    // position of A inside the scene
const std::int32_t kTop = 25;

// Wider scene of random coloured rectangles, so both cuts are fully textured.
struct Scene {
    std::int32_t width = kWidth + 80;
    std::int32_t height = kHeight + 40;
    std::vector<std::uint8_t> rgb;
    Scene() : rgb(static_cast<std::size_t>(width) * height * 3, 100) {
        TestRandom random(2026);
        for (int r = 0; r < 900; ++r) {
            const std::int32_t x0 = random.below(width);
            const std::int32_t y0 = random.below(height);
            const std::int32_t w = 4 + random.below(30);
            const std::int32_t h = 4 + random.below(30);
            std::uint8_t c[3];
            for (int ch = 0; ch < 3; ++ch) c[ch] = static_cast<std::uint8_t>(random.below(256));
            for (std::int32_t y = y0; y < y0 + h && y < height; ++y)
                for (std::int32_t x = x0; x < x0 + w && x < width; ++x)
                    for (int ch = 0; ch < 3; ++ch) rgb[(static_cast<std::size_t>(y) * width + x) * 3 + ch] = c[ch];
        }
    }
    const std::uint8_t* at(std::int32_t x, std::int32_t y) const {
        return rgb.data() + (static_cast<std::size_t>(y) * width + x) * 3;
    }
};

struct RgbImage {
    std::vector<std::uint8_t> pixels;
    Image image;
    RgbImage(const Scene& scene, std::int32_t left, std::int32_t top)
        : pixels(static_cast<std::size_t>(kWidth) * kHeight * 3) {
        for (std::int32_t y = 0; y < kHeight; ++y)
            std::memcpy(pixels.data() + static_cast<std::size_t>(y) * kWidth * 3,
                        scene.at(left, top + y), static_cast<std::size_t>(kWidth) * 3);
        image.data = pixels.data();
        image.width = kWidth;
        image.height = kHeight;
        image.channels = 3;
        image.stride = static_cast<std::size_t>(kWidth) * 3;
    }
};

struct Pair {
    Scene scene;
    RgbImage a;
    RgbImage b;
    Config config;
    Pair() : a(scene, kLeft, kTop), b(scene, kLeft + kShiftX, kTop + kShiftY) {
        require(make_v0_config(kWidth, kHeight, config) == ErrorCode::Success, "config");
    }
};

// Panorama pixel at image-A coordinates (xa, ya).
const std::uint8_t* canvas_at(const Panorama& panorama, std::int32_t xa, std::int32_t ya) {
    const std::int32_t xc = xa + panorama.offset_x;
    const std::int32_t yc = ya + panorama.offset_y;
    return panorama.image.data + static_cast<std::size_t>(yc) * panorama.image.stride +
           static_cast<std::size_t>(xc) * 3;
}

// Mean absolute difference between the panorama and the scene over A-frame rectangle.
double mean_difference(const Pair& pair, const Panorama& panorama, std::int32_t x0,
                       std::int32_t x1, std::int32_t y0, std::int32_t y1) {
    double total = 0.0;
    std::size_t count = 0;
    for (std::int32_t y = y0; y <= y1; ++y)
        for (std::int32_t x = x0; x <= x1; ++x)
            for (int ch = 0; ch < 3; ++ch) {
                total += std::fabs(static_cast<double>(canvas_at(panorama, x, y)[ch]) -
                                   pair.scene.at(x + kLeft, y + kTop)[ch]);
                ++count;
            }
    return total / static_cast<double>(count);
}

void test_translated_pair() {
    Pair pair;
    V0Workspace ws;
    require(v0_prepare(pair.a.image, pair.b.image, pair.config, ws) == ErrorCode::Success, "prepare");
    HomographyReport report;
    Stage stage = Stage::Preprocess;
    require(v0_run(pair.a.image, pair.b.image, pair.config, ws, nullptr, &stage, &report) ==
                ErrorCode::Success, "pipeline");
    require(ws.detected_a > 300 && ws.detected_b > 300, "S2 finds many keypoints");
    require(ws.matches.size() > 100, "S4 keeps many matches");
    require(report.success && report.inlier_mask.size() == ws.matches.size(), "S5 report");
    require(report.final_inliers * 10 >= static_cast<std::int32_t>(ws.matches.size()) * 9,
            "at least 90% of matches are inliers");

    const Homography& h = ws.homography;
    const float corners[4][2] = {{0, 0}, {kWidth - 1.0f, 0}, {0, kHeight - 1.0f},
                                 {kWidth - 1.0f, kHeight - 1.0f}};
    for (const auto& c : corners) {
        const double u = h.data[0] * c[0] + h.data[1] * c[1] + h.data[2];
        const double v = h.data[3] * c[0] + h.data[4] * c[1] + h.data[5];
        const double w = h.data[6] * c[0] + h.data[7] * c[1] + h.data[8];
        require(std::fabs(u / w - (c[0] + kShiftX)) < 0.1 && std::fabs(v / w - (c[1] + kShiftY)) < 0.1,
                "H maps B corners onto A within 0.1 px");
    }

    // Union of A [0, 479] x [0, 319] and shifted B [37, 516] x [-11, 308]; the bbox may
    // grow by one pixel because H is estimated, not exact.
    const Panorama& p = ws.panorama;
    require(p.image.data != nullptr && p.image.channels == 3, "S6 output");
    require(p.image.width >= 517 && p.image.width <= 518, "canvas width");
    require(p.image.height >= 331 && p.image.height <= 332, "canvas height");
    require(p.offset_x >= 0 && p.offset_x <= 1 && p.offset_y >= 11 && p.offset_y <= 12, "offset");

    // Left strip and bottom strip are covered by A only, so they are copied exactly.
    for (std::int32_t y = 0; y < kHeight; ++y)
        for (std::int32_t x = 0; x < 35; ++x)
            require(std::memcmp(canvas_at(p, x, y), pair.scene.at(x + kLeft, y + kTop), 3) == 0,
                    "A-only pixels are copied");
    for (std::int32_t y = 311; y < kHeight; ++y)
        for (std::int32_t x = 0; x < kWidth; ++x)
            require(std::memcmp(canvas_at(p, x, y), pair.scene.at(x + kLeft, y + kTop), 3) == 0,
                    "A-only pixels are copied");
    // Above A and left of B nothing is valid: background stays black.
    for (std::int32_t y = -10; y < 0; ++y)
        for (std::int32_t x = 0; x < 35; ++x) {
            const std::uint8_t* pixel = canvas_at(p, x, y);
            require(pixel[0] == 0 && pixel[1] == 0 && pixel[2] == 0, "background is black");
        }
    // Overlap blends A with resampled B, and the B-only strip comes from B: both close
    // to the scene up to bilinear resampling at rectangle edges.
    const double overlap = mean_difference(pair, p, 40, 475, 0, 305);
    const double b_only = mean_difference(pair, p, 482, 514, -9, 305);
    require(overlap < 4.0, "overlap matches the scene");
    require(b_only < 8.0, "B-only strip matches the scene");
    std::cout << "pipeline: keypoints A=" << ws.detected_a << " B=" << ws.detected_b
              << " matches=" << ws.matches.size() << " inliers=" << report.final_inliers
              << " canvas=" << p.image.width << 'x' << p.image.height
              << " mean_diff overlap=" << overlap << " b_only=" << b_only << '\n';
}

void test_repeated_runs_are_identical() {
    Pair pair;
    V0Workspace ws;
    require(v0_prepare(pair.a.image, pair.b.image, pair.config, ws) == ErrorCode::Success, "prepare");
    require(v0_run(pair.a.image, pair.b.image, pair.config, ws, nullptr, nullptr) ==
                ErrorCode::Success, "first run");
    const Homography first_h = ws.homography;
    const Panorama first = ws.panorama;
    const std::size_t bytes = first.image.stride * static_cast<std::size_t>(first.image.height);
    const std::vector<std::uint8_t> first_pixels(first.image.data, first.image.data + bytes);
    for (int run = 0; run < 3; ++run) {
        TimingStats timing;
        timing.end_to_end_ms = -1.0;
        require(v0_run(pair.a.image, pair.b.image, pair.config, ws, &timing, nullptr) ==
                    ErrorCode::Success, "timed run");
        double sum = 0.0;
        for (std::size_t s = 0; s < kStageCount; ++s) {
            require(timing.stage_ms[s] >= 0.0, "stage time is measured");
            sum += timing.stage_ms[s];
        }
        require(timing.end_to_end_ms >= sum * 0.999, "end-to-end covers the six stages");
        require(std::memcmp(first_h.data, ws.homography.data, sizeof(first_h.data)) == 0,
                "same H on every run");
        require(ws.panorama.image.width == first.image.width &&
                    ws.panorama.image.height == first.image.height &&
                    ws.panorama.offset_x == first.offset_x && ws.panorama.offset_y == first.offset_y,
                "same canvas on every run");
        require(std::memcmp(ws.panorama.image.data, first_pixels.data(), bytes) == 0,
                "same panorama pixels on every run");
    }
    v0_release_output(ws);
    require(ws.panorama.image.data == nullptr && ws.panorama.image.width == 0, "release resets");
    v0_release_output(ws);  // releasing twice is harmless
}

void test_reports_failing_stage() {
    Pair pair;
    {
        V0Workspace ws;
        Config config = pair.config;
        require(v0_prepare(pair.a.image, pair.b.image, config, ws) == ErrorCode::Success, "prepare");
        config.gaussian_sigma = 0.0f;
        Stage stage = Stage::WarpBlend;
        require(v0_run(pair.a.image, pair.b.image, config, ws, nullptr, &stage) ==
                    ErrorCode::InvalidConfig, "bad sigma");
        require(stage == Stage::Preprocess, "S1 reported");
        require(ws.panorama.image.data == nullptr, "no panorama on failure");
    }
    {
        V0Workspace ws;
        Config config = pair.config;
        require(v0_prepare(pair.a.image, pair.b.image, config, ws) == ErrorCode::Success, "prepare");
        config.match_ratio_threshold = 0.7f;  // S4 accepts only the chosen ratio
        Stage stage = Stage::Preprocess;
        require(v0_run(pair.a.image, pair.b.image, config, ws, nullptr, &stage) ==
                    ErrorCode::InvalidConfig, "bad ratio");
        require(stage == Stage::Match, "S4 reported");
    }
    {
        V0Workspace ws;  // not prepared: S1 has no gray buffer
        Stage stage = Stage::WarpBlend;
        require(v0_run(pair.a.image, pair.b.image, pair.config, ws, nullptr, &stage) ==
                    ErrorCode::InvalidImage, "unprepared workspace");
        require(stage == Stage::Preprocess, "S1 reported");
    }
    {
        // A previous panorama is released before the run, even when the run then fails.
        V0Workspace ws;
        require(v0_prepare(pair.a.image, pair.b.image, pair.config, ws) == ErrorCode::Success, "prepare");
        require(v0_run(pair.a.image, pair.b.image, pair.config, ws, nullptr, nullptr) ==
                    ErrorCode::Success, "run");
        Config config = pair.config;
        config.gaussian_sigma = 0.0f;
        require(v0_run(pair.a.image, pair.b.image, config, ws, nullptr, nullptr) ==
                    ErrorCode::InvalidConfig, "failing run");
        require(ws.panorama.image.data == nullptr, "old panorama released");
    }
}

void test_prepare_errors() {
    Pair pair;
    V0Workspace ws;
    Image empty = pair.a.image;
    empty.width = 0;
    require(v0_prepare(empty, pair.b.image, pair.config, ws) == ErrorCode::InvalidImage, "zero width");
    Config config = pair.config;
    config.max_keypoints = 0;
    require(v0_prepare(pair.a.image, pair.b.image, config, ws) == ErrorCode::InvalidConfig,
            "unset keypoint cap");
    require(v0_prepare(pair.a.image, pair.b.image, pair.config, ws) == ErrorCode::Success, "prepare");
    require(ws.gray_a.width == kWidth && ws.gray_a.height == kHeight && ws.gray_a.channels == 1 &&
                ws.gray_a.stride == static_cast<std::size_t>(kWidth) * sizeof(float),
            "packed gray image A");
    require(ws.keypoints_a.capacity() >= 2000 && ws.descriptors_b.capacity() >= 2000,
            "feature vectors reserved");
    fail_allocations = true;
    V0Workspace starved;
    const ErrorCode status = v0_prepare(pair.a.image, pair.b.image, pair.config, starved);
    fail_allocations = false;
    require(status == ErrorCode::AllocationFailed, "allocation failure reported");
}

void test_stage_names() {
    require(std::string(stage_name(Stage::Preprocess)) == "S1 preprocess", "S1 name");
    require(std::string(stage_name(Stage::WarpBlend)) == "S6 warp_blend", "S6 name");
}

}  // namespace

int main() {
    try {
        test_translated_pair();
        test_repeated_runs_are_identical();
        test_reports_failing_stage();
        test_prepare_errors();
        test_stage_names();
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " assertions: " << error.what() << '\n';
        return 1;
    }
    std::cout << "PASS: " << checks << " assertions for the V0 pipeline S1-S6" << '\n';
    return 0;
}
