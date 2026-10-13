// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0_preprocess.h"
#include "gaussian_kernel.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
#include <vector>

// Deterministic allocation failure for S1's temporary buffer, without large allocations.
static bool fail_array_allocation = false;
void* operator new[](std::size_t size) {
    if (fail_array_allocation) throw std::bad_alloc();
    void* result = std::malloc(size ? size : 1);
    if (!result) throw std::bad_alloc();
    return result;
}
void operator delete[](void* pointer) noexcept { std::free(pointer); }

using namespace panorama;
static int checks = 0;
static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}

static const float kSentinel = -7.0f;

// Exact-size allocations so AddressSanitizer sees any out-of-bounds access.
struct RgbFixture {
    std::vector<std::uint8_t> storage;
    Image image;
    RgbFixture(int width, int height, int padding = 0)
        : storage((static_cast<std::size_t>(width) * 3 + padding) * height, 231) {
        image.data = storage.data(); image.width = width; image.height = height;
        image.channels = 3; image.stride = static_cast<std::size_t>(width) * 3 + padding;
    }
    void set(int x, int y, int r, int g, int b) {
        std::uint8_t* p = storage.data() + static_cast<std::size_t>(y) * image.stride + 3 * x;
        p[0] = static_cast<std::uint8_t>(r); p[1] = static_cast<std::uint8_t>(g);
        p[2] = static_cast<std::uint8_t>(b);
    }
    void fill(int r, int g, int b) {
        for (int y = 0; y < image.height; ++y)
            for (int x = 0; x < image.width; ++x) set(x, y, r, g, b);
    }
    void randomize(std::uint32_t seed) {
        std::uint32_t state = seed;
        for (int y = 0; y < image.height; ++y)
            for (int x = 0; x < image.width; ++x) {
                int c[3];
                for (int k = 0; k < 3; ++k) {
                    state = state * 1664525u + 1013904223u;
                    c[k] = static_cast<int>(state >> 24);
                }
                set(x, y, c[0], c[1], c[2]);
            }
    }
};

struct GrayFixture {
    std::vector<float> storage;
    GrayImage image;
    // padding_floats extra floats at the end of each row, filled with a sentinel.
    GrayFixture(int width, int height, int padding_floats = 0)
        : storage((static_cast<std::size_t>(width) + padding_floats) * height, kSentinel) {
        image.data = storage.data(); image.width = width; image.height = height;
        image.channels = 1; image.stride = (static_cast<std::size_t>(width) + padding_floats) * sizeof(float);
    }
    float at(int x, int y) const {
        const unsigned char* base = reinterpret_cast<const unsigned char*>(image.data);
        return reinterpret_cast<const float*>(base + static_cast<std::size_t>(y) * image.stride)[x];
    }
    bool padding_untouched() const {
        const std::size_t row = image.stride / sizeof(float);
        for (int y = 0; y < image.height; ++y)
            for (std::size_t x = image.width; x < row; ++x)
                if (storage[y * row + x] != kSentinel) return false;
        return true;
    }
    bool all_sentinel() const {
        for (float v : storage) if (v != kSentinel) return false;
        return true;
    }
};

static Config settings(float sigma = 1.0f, int radius = 3) {
    Config config;
    config.gaussian_sigma = sigma;
    config.gaussian_radius = radius;
    return config;
}

// Independent reference: direct 2D Gaussian in double with clamped borders.
static std::vector<double> reference_gray(const RgbFixture& in) {
    std::vector<double> gray(static_cast<std::size_t>(in.image.width) * in.image.height);
    for (int y = 0; y < in.image.height; ++y)
        for (int x = 0; x < in.image.width; ++x) {
            const std::uint8_t* p = in.storage.data() + y * in.image.stride + 3 * x;
            gray[static_cast<std::size_t>(y) * in.image.width + x] =
                (0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]) / 255.0;
        }
    return gray;
}

static std::vector<double> kernel_1d(double sigma, int radius) {
    std::vector<double> k(2 * radius + 1);
    double sum = 0;
    for (int i = -radius; i <= radius; ++i) sum += k[i + radius] = std::exp(-double(i * i) / (2 * sigma * sigma));
    for (double& v : k) v /= sum;
    return k;
}

static double reference_blur_at(const std::vector<double>& gray, int width, int height,
                                const std::vector<double>& k, int radius, int x, int y) {
    double sum = 0;
    for (int j = -radius; j <= radius; ++j)
        for (int i = -radius; i <= radius; ++i) {
            const int xx = std::min(std::max(x + i, 0), width - 1);
            const int yy = std::min(std::max(y + j, 0), height - 1);
            sum += k[i + radius] * k[j + radius] * gray[static_cast<std::size_t>(yy) * width + xx];
        }
    return sum;
}

