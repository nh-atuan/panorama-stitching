// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// S2 of V1 against v0_detect (S2 design, sections 6.4 and 7): identical keypoints, score bits
// and order; same error codes; outputs untouched on an error. Also chains S1 V1 -> S2 V1 against
// V0. Optional arguments `<left> <right>` run the chained check on real images.

#include "gpu/s45_test_support.cuh"
#include "support/gpu_compare.h"
#include "support/v0_reference.h"
#include "v0/v0_detect.h"
#include "v0/v0_preprocess.h"
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
#include <algorithm>
#include <cmath>
#include <random>

using namespace panorama;
using namespace gpu_test;

namespace {

constexpr float kGrayPadding = -7.0f;
std::size_t g_compared = 0;

struct Gray {
    std::int32_t width = 0, height = 0;
    std::vector<float> pixels;  // Packed.
    GrayImage view() {
        GrayImage image;
        image.data = pixels.data();
        image.stride = static_cast<std::size_t>(width) * sizeof(float);
        image.width = width;
        image.height = height;
        image.channels = 1;
        return image;
    }
};

Config make_config(float threshold, std::int32_t max_keypoints) {
    Config config;
    config.gaussian_sigma = 1.0f;
    config.gaussian_radius = 3;
    config.fast_threshold = threshold;
    config.max_keypoints = max_keypoints;
    return config;
}

Gray blurred_test_image(std::int32_t w, std::int32_t h, std::uint32_t seed) {
    RgbImage rgb = make_test_image(w, h, seed);
    Gray gray;
    gray.width = w;
    gray.height = h;
    gray.pixels.assign(static_cast<std::size_t>(w) * h, 0.0f);
    GrayImage view = gray.view();
    require(v0_preprocess(rgb.view(), view, make_config(0.05f, 1)) == ErrorCode::Success, "V0 preprocess");
    return gray;
}

// Blocks of 3 gray levels: many corners share a score, so the raster tie rule matters.
Gray three_level_image(std::int32_t w, std::int32_t h, std::uint32_t seed) {
    Gray gray;
    gray.width = w;
    gray.height = h;
    gray.pixels.resize(static_cast<std::size_t>(w) * h);
    std::mt19937 random(seed);
    const float levels[] = {0.2f, 0.5f, 0.8f};
    std::vector<float> blocks(static_cast<std::size_t>((w + 3) / 4) * ((h + 3) / 4));
    for (float& v : blocks) v = levels[random() % 3];
    for (std::int32_t y = 0; y < h; ++y) {
        for (std::int32_t x = 0; x < w; ++x) gray.pixels[y * w + x] = blocks[(y / 4) * ((w + 3) / 4) + x / 4];
    }
    return gray;
}

// Uniform noise: tens of thousands of candidates, so the sort works on large non power-of-two counts.
Gray noise_image(std::int32_t w, std::int32_t h, std::uint32_t seed) {
    Gray gray;
    gray.width = w;
    gray.height = h;
    gray.pixels.resize(static_cast<std::size_t>(w) * h);
    std::mt19937 random(seed);
    std::uniform_real_distribution<float> value(0.0f, 1.0f);
    for (float& v : gray.pixels) v = value(random);
    return gray;
}

Gray constant_image(std::int32_t w, std::int32_t h, float value) {
    Gray gray;
    gray.width = w;
    gray.height = h;
    gray.pixels.assign(static_cast<std::size_t>(w) * h, value);
    return gray;
}

std::vector<Keypoint> v0_keypoints(Gray gray, const Config& config) {
    std::vector<Keypoint> keypoints;
    require(v0_detect(gray.view(), keypoints, config) == ErrorCode::Success, "V0 detect");
    return keypoints;
}

std::vector<float> padded(const Gray& gray, std::int32_t pad) {
    std::vector<float> values(static_cast<std::size_t>(gray.width + pad) * gray.height, kGrayPadding);
    for (std::int32_t y = 0; y < gray.height; ++y) {
        std::copy(gray.pixels.begin() + y * gray.width, gray.pixels.begin() + (y + 1) * gray.width,
                  values.begin() + y * (gray.width + pad));
    }
    return values;
}

Keypoint sentinel_keypoint() {
    Keypoint k;
    k.x = k.y = k.score = k.angle = -3.0f;
    return k;
}

DeviceCounts sentinel_counts() {
    DeviceCounts counts;
    counts.keypointsA = counts.keypointsB = 777;
    counts.descriptorsA = counts.descriptorsB = 555;
    counts.matches = 333;
    counts.status = ErrorCode::InsufficientMatches;
    return counts;
}

bool same_counts(const DeviceCounts& a, const DeviceCounts& b) {
    return a.keypointsA == b.keypointsA && a.keypointsB == b.keypointsB && a.descriptorsA == b.descriptorsA &&
           a.descriptorsB == b.descriptorsB && a.matches == b.matches && a.status == b.status;
}

// Gray A and B on the Device (with `pad` floats of padding per row), keypoint buffers of
// `capacity` filled with a sentinel, counts filled with a sentinel, and S2 scratch.
struct Fixture {
    Gray a, b;
    std::int32_t pad;
    std::size_t capacity;
    std::vector<float> host_a, host_b;
    DeviceBuffer<float> gray_a, gray_b;
    DeviceBuffer<Keypoint> keypoints_a, keypoints_b;
    DeviceBuffer<DeviceCounts> counts;
    DeviceBuffer<std::uint8_t> scratch;
    DeviceWorkspace w;
    Stream stream;

