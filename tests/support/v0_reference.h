// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// V0 intermediate results used as input and as expected output of GPU stage tests.
// Host code only. Does not include feature_test_support.h: that header replaces the
// global operator new for CPU OOM tests.

#ifndef GROUP16_V0_REFERENCE_H
#define GROUP16_V0_REFERENCE_H

#include "common/common.h"
#include "common/stb_image.h"
#include "common/v0_config.h"
#include "v0/v0_describe.h"
#include "v0/v0_detect.h"
#include "v0/v0_preprocess.h"
#include <cstddef>
#include <cstdint>
#include <random>
#include <vector>

namespace gpu_test {

// Packed RGB image; view() stays valid while this object is alive and unchanged.
struct RgbImage {
    std::vector<std::uint8_t> bytes;
    std::int32_t width = 0;
    std::int32_t height = 0;

    panorama::Image view() {
        panorama::Image image;
        image.data = bytes.data();
        image.stride = static_cast<std::size_t>(width) * 3;
        image.width = width;
        image.height = height;
        image.channels = 3;
        return image;
    }
};

// Rectangles on a dark background, seeded, so FAST finds corners at any size.
inline RgbImage make_test_image(std::int32_t width, std::int32_t height, std::uint32_t seed) {
    RgbImage image;
    image.width = width;
    image.height = height;
    image.bytes.assign(static_cast<std::size_t>(width) * height * 3, 16);
    std::mt19937 random(seed);
    const std::int32_t rectangles = 8 + width * height / 2000;
    for (std::int32_t i = 0; i < rectangles; ++i) {
        const std::int32_t x0 = static_cast<std::int32_t>(random() % static_cast<std::uint32_t>(width));
        const std::int32_t y0 = static_cast<std::int32_t>(random() % static_cast<std::uint32_t>(height));
        const std::int32_t x1 = x0 + 4 + static_cast<std::int32_t>(random() % 24);
        const std::int32_t y1 = y0 + 4 + static_cast<std::int32_t>(random() % 24);
        const std::uint8_t level = static_cast<std::uint8_t>(random() % 256);
        for (std::int32_t y = y0; y < y1 && y < height; ++y) {
            for (std::int32_t x = x0; x < x1 && x < width; ++x) {
                const std::size_t pixel = (static_cast<std::size_t>(y) * width + x) * 3;
                image.bytes[pixel] = image.bytes[pixel + 1] = image.bytes[pixel + 2] = level;
            }
        }
    }
    return image;
}

// Needs stb_impl in the build. Returns false when the file cannot be decoded.
inline bool load_rgb_image(const char* path, RgbImage& image) {
    int width = 0, height = 0, channels = 0;
    stbi_uc* pixels = stbi_load(path, &width, &height, &channels, 3);
    if (!pixels) return false;
    image.width = width;
    image.height = height;
    image.bytes.assign(pixels, pixels + static_cast<std::size_t>(width) * height * 3);
    stbi_image_free(pixels);
    return true;
}

// Results of V0 S1 to S3 on one image. `detected` is the S2 output before S3 compaction.
struct V0Features {
    std::vector<float> gray_pixels;
    std::int32_t width = 0;
    std::int32_t height = 0;
    std::vector<panorama::Keypoint> detected;
    std::vector<panorama::Keypoint> keypoints;
    std::vector<panorama::Descriptor> descriptors;

    panorama::GrayImage gray() {
        panorama::GrayImage image;
        image.data = gray_pixels.data();
        image.stride = static_cast<std::size_t>(width) * sizeof(float);
        image.width = width;
        image.height = height;
        image.channels = 1;
        return image;
    }
};

inline panorama::ErrorCode compute_v0_features(const panorama::Image& input, const panorama::Config& config,
                                               V0Features& features) {
    using panorama::ErrorCode;
    features.width = input.width;
    features.height = input.height;
    features.gray_pixels.assign(static_cast<std::size_t>(input.width) * input.height, 0.0f);
    panorama::GrayImage gray = features.gray();
    ErrorCode status = panorama::v0_preprocess(input, gray, config);
    if (status != ErrorCode::Success) return status;
    status = panorama::v0_detect(gray, features.detected, config);
    if (status != ErrorCode::Success) return status;
    features.keypoints = features.detected;
    return panorama::v0_describe(gray, features.keypoints, features.descriptors, config);
}

}  // namespace gpu_test

#endif  // GROUP16_V0_REFERENCE_H
