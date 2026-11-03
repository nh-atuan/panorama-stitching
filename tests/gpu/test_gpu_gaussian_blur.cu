// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// V1 separable blur against gaussian_blur_in_place of V0: bit-exact output, padding and
// source left untouched, and the same error codes for bad calls.

#include "gpu/s45_test_support.cuh"
#include "support/gpu_compare.h"
#include "common/gaussian_blur.h"
#include "v1/common/v1_gaussian_blur.h"
#include <random>

using namespace panorama;
using namespace gpu_test;

namespace {

constexpr float kPadding = -7.0f;

// Host float image with `pad` floats of padding per row, filled with kPadding.
struct HostGray {
    std::int32_t width, height, pitch;
    std::vector<float> values;
    HostGray(std::int32_t w, std::int32_t h, std::int32_t pad)
        : width(w), height(h), pitch(w + pad), values(static_cast<std::size_t>(w + pad) * h, kPadding) {}
    float& at(std::int32_t x, std::int32_t y) { return values[static_cast<std::size_t>(y) * pitch + x]; }
    GrayImage view(float* data) const {
        GrayImage image;
        image.data = data;
        image.stride = static_cast<std::size_t>(pitch) * sizeof(float);
        image.width = width;
        image.height = height;
        image.channels = 1;
        return image;
    }
    std::vector<float> pixels() const {
        std::vector<float> packed;
        for (std::int32_t y = 0; y < height; ++y) {
            const float* row = values.data() + static_cast<std::size_t>(y) * pitch;
            packed.insert(packed.end(), row, row + width);
        }
        return packed;
    }
    bool padding_intact() const {
        for (std::int32_t y = 0; y < height; ++y) {
            for (std::int32_t x = width; x < pitch; ++x) {
                if (float_bits(values[static_cast<std::size_t>(y) * pitch + x]) != float_bits(kPadding)) return false;
            }
        }
        return true;
    }
};

HostGray random_image(std::int32_t w, std::int32_t h, std::int32_t pad, std::uint32_t seed) {
    HostGray image(w, h, pad);
    std::mt19937 random(seed);
    std::uniform_real_distribution<float> value(0.0f, 1.0f);
    for (std::int32_t y = 0; y < h; ++y) {
        for (std::int32_t x = 0; x < w; ++x) image.at(x, y) = value(random);
    }
    return image;
}

HostGray v0_blur(HostGray image, const V1GaussianWeights& weights) {
    std::vector<float> temp(static_cast<std::size_t>(image.width) * image.height);
    GrayImage view = image.view(image.values.data());
    gaussian_blur_in_place(view, temp.data(), weights.values, weights.radius);
    return image;
}

V1GaussianWeights make_weights(float sigma, std::int32_t radius) {
    V1GaussianWeights weights;
    require(v1_make_gaussian_weights(sigma, radius, weights) == ErrorCode::Success, "weights");
    return weights;
}

// Runs V1 with separate source and destination buffers, or in place when `in_place`.
void compare(const HostGray& input, std::int32_t dst_pad, const V1GaussianWeights& weights, bool in_place) {
    const HostGray expected = v0_blur(input, weights);
    HostGray output(input.width, input.height, in_place ? input.pitch - input.width : dst_pad);
    DeviceBuffer<float> src(input.values.size()), dst(output.values.size());
    DeviceBuffer<float> temp(static_cast<std::size_t>(input.width) * input.height);
    src.upload(input.values);
    dst.upload(output.values);
    const GrayImage src_view = input.view(src.data);
    const GrayImage dst_view = in_place ? src_view : output.view(dst.data);
    Stream stream;
    require(v1_gaussian_blur(src_view, dst_view, temp.data, weights, stream.value) == ErrorCode::Success,
            "enqueue blur");
    stream.wait();
    output.values = (in_place ? src : dst).read(output.values.size());
    const std::string message = float_array_mismatch(expected.pixels(), output.pixels());
    require(message.empty(), "blur " + std::to_string(input.width) + "x" + std::to_string(input.height) +
                                 " r=" + std::to_string(weights.radius) + ": " + message);
    require(output.padding_intact(), "destination padding untouched");
    if (!in_place) {
        const std::string source = float_array_mismatch(input.values, src.read(input.values.size()));
        require(source.empty(), "source untouched: " + source);
    }
}

void test_matches_v0() {
    const float sigmas[] = {1.0f, 2.0f, 8.0f};
    const std::int32_t radii[] = {3, 4, 16};
    const std::int32_t sizes[][2] = {{1, 1}, {3, 2}, {2, 40}, {37, 29}, {64, 48}, {257, 131}};
    std::uint32_t seed = 16;
    for (int p = 0; p < 3; ++p) {
        const V1GaussianWeights weights = make_weights(sigmas[p], radii[p]);
        for (const auto& size : sizes) {
            const HostGray input = random_image(size[0], size[1], 3, seed++);
            compare(input, 5, weights, false);
            compare(input, 0, weights, true);
        }
    }
}

void test_constant_image_stays_constant() {
    HostGray input(45, 33, 0);
    for (float& v : input.values) v = 0.375f;
    compare(input, 0, make_weights(1.0f, 3), false);
}

void test_bad_calls() {
    const HostGray input = random_image(16, 8, 0, 3);
    DeviceBuffer<float> src(input.values.size()), temp(input.values.size());
    const GrayImage view = input.view(src.data);
    Stream stream;
    const V1GaussianWeights good = make_weights(1.0f, 3);

    V1GaussianWeights weights = good;
    require(v1_make_gaussian_weights(1.0f, 0, weights) == ErrorCode::InvalidConfig, "radius 0 weights");
    require(v1_make_gaussian_weights(1.0f, 17, weights) == ErrorCode::InvalidConfig, "radius 17 weights");
    require(weights.radius == good.radius, "weights unchanged on error");
    weights.radius = 0;
    require(v1_gaussian_blur(view, view, temp.data, weights, stream.value) == ErrorCode::InvalidConfig,
            "radius 0");
    weights.radius = kMaxGaussianRadius + 1;
    require(v1_gaussian_blur(view, view, temp.data, weights, stream.value) == ErrorCode::InvalidConfig,
            "radius 17");

    GrayImage bad = view;
    bad.channels = 3;
    require(v1_gaussian_blur(bad, view, temp.data, good, stream.value) == ErrorCode::InvalidImage, "channels");
    bad = view;
    bad.width = 15;
    require(v1_gaussian_blur(view, bad, temp.data, good, stream.value) == ErrorCode::InvalidImage, "size");
    bad = view;
    bad.stride = 16;
    require(v1_gaussian_blur(view, bad, temp.data, good, stream.value) == ErrorCode::InvalidImage,
            "stride in elements");
    bad = view;
    bad.data = nullptr;
    require(v1_gaussian_blur(bad, view, temp.data, good, stream.value) == ErrorCode::InvalidImage, "null");
    require(v1_gaussian_blur(view, view, nullptr, good, stream.value) == ErrorCode::InvalidArgument, "temp");
    stream.wait();
}

}  // namespace

int main() {
    try {
        print_gpu();
        test_matches_v0();
        test_constant_image_stays_constant();
        test_bad_calls();
        std::cout << "PASS GPU blur: " << checks() << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
