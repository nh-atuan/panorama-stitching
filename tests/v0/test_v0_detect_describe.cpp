// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// Integration on a synthetic pair: S1 -> S2 -> S3 with the group's S4 and S5 on main.
// B is A translated by an integer offset, so every correct match satisfies pA = pB + offset.

#include "v0/v0_preprocess.h"
#include "v0/v0_detect.h"
#include "v0/v0_describe.h"
#include "v0/v0_match.h"
#include "v0/v0_homography.h"
#include "common/feature_support.h"
#include "support/feature_test_support.h"
#include <cmath>

using namespace panorama;

namespace {

const std::int32_t kWidth = 480;
const std::int32_t kHeight = 320;
const std::int32_t kShiftX = 37;  // B(x, y) = A(x + kShiftX, y + kShiftY)
const std::int32_t kShiftY = -11;

struct RgbScene {
    std::vector<std::uint8_t> pixels;
    Image image;
    RgbScene() : pixels(static_cast<std::size_t>(kWidth) * kHeight * 3, 128) {
        image.data = pixels.data();
        image.width = kWidth;
        image.height = kHeight;
        image.channels = 3;
        image.stride = static_cast<std::size_t>(kWidth) * 3;
    }
    std::uint8_t* at(std::int32_t x, std::int32_t y) {
        return pixels.data() + (static_cast<std::size_t>(y) * kWidth + x) * 3;
    }
};

// A wider scene from which A and B are cut, so both images are fully textured.
struct World {
    std::int32_t width;
    std::int32_t height;
    std::vector<std::uint8_t> rgb;
    World() : width(kWidth + 80), height(kHeight + 40), rgb(static_cast<std::size_t>(width) * height * 3) {
        TestRandom random(2026);
        for (std::size_t i = 0; i < rgb.size(); ++i) rgb[i] = 100;
        for (int r = 0; r < 900; ++r) {
            const std::int32_t x0 = random.below(width);
            const std::int32_t y0 = random.below(height);
            const std::int32_t w = 4 + random.below(30);
            const std::int32_t h = 4 + random.below(30);
            const std::uint8_t c[3] = {static_cast<std::uint8_t>(random.below(256)),
                                       static_cast<std::uint8_t>(random.below(256)),
                                       static_cast<std::uint8_t>(random.below(256))};
            for (std::int32_t y = y0; y < y0 + h && y < height; ++y)
                for (std::int32_t x = x0; x < x0 + w && x < width; ++x)
                    for (int ch = 0; ch < 3; ++ch) rgb[(static_cast<std::size_t>(y) * width + x) * 3 + ch] = c[ch];
        }
    }
    void cut(RgbScene& scene, std::int32_t left, std::int32_t top) const {
        for (std::int32_t y = 0; y < kHeight; ++y)
            for (std::int32_t x = 0; x < kWidth; ++x)
                for (int ch = 0; ch < 3; ++ch)
                    scene.at(x, y)[ch] = rgb[(static_cast<std::size_t>(y + top) * width + (x + left)) * 3 + ch];
    }
};

template <typename T>
FeatureView<T> view(const std::vector<T>& values) {
    return FeatureView<T>(values.data(), static_cast<std::int32_t>(values.size()), values.size());
}

struct Features {
    std::vector<float> gray;
    std::vector<Keypoint> keypoints;
    std::vector<Descriptor> descriptors;
};

void extract(const Image& rgb, const Config& config, Features& out) {
    out.gray.assign(static_cast<std::size_t>(kWidth) * kHeight, 0.0f);
    GrayImage gray;
    gray.data = out.gray.data();
    gray.width = kWidth;
    gray.height = kHeight;
    gray.channels = 1;
    gray.stride = static_cast<std::size_t>(kWidth) * sizeof(float);
    require(v0_preprocess(rgb, gray, config) == ErrorCode::Success, "S1");
    require(v0_detect(gray, out.keypoints, config) == ErrorCode::Success, "S2");
    const std::size_t detected = out.keypoints.size();
    require(v0_describe(gray, out.keypoints, out.descriptors, config) == ErrorCode::Success, "S3");
    require(out.keypoints.size() == detected && out.descriptors.size() == detected,
            "S3 keeps every S2 keypoint because S2 respects the patch border");
}

void test_translated_pair() {
    World world;
    RgbScene a;
    RgbScene b;
    const std::int32_t left = 20;
    const std::int32_t top = 25;
    world.cut(a, left, top);
    world.cut(b, left + kShiftX, top + kShiftY);

    Config config;
    config.gaussian_sigma = 1.0f;
    config.gaussian_radius = 3;
    config.fast_threshold = 0.05f;
    config.max_keypoints = 2000;
    require(configure_v0_features(config, kWidth, kHeight) == ErrorCode::Success, "S4/S5 config");

    Features fa;
    Features fb;
    extract(a.image, config, fa);
    extract(b.image, config, fb);
    require(fa.keypoints.size() > 300 && fb.keypoints.size() > 300, "both images have many keypoints");

    std::vector<Match> matches;
    require(v0_match(view(fa.descriptors), view(fb.descriptors), matches, config) == ErrorCode::Success,
            "S4");
    std::size_t exact = 0;
    for (const Match& m : matches) {
        const Keypoint& pa = fa.keypoints[m.indexA];
        const Keypoint& pb = fb.keypoints[m.indexB];
        if (pa.x == pb.x + kShiftX && pa.y == pb.y + kShiftY) ++exact;
    }
    require(matches.size() > 100, "S4 keeps many matches");
    require(exact * 10 >= matches.size() * 9, "at least 90% of matches follow the translation");

    Homography h;
    require(v0_homography(view(fa.keypoints), view(fb.keypoints), view(matches), h, config) ==
                ErrorCode::Success,
            "S5");
    const float corners[4][2] = {{0, 0}, {kWidth - 1.0f, 0}, {0, kHeight - 1.0f},
                                 {kWidth - 1.0f, kHeight - 1.0f}};
    for (const auto& c : corners) {
        const double u = h.data[0] * c[0] + h.data[1] * c[1] + h.data[2];
        const double v = h.data[3] * c[0] + h.data[4] * c[1] + h.data[5];
        const double w = h.data[6] * c[0] + h.data[7] * c[1] + h.data[8];
        require(std::fabs(u / w - (c[0] + kShiftX)) < 0.1 && std::fabs(v / w - (c[1] + kShiftY)) < 0.1,
                "H maps B corners onto A within 0.1 px");
    }
    std::cout << "integration: keypoints A=" << fa.keypoints.size() << " B=" << fb.keypoints.size()
              << " matches=" << matches.size() << " exact=" << exact << '\n';
}

}  // namespace

int main() {
    try {
        test_translated_pair();
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " assertions: " << error.what() << '\n';
        return 1;
    }
    std::cout << "PASS: " << checks << " assertions for S1-S5 integration on a translated pair" << '\n';
    return 0;
}
