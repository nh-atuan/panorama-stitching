// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// S1 of V1 against v0_preprocess (S1 design, sections 6.4 and 7): max absolute difference
// <= 1e-5 (measured value is printed), padding untouched, same error codes, outputs left
// untouched on an error. Optional arguments `<left> <right>` run the same check on real images.

#include "gpu/s45_test_support.cuh"
#include "support/gpu_compare.h"
#include "support/v0_reference.h"
#include "v0/v0_preprocess.h"
#include "v1/s1/v1_preprocess.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <random>

using namespace panorama;
using namespace gpu_test;

namespace {

constexpr float kTolerance = 1e-5f;
constexpr float kGrayPadding = -7.0f;
constexpr std::uint8_t kRgbPadding = 0xAB;

double g_max_diff = 0.0;
std::size_t g_pixels = 0, g_exact = 0;

Config make_config(float sigma, std::int32_t radius) {
    Config config;
    config.gaussian_sigma = sigma;
    config.gaussian_radius = radius;
    return config;
}

RgbImage random_rgb(std::int32_t w, std::int32_t h, std::uint32_t seed) {
    RgbImage image;
    image.width = w;
    image.height = h;
    image.bytes.resize(static_cast<std::size_t>(w) * h * 3);
    std::mt19937 random(seed);
    for (std::uint8_t& v : image.bytes) v = static_cast<std::uint8_t>(random() & 0xFF);
    return image;
}

RgbImage constant_rgb(std::int32_t w, std::int32_t h, std::uint8_t r, std::uint8_t g, std::uint8_t b) {
    RgbImage image;
    image.width = w;
    image.height = h;
    for (std::int32_t i = 0; i < w * h; ++i) {
        image.bytes.push_back(r);
        image.bytes.push_back(g);
        image.bytes.push_back(b);
    }
    return image;
}

// Packed V0 result for one image.
std::vector<float> v0_gray(RgbImage image, const Config& config) {
    std::vector<float> gray(static_cast<std::size_t>(image.width) * image.height, 0.0f);
    GrayImage view;
    view.data = gray.data();
    view.stride = static_cast<std::size_t>(image.width) * sizeof(float);
    view.width = image.width;
    view.height = image.height;
    view.channels = 1;
    require(v0_preprocess(image.view(), view, config) == ErrorCode::Success, "V0 preprocess");
    return gray;
}

// RGB rows with `pad` bytes of kRgbPadding after each row.
std::vector<std::uint8_t> padded_rgb(const RgbImage& image, std::int32_t pad) {
    const std::size_t row = static_cast<std::size_t>(image.width) * 3;
    std::vector<std::uint8_t> bytes((row + pad) * image.height, kRgbPadding);
    for (std::int32_t y = 0; y < image.height; ++y) {
        std::copy(image.bytes.begin() + y * row, image.bytes.begin() + (y + 1) * row, bytes.begin() + y * (row + pad));
    }
    return bytes;
}

// Device copies of A and B with padded rows, and a workspace pointing at them.
struct Fixture {
    RgbImage a, b;
    std::int32_t rgb_pad, gray_pad;
    std::vector<std::uint8_t> host_rgb_a, host_rgb_b;
    std::vector<float> host_gray_a, host_gray_b;
    DeviceBuffer<std::uint8_t> rgb_a, rgb_b;
    DeviceBuffer<float> gray_a, gray_b;
    DeviceBuffer<std::uint8_t> scratch;
    DeviceWorkspace w;
    Stream stream;

