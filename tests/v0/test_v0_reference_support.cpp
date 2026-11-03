// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// Host checks of the helpers GPU stage tests rely on: a comparator that misses a
// difference would let a wrong kernel pass.

#include "support/gpu_compare.h"
#include "support/v0_reference.h"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace panorama;
using namespace gpu_test;

namespace {

int checks = 0;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}

void require_mentions(const std::string& text, const std::string& part) {
    require(text.find(part) != std::string::npos, "expected '" + part + "' in '" + text + "'");
}

std::vector<Keypoint> sample_keypoints() {
    std::vector<Keypoint> keypoints(3);
    for (std::size_t i = 0; i < keypoints.size(); ++i) {
        keypoints[i].x = 10.0f + static_cast<float>(i);
        keypoints[i].y = 20.0f;
        keypoints[i].score = 1.5f;
    }
    return keypoints;
}

void test_keypoint_comparison() {
    const std::vector<Keypoint> expected = sample_keypoints();
    require(keypoint_mismatch(expected, expected).empty(), "identical keypoints");

    std::vector<Keypoint> changed = expected;
    changed.pop_back();
    require_mentions(keypoint_mismatch(expected, changed), "size");

    changed = expected;
    changed[1].score = std::nextafter(changed[1].score, 2.0f);
    require_mentions(keypoint_mismatch(expected, changed), "[1].score");

    changed = expected;
    changed[2].x = 99.0f;
    changed[2].y = 99.0f;
    require_mentions(keypoint_mismatch(expected, changed), "[2].x");

    changed = expected;
    changed[0].angle = -0.0f;
    require_mentions(keypoint_mismatch(expected, changed), "[0].angle");

    changed = expected;
    std::swap(changed[0], changed[1]);
    require_mentions(keypoint_mismatch(expected, changed), "[0].x");
}

void test_descriptor_comparison() {
    std::vector<Descriptor> expected(2);
    expected[1].data[7] = 0x80000000u;
    require(descriptor_mismatch(expected, expected).empty(), "identical descriptors");

    std::vector<Descriptor> changed = expected;
    changed[1].data[7] = 0u;
    require_mentions(descriptor_mismatch(expected, changed), "[1].data[7]");

    changed = expected;
    changed.resize(1);
    require_mentions(descriptor_mismatch(expected, changed), "size");
}

void test_float_array_comparison() {
    const std::vector<float> expected = {0.25f, 0.5f};
    std::vector<float> changed = expected;
    changed[1] = std::nextafter(changed[1], 1.0f);
    require_mentions(float_array_mismatch(expected, changed), "[1]");
    require(float_array_mismatch(expected, changed, 1e-5f).empty(), "inside tolerance");

    changed[1] = 0.6f;
    require_mentions(float_array_mismatch(expected, changed, 1e-5f), "[1]");

    changed[1] = std::numeric_limits<float>::quiet_NaN();
    require_mentions(float_array_mismatch(expected, changed, 1e-5f), "[1]");

    changed.pop_back();
    require_mentions(float_array_mismatch(expected, changed), "size");
}

void test_v0_reference() {
    RgbImage image = make_test_image(160, 120, 16);
    RgbImage same = make_test_image(160, 120, 16);
    require(image.bytes == same.bytes, "seeded test image is reproducible");
    require(image.bytes != make_test_image(160, 120, 17).bytes, "seed changes the image");

    Config config;
    require(make_v0_config(image.width, image.height, config) == ErrorCode::Success, "config");

    V0Features first, second;
    require(compute_v0_features(image.view(), config, first) == ErrorCode::Success, "V0 S1 to S3");
    require(compute_v0_features(same.view(), config, second) == ErrorCode::Success, "V0 again");
    require(first.gray_pixels.size() == 160u * 120u, "gray size");
    require(!first.detected.empty(), "test image has corners");
    require(first.detected.size() <= static_cast<std::size_t>(config.max_keypoints), "S2 limit");
    require(first.keypoints.size() == first.descriptors.size(), "S3 pairing");
    require(first.keypoints.size() == first.detected.size(), "S2 border keeps every keypoint");
    require(float_array_mismatch(first.gray_pixels, second.gray_pixels).empty(), "gray repeats");
    require(keypoint_mismatch(first.detected, second.detected).empty(), "S2 repeats");
    require(descriptor_mismatch(first.descriptors, second.descriptors).empty(), "S3 repeats");

    Image broken = image.view();
    broken.channels = 1;
    V0Features failed;
    require(compute_v0_features(broken, config, failed) == ErrorCode::InvalidImage, "error is returned");
}

}  // namespace

int main() {
    try {
        test_keypoint_comparison();
        test_descriptor_comparison();
        test_float_array_comparison();
        test_v0_reference();
        std::cout << "PASS reference support: " << checks << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