static double max_error_vs_reference(const RgbFixture& in, const GrayFixture& out, double sigma, int radius) {
    const std::vector<double> gray = reference_gray(in);
    const std::vector<double> k = kernel_1d(sigma, radius);
    double worst = 0;
    for (int y = 0; y < in.image.height; ++y)
        for (int x = 0; x < in.image.width; ++x) {
            const double expected = reference_blur_at(gray, in.image.width, in.image.height, k, radius, x, y);
            worst = std::max(worst, std::fabs(expected - out.at(x, y)));
        }
    return worst;
}

static void run_ok(const RgbFixture& in, GrayFixture& out, const Config& config) {
    require(v0_preprocess(in.image, out.image, config) == ErrorCode::Success, "Expected Success");
}

static void expect_error(const Image& in, GrayImage& out, const GrayFixture& watch,
                         const Config& config, ErrorCode expected, const char* message) {
    std::vector<float> before = watch.storage;
    require(v0_preprocess(in, out, config) == expected, message);
    require(before == watch.storage, "Output changed on error");
}

static void test_kernel() {
    for (int radius = 1; radius <= kMaxGaussianRadius; radius += 5) {
        const float sigma = std::min(1.0f, radius / 2.0f);
        std::vector<float> w(2 * radius + 1);
        require(make_gaussian_weights(sigma, radius, w.data()) == ErrorCode::Success, "Kernel failed");
        double sum = 0;
        const std::vector<double> ref = kernel_1d(sigma, radius);
        for (int i = 0; i < 2 * radius + 1; ++i) {
            sum += w[i];
            require(w[i] == w[2 * radius - i], "Kernel not symmetric");
            require(std::fabs(w[i] - ref[i]) < 1e-7, "Kernel differs from formula");
        }
        require(std::fabs(sum - 1.0) < 1e-6, "Kernel does not sum to 1");
    }
    float w[7];
    require(make_gaussian_weights(1.0f, 3, nullptr) == ErrorCode::InvalidArgument, "Null weights");
    require(validate_gaussian_params(1.0f, 3) == ErrorCode::Success, "sigma 1 radius 3");
    require(validate_gaussian_params(1.5f, 3) == ErrorCode::Success, "radius == 2 sigma accepted");
    require(validate_gaussian_params(8.0f, 16) == ErrorCode::Success, "Largest supported kernel");
    require(validate_gaussian_params(1e-3f, 1) == ErrorCode::Success, "Tiny sigma is valid");
    const float nan = std::nanf(""), inf = std::numeric_limits<float>::infinity();
    require(validate_gaussian_params(0.0f, 3) == ErrorCode::InvalidConfig, "sigma 0");
    require(validate_gaussian_params(-1.0f, 3) == ErrorCode::InvalidConfig, "sigma < 0");
    require(validate_gaussian_params(nan, 3) == ErrorCode::InvalidConfig, "sigma NaN");
    require(validate_gaussian_params(inf, 3) == ErrorCode::InvalidConfig, "sigma inf");
    require(validate_gaussian_params(1.0f, 0) == ErrorCode::InvalidConfig, "radius 0");
    require(validate_gaussian_params(1.0f, -3) == ErrorCode::InvalidConfig, "radius < 0");
    require(validate_gaussian_params(1.0f, 17) == ErrorCode::InvalidConfig, "radius 17");
    require(validate_gaussian_params(2.0f, 3) == ErrorCode::InvalidConfig, "radius < 2 sigma");
    require(validate_gaussian_params(1.6f, 3) == ErrorCode::InvalidConfig, "radius < ceil(2 sigma)");
    w[0] = 5.0f;
    require(make_gaussian_weights(2.0f, 3, w) == ErrorCode::InvalidConfig && w[0] == 5.0f, "Wrote on invalid");
}

static void test_constant_and_colors() {
    RgbFixture gray(23, 17);
    gray.fill(128, 128, 128);
    GrayFixture out(23, 17);
    run_ok(gray, out, settings());
    for (int y = 0; y < 17; ++y)
        for (int x = 0; x < 23; ++x)
            require(std::fabs(out.at(x, y) - 128.0f / 255.0f) < 1e-6, "Constant image changed");

    const int colors[3][3] = {{255, 0, 0}, {0, 255, 0}, {0, 0, 255}};
    const float expected[3] = {0.299f, 0.587f, 0.114f};
    for (int c = 0; c < 3; ++c) {
        RgbFixture img(9, 9);
        img.fill(colors[c][0], colors[c][1], colors[c][2]);
        GrayFixture g(9, 9);
        run_ok(img, g, settings());
        for (int y = 0; y < 9; ++y)
            for (int x = 0; x < 9; ++x)
                require(std::fabs(g.at(x, y) - expected[c]) < 1e-6, "Wrong BT.601 weight");
    }
    RgbFixture black(5, 5);
    black.fill(0, 0, 0);
    GrayFixture g0(5, 5);
    run_ok(black, g0, settings());
    require(g0.at(2, 2) == 0.0f, "Black must stay 0");
    RgbFixture white(5, 5);
    white.fill(255, 255, 255);
    GrayFixture g1(5, 5);
    run_ok(white, g1, settings());
    require(std::fabs(g1.at(0, 0) - 1.0f) < 1e-6 && std::fabs(g1.at(4, 4) - 1.0f) < 1e-6, "White must stay 1");
}