    Fixture(const Gray& left, const Gray& right, std::int32_t padding, std::size_t keypoint_capacity)
        : a(left), b(right), pad(padding), capacity(keypoint_capacity), host_a(padded(a, pad)),
          host_b(padded(b, pad)), gray_a(host_a.size()), gray_b(host_b.size()), keypoints_a(capacity),
          keypoints_b(capacity), counts(1),
          scratch(std::max(v1_detect_scratch_bytes(a.width, a.height), v1_detect_scratch_bytes(b.width, b.height))) {
        gray_a.upload(host_a);
        gray_b.upload(host_b);
        keypoints_a.upload(std::vector<Keypoint>(capacity, sentinel_keypoint()));
        keypoints_b.upload(std::vector<Keypoint>(capacity, sentinel_keypoint()));
        counts.upload(std::vector<DeviceCounts>(1, sentinel_counts()));
        w.d_grayA = gray_a.data;
        w.d_grayB = gray_b.data;
        w.grayA = view(gray_a.data, a);
        w.grayB = view(gray_b.data, b);
        w.d_keypointsA = keypoints_a.data;
        w.d_keypointsB = keypoints_b.data;
        w.keypoint_capacityA = w.keypoint_capacityB = capacity;
        w.d_counts = counts.data;
        w.d_scratch = scratch.data;
        w.scratch_capacity_bytes = scratch.count;
    }
    GrayImage view(float* data, const Gray& gray) const {
        GrayImage image;
        image.data = data;
        image.stride = static_cast<std::size_t>(gray.width + pad) * sizeof(float);
        image.width = gray.width;
        image.height = gray.height;
        image.channels = 1;
        return image;
    }
    ErrorCode run(const Config& config) {
        const ErrorCode status = v1_detect(w, config, stream.value);
        stream.wait();
        return status;
    }
    DeviceCounts read_counts() const { return counts.read(1)[0]; }
    std::vector<Keypoint> keypoints(bool image_a) const {
        const DeviceCounts c = read_counts();
        const std::uint32_t n = image_a ? c.keypointsA : c.keypointsB;
        require(n <= capacity, "count within capacity");
        return (image_a ? keypoints_a : keypoints_b).read(n);
    }
    bool outputs_untouched() const {
        const std::vector<Keypoint> ka = keypoints_a.read(capacity), kb = keypoints_b.read(capacity);
        const std::vector<Keypoint> s(capacity, sentinel_keypoint());
        return same_counts(read_counts(), sentinel_counts()) && keypoint_mismatch(s, ka).empty() &&
               keypoint_mismatch(s, kb).empty();
    }
    bool gray_untouched() const { return gray_a.read(host_a.size()) == host_a && gray_b.read(host_b.size()) == host_b; }
};

std::string label_of(const std::string& name, const Gray& gray, const Config& config) {
    return name + " " + std::to_string(gray.width) + "x" + std::to_string(gray.height) +
           " t=" + std::to_string(config.fast_threshold) + " N=" + std::to_string(config.max_keypoints);
}

void compare(const Gray& left, const Gray& right, const Config& config, std::int32_t pad, const std::string& name) {
    Fixture f(left, right, pad, static_cast<std::size_t>(config.max_keypoints));
    require(f.run(config) == ErrorCode::Success, label_of(name, left, config) + ": v1_detect");
    const std::vector<Keypoint> expected[2] = {v0_keypoints(left, config), v0_keypoints(right, config)};
    for (int i = 0; i < 2; ++i) {
        const std::string message = keypoint_mismatch(expected[i], f.keypoints(i == 0));
        require(message.empty(), label_of(name, i ? right : left, config) + (i ? " B: " : " A: ") + message);
        g_compared += expected[i].size();
    }
    const DeviceCounts c = f.read_counts();
    require(c.status == ErrorCode::InsufficientMatches && c.descriptorsA == 555 && c.matches == 333,
            name + ": other counts and status untouched");
    require(f.gray_untouched(), name + ": gray input untouched");
}

void test_matches_v0() {
    const std::int32_t sizes[][2] = {{31, 31}, {33, 47}, {64, 64}, {97, 61}, {257, 131}, {320, 240}};
    const float thresholds[] = {0.02f, 0.05f, 0.1f, 0.2f};
    const std::int32_t limits[] = {1, 7, 2000};
    std::uint32_t seed = 16;
    for (const auto& size : sizes) {
        for (float t : thresholds) {
            for (std::int32_t n : limits) {
                const Config config = make_config(t, n);
                compare(blurred_test_image(size[0], size[1], seed), three_level_image(size[1], size[0], seed + 1),
                        config, 0, "rectangles/three levels");
                ++seed;
            }
        }
    }
}

void test_many_candidates() {
    // Noise gives far more than 2000 candidates; N above the count checks the full sorted list.
    const Gray a = noise_image(257, 131, 7), b = noise_image(640, 480, 8);
    for (std::int32_t n : {1, 2000, 30000, 1000000}) compare(a, b, make_config(0.05f, n), 0, "noise");
    compare(a, b, make_config(0.3f, 50000), 3, "noise padded");
}

void test_padding() {
    const Gray a = blurred_test_image(120, 90, 3), b = three_level_image(90, 120, 4);
    compare(a, b, make_config(0.05f, 2000), 5, "padded");
}

void test_small_and_flat_images() {
    const Config config = make_config(0.05f, 2000);
    const std::int32_t sizes[][2] = {{1, 1}, {2, 2}, {30, 30}, {30, 200}, {200, 30}};
    for (const auto& size : sizes) {
        Fixture f(blurred_test_image(size[0], size[1], 1), noise_image(size[0], size[1], 2), 0, 2000);
        require(f.run(config) == ErrorCode::Success, "small image");
        const DeviceCounts c = f.read_counts();
        require(c.keypointsA == 0 && c.keypointsB == 0, "small image has no keypoints");
    }
    compare(constant_image(64, 64, 0.5f), constant_image(64, 64, 0.0f), config, 0, "constant");

    Gray dot = constant_image(31, 31, 0.8f);
    dot.pixels[15 * 31 + 15] = 0.1f;
    Fixture f(dot, dot, 0, 2000);
    require(f.run(config) == ErrorCode::Success, "dot");
    const std::vector<Keypoint> k = f.keypoints(true);
    require(k.size() == 1 && k[0].x == 15.0f && k[0].y == 15.0f && k[0].angle == 0.0f, "dot at (15, 15)");
}

void test_repeat_is_bit_identical() {
    const Gray a = noise_image(200, 150, 21), b = blurred_test_image(150, 200, 22);
    Fixture f(a, b, 0, 2000);
    const Config config = make_config(0.05f, 2000);
    require(f.run(config) == ErrorCode::Success, "first run");
    const std::vector<Keypoint> ka = f.keypoints(true), kb = f.keypoints(false);
    require(f.run(config) == ErrorCode::Success, "second run");
    require(keypoint_mismatch(ka, f.keypoints(true)).empty(), "repeat A");
    require(keypoint_mismatch(kb, f.keypoints(false)).empty(), "repeat B");
}

void test_scratch_bytes() {
    require(v1_detect_scratch_bytes(30, 500) == 0, "no region");
    require(v1_detect_scratch_bytes(0, 64) == 0, "width 0");
    require(v1_detect_scratch_bytes(64, -2) == 0, "height negative");
    // 31 x 31: counter 16 + scores 3844 -> keys at 3872; 16 x 16 = 256 slots of 8 bytes.
    require(v1_detect_scratch_bytes(31, 31) == 3872 + 256 * 8, "31x31 layout");
    require(v1_detect_scratch_bytes(70000, 70000) == 0, "W*H over 32 bits");
}

template <class Mutate>
void expect_error(const std::string& label, ErrorCode code, const Config& config, Mutate mutate) {
    Fixture f(blurred_test_image(64, 48, 3), blurred_test_image(48, 64, 4), 0, 16);
    mutate(f.w);
    require(f.run(config) == code, label + ": error code");
    require(f.outputs_untouched(), label + ": outputs untouched");
}

void test_bad_calls() {
    const Config good = make_config(0.05f, 16);
    expect_error("A null", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.grayA.data = nullptr; });
    expect_error("B channels", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.grayB.channels = 3; });
    expect_error("A stride in elements", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.grayA.stride = 64; });
    expect_error("B stride odd", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.grayB.stride += 2; });
    expect_error("A height 0", ErrorCode::InvalidImage, good, [](DeviceWorkspace& w) { w.grayA.height = 0; });
    expect_error("image before config", ErrorCode::InvalidImage, make_config(0.0f, 16),
                 [](DeviceWorkspace& w) { w.grayB.channels = 2; });

    auto none = [](DeviceWorkspace&) {};
    expect_error("t 0", ErrorCode::InvalidConfig, make_config(0.0f, 16), none);
    expect_error("t 1", ErrorCode::InvalidConfig, make_config(1.0f, 16), none);
    expect_error("t negative", ErrorCode::InvalidConfig, make_config(-0.1f, 16), none);
    expect_error("t NaN", ErrorCode::InvalidConfig, make_config(std::nanf(""), 16), none);
    expect_error("t infinite", ErrorCode::InvalidConfig, make_config(INFINITY, 16), none);
    expect_error("N 0", ErrorCode::InvalidConfig, make_config(0.05f, 0), none);
    expect_error("N over limit", ErrorCode::InvalidConfig, make_config(0.05f, kMaxKeypointsLimit + 1), none);
    expect_error("default config", ErrorCode::InvalidConfig, Config(), none);
    expect_error("config before workspace", ErrorCode::InvalidConfig, make_config(0.05f, 0),
                 [](DeviceWorkspace& w) { w.d_scratch = nullptr; });

    expect_error("counts null", ErrorCode::InvalidArgument, good, [](DeviceWorkspace& w) { w.d_counts = nullptr; });
    expect_error("keypoints B null", ErrorCode::InvalidArgument, good,
                 [](DeviceWorkspace& w) { w.d_keypointsB = nullptr; });
    expect_error("capacity A below N", ErrorCode::InvalidArgument, good,
                 [](DeviceWorkspace& w) { w.keypoint_capacityA = 15; });
    expect_error("scratch null", ErrorCode::InvalidArgument, good, [](DeviceWorkspace& w) { w.d_scratch = nullptr; });
    expect_error("scratch small", ErrorCode::InvalidArgument, good,
                 [](DeviceWorkspace& w) { w.scratch_capacity_bytes -= 1; });
    expect_error("scratch misaligned", ErrorCode::InvalidArgument, good, [](DeviceWorkspace& w) {
        w.d_scratch += 8;
        w.scratch_capacity_bytes -= 8;
    });
}