    Fixture(const RgbImage& left, const RgbImage& right, std::int32_t rgb_padding, std::int32_t gray_padding)
        : a(left), b(right), rgb_pad(rgb_padding), gray_pad(gray_padding),
          host_rgb_a(padded_rgb(a, rgb_pad)), host_rgb_b(padded_rgb(b, rgb_pad)),
          host_gray_a(static_cast<std::size_t>(a.width + gray_pad) * a.height, kGrayPadding),
          host_gray_b(static_cast<std::size_t>(b.width + gray_pad) * b.height, kGrayPadding),
          rgb_a(host_rgb_a.size()), rgb_b(host_rgb_b.size()), gray_a(host_gray_a.size()),
          gray_b(host_gray_b.size()),
          scratch(std::max(v1_preprocess_scratch_bytes(a.width, a.height),
                           v1_preprocess_scratch_bytes(b.width, b.height))) {
        rgb_a.upload(host_rgb_a);
        rgb_b.upload(host_rgb_b);
        gray_a.upload(host_gray_a);
        gray_b.upload(host_gray_b);
        w.d_imageA = rgb_a.data;
        w.d_imageB = rgb_b.data;
        w.d_grayA = gray_a.data;
        w.d_grayB = gray_b.data;
        w.imageA = rgb_view(rgb_a.data, a);
        w.imageB = rgb_view(rgb_b.data, b);
        w.grayA = gray_view(gray_a.data, a);
        w.grayB = gray_view(gray_b.data, b);
        w.d_scratch = scratch.data;
        w.scratch_capacity_bytes = scratch.count;
    }
    Image rgb_view(std::uint8_t* data, const RgbImage& image) const {
        Image view;
        view.data = data;
        view.stride = static_cast<std::size_t>(image.width) * 3 + rgb_pad;
        view.width = image.width;
        view.height = image.height;
        view.channels = 3;
        return view;
    }
    GrayImage gray_view(float* data, const RgbImage& image) const {
        GrayImage view;
        view.data = data;
        view.stride = static_cast<std::size_t>(image.width + gray_pad) * sizeof(float);
        view.width = image.width;
        view.height = image.height;
        view.channels = 1;
        return view;
    }
    ErrorCode run(const Config& config) {
        const ErrorCode status = v1_preprocess(w, config, stream.value);
        stream.wait();
        return status;
    }
    // Raw Device gray buffer, padding included.
    std::vector<float> raw(bool image_a) const {
        return image_a ? gray_a.read(host_gray_a.size()) : gray_b.read(host_gray_b.size());
    }
    std::vector<float> packed(bool image_a) const {
        const RgbImage& image = image_a ? a : b;
        const std::vector<float> values = raw(image_a);
        const std::size_t pitch = static_cast<std::size_t>(image.width + gray_pad);
        std::vector<float> out;
        for (std::int32_t y = 0; y < image.height; ++y) {
            out.insert(out.end(), values.begin() + y * pitch, values.begin() + y * pitch + image.width);
        }
        return out;
    }
    bool gray_padding_intact(bool image_a) const {
        const RgbImage& image = image_a ? a : b;
        const std::vector<float> values = raw(image_a);
        const std::size_t pitch = static_cast<std::size_t>(image.width + gray_pad);
        for (std::int32_t y = 0; y < image.height; ++y) {
            for (std::size_t x = image.width; x < pitch; ++x) {
                if (float_bits(values[y * pitch + x]) != float_bits(kGrayPadding)) return false;
            }
        }
        return true;
    }
    bool rgb_untouched() const {
        return rgb_a.read(host_rgb_a.size()) == host_rgb_a && rgb_b.read(host_rgb_b.size()) == host_rgb_b;
    }
    bool gray_untouched() const { return raw(true) == host_gray_a && raw(false) == host_gray_b; }
};

double max_abs_diff(const std::vector<float>& expected, const std::vector<float>& actual) {
    double diff = 0.0;
    for (std::size_t i = 0; i < expected.size(); ++i) {
        diff = std::max(diff, std::fabs(static_cast<double>(expected[i]) - actual[i]));
        if (float_bits(expected[i]) == float_bits(actual[i])) ++g_exact;
    }
    g_pixels += expected.size();
    g_max_diff = std::max(g_max_diff, diff);
    return diff;
}

std::string size_name(const RgbImage& image) {
    return std::to_string(image.width) + "x" + std::to_string(image.height);
}

// Runs V1 on (left, right) and requires both outputs within kTolerance of V0.
void compare(const RgbImage& left, const RgbImage& right, const Config& config, std::int32_t rgb_pad,
             std::int32_t gray_pad, const std::string& label) {
    Fixture f(left, right, rgb_pad, gray_pad);
    require(f.run(config) == ErrorCode::Success, label + ": v1_preprocess");
    const std::vector<float> expected[2] = {v0_gray(left, config), v0_gray(right, config)};
    for (int i = 0; i < 2; ++i) {
        const std::vector<float> actual = f.packed(i == 0);
        require(actual.size() == expected[i].size(), label + ": size");
        const double diff = max_abs_diff(expected[i], actual);
        require(diff <= kTolerance, label + (i ? " B " : " A ") + size_name(i ? right : left) +
                                        " r=" + std::to_string(config.gaussian_radius) +
                                        ": max diff " + std::to_string(diff));
        require(f.gray_padding_intact(i == 0), label + ": gray padding untouched");
    }
    require(f.rgb_untouched(), label + ": RGB input untouched");
}

void test_random_images() {
    const Config configs[] = {make_config(1.0f, 3), make_config(0.5f, 1), make_config(2.0f, 4),
                              make_config(8.0f, 16)};
    const std::int32_t sizes[][2] = {{1, 1}, {1, 7}, {7, 1}, {2, 2}, {3, 5}, {33, 9},
                                     {37, 29}, {64, 48}, {257, 131}};
    const std::size_t count = sizeof(sizes) / sizeof(sizes[0]);
    std::uint32_t seed = 16;
    for (const Config& config : configs) {
        for (std::size_t i = 0; i < count; ++i) {
            const std::int32_t* sa = sizes[i];
            const std::int32_t* sb = sizes[(i + 1) % count];
            const RgbImage a = random_rgb(sa[0], sa[1], seed++);
            const RgbImage b = random_rgb(sb[0], sb[1], seed++);
            compare(a, b, config, 0, 0, "random packed");
            compare(a, b, config, 5, 3, "random padded");
        }
    }
}

void test_constant_and_pure_colors() {
    const Config config = make_config(1.0f, 3);
    const std::uint8_t colors[][3] = {{128, 128, 128}, {255, 0, 0}, {0, 255, 0}, {0, 0, 255},
                                      {0, 0, 0}, {255, 255, 255}};
    const float expected[] = {128.0f / 255.0f, 0.299f, 0.587f, 0.114f, 0.0f, 1.0f};
    for (int c = 0; c < 6; ++c) {
        const RgbImage image = constant_rgb(45, 33, colors[c][0], colors[c][1], colors[c][2]);
        compare(image, image, config, 2, 1, "color " + std::to_string(c));
        Fixture f(image, image, 0, 0);
        require(f.run(config) == ErrorCode::Success, "constant run");
        for (float v : f.packed(true)) {
            require(std::fabs(v - expected[c]) <= kTolerance, "constant color value " + std::to_string(c));
        }
    }
}

void test_bright_point() {
    RgbImage image = constant_rgb(21, 17, 0, 0, 0);
    const std::size_t center = (static_cast<std::size_t>(8) * 21 + 10) * 3;
    image.bytes[center] = image.bytes[center + 1] = image.bytes[center + 2] = 255;
    compare(image, image, make_config(1.0f, 3), 0, 0, "bright point");
    compare(image, image, make_config(2.0f, 4), 3, 2, "bright point");
}

void test_repeat_is_bit_identical() {
    const RgbImage a = random_rgb(70, 41, 5), b = random_rgb(41, 70, 6);
    Fixture f(a, b, 1, 1);
    const Config config = make_config(1.0f, 3);
    require(f.run(config) == ErrorCode::Success, "first run");
    const std::vector<float> first_a = f.raw(true), first_b = f.raw(false);
    require(f.run(config) == ErrorCode::Success, "second run");
    require(float_array_mismatch(first_a, f.raw(true)).empty(), "repeat A bit identical");
    require(float_array_mismatch(first_b, f.raw(false)).empty(), "repeat B bit identical");
}

void test_scratch_bytes() {
    require(v1_preprocess_scratch_bytes(3, 4) == 48, "scratch 3x4");
    require(v1_preprocess_scratch_bytes(1, 1) == 4, "scratch 1x1");
    require(v1_preprocess_scratch_bytes(0, 4) == 0, "scratch width 0");
    require(v1_preprocess_scratch_bytes(4, -1) == 0, "scratch height -1");
    const std::int32_t big = std::numeric_limits<std::int32_t>::max();
    const bool overflows = static_cast<unsigned long long>(big) * big >
                           std::numeric_limits<std::size_t>::max() / sizeof(float);
    if (overflows) require(v1_preprocess_scratch_bytes(big, big) == 0, "scratch overflow");
}

// Each bad call must return `code` and leave both gray outputs untouched.
template <class Mutate>
void expect_error(const std::string& label, ErrorCode code, const Config& config, Mutate mutate) {
    Fixture f(random_rgb(16, 8, 3), random_rgb(16, 8, 4), 0, 0);
    mutate(f.w);
    require(f.run(config) == code, label + ": error code");
    require(f.gray_untouched(), label + ": outputs untouched");
}

void test_bad_calls() {
    const Config good = make_config(1.0f, 3);
    expect_error("A channels", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.imageA.channels = 4; });
    expect_error("B null", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.imageB.data = nullptr; });
    expect_error("A stride short", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.imageA.stride = 47; });
    expect_error("gray A width", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.grayA.width = 15; });
    expect_error("gray B channels", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.grayB.channels = 3; });
    expect_error("gray B stride in elements", ErrorCode::InvalidImage, good,
                 [](DeviceWorkspace& w) { w.grayB.stride = 16; });
    expect_error("gray A misaligned", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) {
        w.grayA.data = reinterpret_cast<float*>(reinterpret_cast<unsigned char*>(w.grayA.data) + 2);
    });
    expect_error("width 0", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) {
        w.imageA.width = 0;
        w.grayA.width = 0;
    });
    expect_error("image before config", ErrorCode::InvalidImage, make_config(1.0f, 0),
                 [](DeviceWorkspace& w) { w.imageA.channels = 1; });

    auto none = [](DeviceWorkspace&) {};
    expect_error("sigma NaN", ErrorCode::InvalidConfig, make_config(std::nanf(""), 3), none);
    expect_error("sigma 0", ErrorCode::InvalidConfig, make_config(0.0f, 3), none);
    expect_error("radius 0", ErrorCode::InvalidConfig, make_config(1.0f, 0), none);
    expect_error("radius 17", ErrorCode::InvalidConfig, make_config(1.0f, 17), none);
    expect_error("radius below 2 sigma", ErrorCode::InvalidConfig, make_config(2.0f, 3), none);
    expect_error("config before scratch", ErrorCode::InvalidConfig, make_config(1.0f, 0),
                 [](DeviceWorkspace& w) { w.d_scratch = nullptr; });

    expect_error("scratch null", ErrorCode::InvalidArgument, good, [](DeviceWorkspace& w) { w.d_scratch = nullptr; });
    expect_error("scratch small", ErrorCode::InvalidArgument, good,
                 [](DeviceWorkspace& w) { w.scratch_capacity_bytes -= 1; });
    expect_error("scratch misaligned", ErrorCode::InvalidArgument, good, [](DeviceWorkspace& w) {
        w.d_scratch += 2;
        w.scratch_capacity_bytes -= 2;
    });
}

void test_real_images(const char* left_path, const char* right_path) {
    RgbImage left, right;
    require(load_rgb_image(left_path, left), std::string("load ") + left_path);
    require(load_rgb_image(right_path, right), std::string("load ") + right_path);
    compare(left, right, make_config(1.0f, 3), 0, 0, "real images");
    std::cout << "S1 real images " << size_name(left) << " and " << size_name(right) << ": max diff within "
              << kTolerance << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        print_gpu();
        if (argc != 1 && argc != 3) throw std::runtime_error("usage: gpu_s1 [<left> <right>]");
        test_scratch_bytes();
        test_random_images();
        test_constant_and_pure_colors();
        test_bright_point();
        test_repeat_is_bit_identical();
        test_bad_calls();
        if (argc == 3) test_real_images(argv[1], argv[2]);
        std::cout << "S1 pixels=" << g_pixels << " bit_exact=" << g_exact << " max_abs_diff=" << g_max_diff
                  << " tolerance=" << kTolerance << '\n';
        std::cout << "PASS GPU S1: " << checks() << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