static void test_impulse() {
    RgbFixture img(15, 15);
    img.fill(0, 0, 0);
    img.set(7, 7, 1, 1, 1);
    GrayFixture out(15, 15);
    run_ok(img, out, settings());
    const std::vector<double> k = kernel_1d(1.0, 3);
    double total = 0;
    for (int y = 0; y < 15; ++y)
        for (int x = 0; x < 15; ++x) {
            double expected = 0;
            if (std::abs(x - 7) <= 3 && std::abs(y - 7) <= 3) expected = k[x - 7 + 3] * k[y - 7 + 3] / 255.0;
            require(std::fabs(out.at(x, y) - expected) < 1e-6, "Impulse response differs");
            total += out.at(x, y);
        }
    require(std::fabs(total - 1.0 / 255.0) < 1e-6, "Impulse mass not preserved");
    // Mirrored taps use the same weight, so mirror images are bit-identical; x/y symmetry only up to rounding.
    require(out.at(6, 7) == out.at(8, 7) && out.at(7, 6) == out.at(7, 8), "Impulse response not mirrored");
    require(std::fabs(out.at(6, 7) - out.at(7, 6)) < 1e-9, "Impulse response not symmetric in x and y");
}

static void test_random_vs_reference() {
    const int sizes[][2] = {{37, 29}, {64, 48}, {7, 40}, {40, 7}};
    for (const auto& s : sizes) {
        RgbFixture img(s[0], s[1]);
        img.randomize(16u + s[0]);
        GrayFixture out(s[0], s[1]);
        run_ok(img, out, settings());
        require(max_error_vs_reference(img, out, 1.0, 3) <= 1e-5, "Random image differs from 2D reference");
    }
    RgbFixture img(33, 21);
    img.randomize(99);
    GrayFixture out(33, 21);
    run_ok(img, out, settings(2.0f, 4));
    require(max_error_vs_reference(img, out, 2.0, 4) <= 1e-5, "sigma 2 radius 4 differs");
    run_ok(img, out, settings(8.0f, 16));
    require(max_error_vs_reference(img, out, 8.0, 16) <= 1e-5, "sigma 8 radius 16 differs");
}

static void test_padding() {
    RgbFixture packed(31, 19), padded(31, 19, 13);
    packed.randomize(5);
    for (int y = 0; y < 19; ++y)  // copy pixels; padded rows keep 231 in the padding
        for (int x = 0; x < 31; ++x) {
            const std::uint8_t* p = packed.storage.data() + y * packed.image.stride + 3 * x;
            padded.set(x, y, p[0], p[1], p[2]);
        }
    GrayFixture a(31, 19), b(31, 19, 5);
    run_ok(packed, a, settings());
    run_ok(padded, b, settings());
    for (int y = 0; y < 19; ++y)
        for (int x = 0; x < 31; ++x)
            require(a.at(x, y) == b.at(x, y), "Padded input/output gives a different result");
    require(b.padding_untouched(), "Output padding was written");
    // Different padding content must not change anything.
    for (int y = 0; y < 19; ++y)
        for (int x = 31 * 3; x < static_cast<int>(padded.image.stride); ++x)
            padded.storage[y * padded.image.stride + x] = 0;
    GrayFixture c(31, 19, 5);
    run_ok(padded, c, settings());
    require(c.storage == b.storage, "Input padding influences the result");
}

static void test_small_images() {
    const int sizes[][2] = {{1, 1}, {1, 9}, {9, 1}, {2, 2}, {3, 2}, {2, 5}};
    for (const auto& s : sizes) {
        RgbFixture img(s[0], s[1]);
        img.randomize(7 + s[0] * 31 + s[1]);
        GrayFixture out(s[0], s[1]);
        run_ok(img, out, settings());
        require(max_error_vs_reference(img, out, 1.0, 3) <= 1e-5, "Small image differs from reference");
        RgbFixture flat(s[0], s[1]);
        flat.fill(200, 40, 90);
        GrayFixture f(s[0], s[1]);
        run_ok(flat, f, settings(8.0f, 16));
        const double expected = (0.299 * 200 + 0.587 * 40 + 0.114 * 90) / 255.0;
        for (int y = 0; y < s[1]; ++y)
            for (int x = 0; x < s[0]; ++x) require(std::fabs(f.at(x, y) - expected) < 1e-5, "Flat small image changed");
    }
}