// S1 V1 -> S2 V1 on the Device against v0_preprocess -> v0_detect.
void compare_chain(RgbImage left, RgbImage right, const Config& config, const std::string& name) {
    V0Features expected[2];
    RgbImage* images[2] = {&left, &right};
    for (int i = 0; i < 2; ++i) {
        expected[i].width = images[i]->width;
        expected[i].height = images[i]->height;
        expected[i].gray_pixels.assign(static_cast<std::size_t>(images[i]->width) * images[i]->height, 0.0f);
        GrayImage gray = expected[i].gray();
        require(v0_preprocess(images[i]->view(), gray, config) == ErrorCode::Success, "chain V0 S1");
        require(v0_detect(gray, expected[i].detected, config) == ErrorCode::Success, "chain V0 S2");
    }
    const std::size_t capacity = static_cast<std::size_t>(config.max_keypoints);
    DeviceBuffer<std::uint8_t> rgb_a(left.bytes.size()), rgb_b(right.bytes.size());
    DeviceBuffer<float> gray_a(expected[0].gray_pixels.size()), gray_b(expected[1].gray_pixels.size());
    DeviceBuffer<Keypoint> kp_a(capacity), kp_b(capacity);
    DeviceBuffer<DeviceCounts> counts(1);
    const std::size_t scratch_bytes = std::max(
        std::max(v1_preprocess_scratch_bytes(left.width, left.height), v1_preprocess_scratch_bytes(right.width, right.height)),
        std::max(v1_detect_scratch_bytes(left.width, left.height), v1_detect_scratch_bytes(right.width, right.height)));
    DeviceBuffer<std::uint8_t> scratch(scratch_bytes);
    rgb_a.upload(left.bytes);
    rgb_b.upload(right.bytes);
    counts.upload(std::vector<DeviceCounts>(1));
    DeviceWorkspace w;
    w.d_imageA = rgb_a.data;
    w.d_imageB = rgb_b.data;
    w.imageA = left.view();
    w.imageA.data = rgb_a.data;
    w.imageB = right.view();
    w.imageB.data = rgb_b.data;
    w.d_grayA = gray_a.data;
    w.d_grayB = gray_b.data;
    w.grayA = expected[0].gray();
    w.grayA.data = gray_a.data;
    w.grayB = expected[1].gray();
    w.grayB.data = gray_b.data;
    w.d_keypointsA = kp_a.data;
    w.d_keypointsB = kp_b.data;
    w.keypoint_capacityA = w.keypoint_capacityB = capacity;
    w.d_counts = counts.data;
    w.d_scratch = scratch.data;
    w.scratch_capacity_bytes = scratch.count;
    Stream stream;
    require(v1_preprocess(w, config, stream.value) == ErrorCode::Success, name + ": chain V1 S1");
    require(v1_detect(w, config, stream.value) == ErrorCode::Success, name + ": chain V1 S2");
    stream.wait();
    const DeviceCounts c = counts.read(1)[0];
    const std::vector<Keypoint> actual[2] = {kp_a.read(c.keypointsA), kp_b.read(c.keypointsB)};
    for (int i = 0; i < 2; ++i) {
        const std::string message = keypoint_mismatch(expected[i].detected, actual[i]);
        require(message.empty(), name + (i ? " chain B: " : " chain A: ") + message);
        g_compared += actual[i].size();
    }
    std::cout << "S2 chain " << name << " " << left.width << "x" << left.height << ": keypoints A=" << c.keypointsA
              << " B=" << c.keypointsB << " identical to V0\n";
}

void test_chain() {
    compare_chain(make_test_image(320, 240, 31), make_test_image(240, 320, 32), make_config(0.05f, 2000),
                  "rectangles");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        print_gpu();
        if (argc != 1 && argc != 3) throw std::runtime_error("usage: gpu_s2 [<left> <right>]");
        test_scratch_bytes();
        test_matches_v0();
        test_many_candidates();
        test_padding();
        test_small_and_flat_images();
        test_repeat_is_bit_identical();
        test_bad_calls();
        test_chain();
        if (argc == 3) {
            RgbImage left, right;
            require(load_rgb_image(argv[1], left), std::string("load ") + argv[1]);
            require(load_rgb_image(argv[2], right), std::string("load ") + argv[2]);
            compare_chain(left, right, make_config(0.05f, 2000), "real images");
        }
        std::cout << "S2 keypoints compared=" << g_compared << " mismatches=0\n";
        std::cout << "PASS GPU S2: " << checks() << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
