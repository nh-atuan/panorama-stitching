// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// Dev tool for the S2/S3 quality evidence, outside any timed region.
// Runs S1 -> S2 -> S3 on a left/right pair, then S4 and S5 of the group, and prints one line:
//   width,height,keypoints_left,keypoints_right,matches,inliers,status
// It also writes <prefix>_left.png and <prefix>_right.png: the S1 gray image with every
// keypoint drawn as a red cross (5 px arms) and the strongest 50 drawn in yellow.
// Usage: tool_export_keypoints <left_image> <right_image> <output_prefix> [threshold max_keypoints]

#include "v0/v0_preprocess.h"
#include "v0/v0_detect.h"
#include "v0/v0_describe.h"
#include "v0/v0_match.h"
#include "v0/v0_homography.h"
#include "common/feature_support.h"
#include "common/stb_image.h"
#include "common/stb_image_write.h"
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace panorama;

namespace {

struct Side {
    std::vector<float> gray;
    std::vector<Keypoint> keypoints;
    std::vector<Descriptor> descriptors;
    std::int32_t width = 0;
    std::int32_t height = 0;
};

bool extract(const char* path, const Config& config, Side& side) {
    int w = 0, h = 0, channels = 0;
    std::uint8_t* pixels = stbi_load(path, &w, &h, &channels, 3);
    if (!pixels) {
        std::cerr << "Cannot read " << path << '\n';
        return false;
    }
    Image rgb;
    rgb.data = pixels; rgb.width = w; rgb.height = h; rgb.channels = 3;
    rgb.stride = static_cast<std::size_t>(w) * 3;
    side.width = w;
    side.height = h;
    side.gray.assign(static_cast<std::size_t>(w) * h, 0.0f);
    GrayImage gray;
    gray.data = side.gray.data(); gray.width = w; gray.height = h; gray.channels = 1;
    gray.stride = static_cast<std::size_t>(w) * sizeof(float);
    ErrorCode status = v0_preprocess(rgb, gray, config);
    stbi_image_free(pixels);
    if (status == ErrorCode::Success) status = v0_detect(gray, side.keypoints, config);
    if (status == ErrorCode::Success) {
        status = v0_describe(gray, side.keypoints, side.descriptors, config);
    }
    if (status != ErrorCode::Success) {
        std::cerr << path << ": stage error " << static_cast<unsigned>(status) << '\n';
        return false;
    }
    return true;
}

void cross(std::vector<std::uint8_t>& rgb, std::int32_t w, std::int32_t h, std::int32_t x,
           std::int32_t y, std::uint8_t r, std::uint8_t g) {
    for (std::int32_t d = -5; d <= 5; ++d) {
        const std::int32_t px[2] = {x + d, x};
        const std::int32_t py[2] = {y, y + d};
        for (int i = 0; i < 2; ++i) {
            if (px[i] < 0 || py[i] < 0 || px[i] >= w || py[i] >= h) continue;
            std::uint8_t* p = rgb.data() + (static_cast<std::size_t>(py[i]) * w + px[i]) * 3;
            p[0] = r; p[1] = g; p[2] = 0;
        }
    }
}

bool write_overlay(const std::string& path, const Side& side) {
    std::vector<std::uint8_t> rgb(side.gray.size() * 3);
    for (std::size_t i = 0; i < side.gray.size(); ++i) {
        const std::uint8_t v = static_cast<std::uint8_t>(std::floor(side.gray[i] * 255.0f + 0.5f));
        rgb[3 * i] = rgb[3 * i + 1] = rgb[3 * i + 2] = v;
    }
    // Keypoints are sorted by score, so the first 50 are the strongest.
    for (std::size_t i = side.keypoints.size(); i-- > 0;) {
        const bool strong = i < 50;
        cross(rgb, side.width, side.height, static_cast<std::int32_t>(side.keypoints[i].x),
              static_cast<std::int32_t>(side.keypoints[i].y), 255, strong ? 255 : 0);
    }
    return stbi_write_png(path.c_str(), side.width, side.height, 3, rgb.data(), side.width * 3) != 0;
}

template <typename T>
FeatureView<T> view(const std::vector<T>& values) {
    return FeatureView<T>(values.data(), static_cast<std::int32_t>(values.size()), values.size());
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4 && argc != 6) {
        std::cerr << "Usage: tool_export_keypoints <left_image> <right_image> <output_prefix>"
                     " [threshold max_keypoints]\n";
        return 2;
    }
    Config config;
    config.gaussian_sigma = 1.0f;
    config.gaussian_radius = 3;
    config.fast_threshold = argc == 6 ? static_cast<float>(std::atof(argv[4])) : 0.05f;
    config.max_keypoints = argc == 6 ? std::atoi(argv[5]) : 2000;

    Side left;
    Side right;
    if (!extract(argv[1], config, left) || !extract(argv[2], config, right)) return 1;
    const std::string prefix = argv[3];
    if (!write_overlay(prefix + "_left.png", left) || !write_overlay(prefix + "_right.png", right)) {
        std::cerr << "Cannot write overlays\n";
        return 1;
    }

    std::vector<Match> matches;
    Homography h;
    HomographyReport report;
    ErrorCode status = configure_v0_features(config, left.width, left.height);
    if (status == ErrorCode::Success) {
        status = v0_match(view(left.descriptors), view(right.descriptors), matches, config);
    }
    if (status == ErrorCode::Success) {
        status = v0_homography(view(left.keypoints), view(right.keypoints), view(matches), h, config,
                               &report);
    }
    std::cout << "width,height,keypoints_left,keypoints_right,matches,inliers,status\n"
              << left.width << ',' << left.height << ',' << left.keypoints.size() << ','
              << right.keypoints.size() << ',' << matches.size() << ','
              << (report.success ? report.final_inliers : 0) << ','
              << static_cast<unsigned>(status) << '\n';
    return 0;
}