static void test_invalid_arguments() {
    RgbFixture good(8, 6);
    good.randomize(3);
    GrayFixture out(8, 6);
    const Config config = settings();

    Image bad = good.image; bad.data = nullptr;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Null input");
    bad = good.image; bad.channels = 1;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input channels 1");
    bad = good.image; bad.channels = 4;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input channels 4");
    bad = good.image; bad.width = 0;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input width 0");
    bad = good.image; bad.height = -1;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input height < 0");
    bad = good.image; bad.stride = 8 * 3 - 1;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input stride too small");
    bad = good.image; bad.stride = 1;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input stride 1");
    bad = good.image; bad.stride = std::numeric_limits<std::size_t>::max();
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input stride overflows");
    bad = good.image; bad.stride = std::numeric_limits<std::size_t>::max() / 4;
    expect_error(bad, out.image, out, config, ErrorCode::InvalidImage, "Input stride * height overflows");

    GrayImage g = out.image; g.data = nullptr;
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Null output");
    g = out.image; g.width = 7;
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Output width differs");
    g = out.image; g.height = 5;
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Output height differs");
    g = out.image; g.channels = 3;
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Output channels 3");
    g = out.image; g.stride = 8;  // element units instead of bytes
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Output stride in elements");
    g = out.image; g.stride = 8 * sizeof(float) + 2;
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Output stride not multiple of 4");
    g = out.image; g.stride = std::numeric_limits<std::size_t>::max() & ~std::size_t(3);
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Output stride overflows");
    g = out.image; g.data = reinterpret_cast<float*>(reinterpret_cast<unsigned char*>(out.storage.data()) + 1);
    expect_error(good.image, g, out, config, ErrorCode::InvalidImage, "Misaligned output");

    expect_error(good.image, out.image, out, Config(), ErrorCode::InvalidConfig, "Unset config");
    const float nan = std::nanf("");
    expect_error(good.image, out.image, out, settings(nan, 3), ErrorCode::InvalidConfig, "sigma NaN");
    expect_error(good.image, out.image, out, settings(-1.0f, 3), ErrorCode::InvalidConfig, "sigma < 0");
    expect_error(good.image, out.image, out, settings(1.0f, 0), ErrorCode::InvalidConfig, "radius 0");
    expect_error(good.image, out.image, out, settings(1.0f, 17), ErrorCode::InvalidConfig, "radius 17");
    expect_error(good.image, out.image, out, settings(2.0f, 3), ErrorCode::InvalidConfig, "radius < 2 sigma");
    // Image errors take precedence over config errors.
    bad = good.image; bad.data = nullptr;
    expect_error(bad, out.image, out, Config(), ErrorCode::InvalidImage, "Image error order");

    require(out.all_sentinel(), "Output touched by an error path");
}

static void test_determinism_and_alloc() {
    RgbFixture img(41, 27, 3);
    img.randomize(2024);
    GrayFixture a(41, 27, 2), b(41, 27, 2);
    run_ok(img, a, settings());
    run_ok(img, b, settings());
    require(a.storage == b.storage && std::memcmp(a.storage.data(), b.storage.data(),
            a.storage.size() * sizeof(float)) == 0, "Two runs differ");
    run_ok(img, a, settings());  // reuse a dirty output buffer
    require(std::memcmp(a.storage.data(), b.storage.data(), a.storage.size() * sizeof(float)) == 0,
            "Reused output buffer changes the result");

    GrayFixture c(41, 27);
    fail_array_allocation = true;
    const ErrorCode status = v0_preprocess(img.image, c.image, settings());
    fail_array_allocation = false;
    require(status == ErrorCode::AllocationFailed, "Allocation failure not reported");
    require(c.all_sentinel(), "Output touched after allocation failure");
    GrayImage debug_out = c.image;
    require(v0_preprocess(img.image, debug_out, settings(), true) == ErrorCode::Success, "Debug mode failed");
}

int main() {
    try {
        test_kernel();
        test_constant_and_colors();
        test_impulse();
        test_random_vs_reference();
        test_padding();
        test_small_images();
        test_invalid_arguments();
        test_determinism_and_alloc();
        std::cout << "PASS: " << checks << " assertions for S1 grayscale, blur, errors and OOM\n";
        return 0;
    } catch (const std::exception& error) {
        fail_array_allocation = false;
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
