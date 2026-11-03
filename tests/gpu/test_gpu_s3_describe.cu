// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// S3 of V1 against v0_describe (S3 design, sections 6.4 and 7): identical kept keypoints,
// order and descriptor bits; Host and Device error handling. Also chains S1 -> S2 -> S3 on the
// GPU against V0, then feeds the S3 output to v1_match and compares with v0_match.
// Optional arguments `<left> <right>` run the chain on real images.

#include "gpu/s45_test_support.cuh"
#include "support/gpu_compare.h"
#include "support/v0_reference.h"
#include "v0/v0_match.h"
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
#include "v1/s3/v1_describe.h"
#include "v1/s4/v1_match.h"
#include <algorithm>
#include <cmath>
#include <random>

using namespace panorama;
using namespace gpu_test;

namespace {

constexpr float kGrayPadding = -7.0f;
std::size_t g_descriptors = 0;

struct Gray {
    std::int32_t width = 0, height = 0;
    std::vector<float> pixels;
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

Keypoint keypoint(float x, float y) {
    Keypoint k;
    k.x = x;
    k.y = y;
    k.score = x + y;
    k.angle = 0.25f;
    return k;
}

// Points inside and outside the patch border, on rounding halves, far away and duplicated.
std::vector<Keypoint> mixed_keypoints(std::int32_t w, std::int32_t h, std::uint32_t seed, std::size_t count) {
    std::mt19937 random(seed);
    std::uniform_real_distribution<float> x(-5.0f, w + 5.0f), y(-5.0f, h + 5.0f);
    std::vector<Keypoint> keypoints;
    keypoints.push_back(keypoint(15.0f, 15.0f));
    keypoints.push_back(keypoint(w - 16.0f, h - 16.0f));
    keypoints.push_back(keypoint(14.49f, 20.0f));
    keypoints.push_back(keypoint(14.5f, 20.0f));
    keypoints.push_back(keypoint(w - 15.5f, 20.0f));
    keypoints.push_back(keypoint(w - 16.5f, 20.0f));
    keypoints.push_back(keypoint(1e30f, 20.0f));
    keypoints.push_back(keypoint(20.0f, -1e30f));
    keypoints.push_back(keypoint(99.6f, 80.4f));
    keypoints.push_back(keypoints.back());
    while (keypoints.size() < count) keypoints.push_back(keypoint(x(random), y(random)));
    keypoints.resize(count);
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

Descriptor sentinel_descriptor() {
    Descriptor d;
    for (std::uint32_t& word : d.data) word = 0xDEADBEEFu;
    return d;
}

// Gray A/B, keypoints and descriptor buffers of `capacity`, counts and S3 scratch on the Device.
struct Fixture {
    Gray a, b;
    std::vector<Keypoint> kp_a, kp_b;
    std::int32_t pad;
    std::size_t capacity;
    std::vector<float> host_a, host_b;
    DeviceBuffer<float> gray_a, gray_b;
    DeviceBuffer<Keypoint> keypoints_a, keypoints_b;
    DeviceBuffer<Descriptor> descriptors_a, descriptors_b;
    DeviceBuffer<DeviceCounts> counts;
    DeviceBuffer<std::uint8_t> scratch;
    DeviceWorkspace w;
    Stream stream;

    Fixture(const Gray& left, const Gray& right, const std::vector<Keypoint>& left_kp,
            const std::vector<Keypoint>& right_kp, std::int32_t padding, std::size_t keypoint_capacity)
        : a(left), b(right), kp_a(left_kp), kp_b(right_kp), pad(padding), capacity(keypoint_capacity),
          host_a(padded(a, pad)), host_b(padded(b, pad)), gray_a(host_a.size()), gray_b(host_b.size()),
          keypoints_a(capacity), keypoints_b(capacity), descriptors_a(capacity), descriptors_b(capacity), counts(1),
          scratch(std::max(v1_describe_scratch_bytes(a.width, a.height, capacity),
                           v1_describe_scratch_bytes(b.width, b.height, capacity))) {
        gray_a.upload(host_a);
        gray_b.upload(host_b);
        std::vector<Keypoint> full_a(kp_a), full_b(kp_b);
        full_a.resize(std::max(capacity, full_a.size()), keypoint(-3.0f, -3.0f));
        full_b.resize(std::max(capacity, full_b.size()), keypoint(-3.0f, -3.0f));
        full_a.resize(capacity);
        full_b.resize(capacity);
        keypoints_a.upload(full_a);
        keypoints_b.upload(full_b);
        descriptors_a.upload(std::vector<Descriptor>(capacity, sentinel_descriptor()));
        descriptors_b.upload(std::vector<Descriptor>(capacity, sentinel_descriptor()));
        DeviceCounts c;
        c.keypointsA = static_cast<std::uint32_t>(kp_a.size());
        c.keypointsB = static_cast<std::uint32_t>(kp_b.size());
        c.descriptorsA = c.descriptorsB = 999;
        c.matches = 333;
        counts.upload(std::vector<DeviceCounts>(1, c));
        w.d_grayA = gray_a.data;
        w.d_grayB = gray_b.data;
        w.grayA = view(gray_a.data, a);
        w.grayB = view(gray_b.data, b);
        w.d_keypointsA = keypoints_a.data;
        w.d_keypointsB = keypoints_b.data;
        w.d_descriptorsA = descriptors_a.data;
        w.d_descriptorsB = descriptors_b.data;
        w.keypoint_capacityA = w.keypoint_capacityB = capacity;
        w.descriptor_capacityA = w.descriptor_capacityB = capacity;
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
    ErrorCode run() {
        const ErrorCode status = v1_describe(w, Config(), stream.value);
        stream.wait();
        return status;
    }
    DeviceCounts read_counts() const { return counts.read(1)[0]; }
    bool gray_untouched() const { return gray_a.read(host_a.size()) == host_a && gray_b.read(host_b.size()) == host_b; }
    bool keypoints_untouched() const {
        return keypoint_mismatch(kp_a, keypoints_a.read(kp_a.size())).empty() &&
               keypoint_mismatch(kp_b, keypoints_b.read(kp_b.size())).empty();
    }
    bool descriptors_untouched() const {
        const std::vector<Descriptor> s(capacity, sentinel_descriptor());
        return descriptor_mismatch(s, descriptors_a.read(capacity)).empty() &&
               descriptor_mismatch(s, descriptors_b.read(capacity)).empty();
    }
};

void expect_v0(Gray gray, std::vector<Keypoint> keypoints, std::vector<Keypoint>& kept,
               std::vector<Descriptor>& descriptors) {
    require(v0_describe(gray.view(), keypoints, descriptors, Config()) == ErrorCode::Success, "V0 describe");
    kept = keypoints;
}

void compare(const Gray& left, const Gray& right, const std::vector<Keypoint>& kp_left,
             const std::vector<Keypoint>& kp_right, std::int32_t pad, std::size_t capacity, const std::string& name) {
    Fixture f(left, right, kp_left, kp_right, pad, capacity);
    require(f.run() == ErrorCode::Success, name + ": v1_describe");
    const DeviceCounts c = f.read_counts();
    require(c.status == ErrorCode::Success && c.matches == 333, name + ": status and match count untouched");
    const Gray* grays[2] = {&left, &right};
    const std::vector<Keypoint>* inputs[2] = {&kp_left, &kp_right};
    const std::uint32_t kept_count[2] = {c.keypointsA, c.keypointsB};
    const std::uint32_t descriptor_count[2] = {c.descriptorsA, c.descriptorsB};
    for (int i = 0; i < 2; ++i) {
        std::vector<Keypoint> kept;
        std::vector<Descriptor> descriptors;
        expect_v0(*grays[i], *inputs[i], kept, descriptors);
        const std::string side = i ? " B: " : " A: ";
        require(kept_count[i] == kept.size() && descriptor_count[i] == kept.size(), name + side + "counts");
        const std::string kp = keypoint_mismatch(kept, (i ? f.keypoints_b : f.keypoints_a).read(kept_count[i]));
        require(kp.empty(), name + side + "keypoints " + kp);
        const std::string ds =
            descriptor_mismatch(descriptors, (i ? f.descriptors_b : f.descriptors_a).read(descriptor_count[i]));
        require(ds.empty(), name + side + "descriptors " + ds);
        g_descriptors += descriptors.size();
    }
    require(f.gray_untouched(), name + ": gray untouched");
}

void test_matches_v0() {
    const std::int32_t sizes[][2] = {{31, 31}, {64, 48}, {97, 61}, {257, 131}, {640, 480}};
    std::uint32_t seed = 16;
    for (const auto& size : sizes) {
        const Gray a = noise_image(size[0], size[1], seed), b = noise_image(size[1], size[0], seed + 1);
        for (std::size_t count : {std::size_t(1), std::size_t(10), std::size_t(300), std::size_t(2000)}) {
            compare(a, b, mixed_keypoints(a.width, a.height, seed + 2, count),
                    mixed_keypoints(b.width, b.height, seed + 3, count), 0, count, "mixed");
        }
        seed += 4;
    }
    // Count below capacity, more keypoints than one scan tile, and padded gray rows.
    const Gray a = noise_image(300, 200, 5), b = noise_image(200, 300, 6);
    compare(a, b, mixed_keypoints(300, 200, 7, 2500), mixed_keypoints(200, 300, 8, 1500), 3, 3000, "padded");
}

void test_empty_and_narrow() {
    const Gray a = noise_image(64, 64, 1), narrow = noise_image(30, 40, 2);
    compare(a, a, std::vector<Keypoint>(), std::vector<Keypoint>(), 0, 16, "empty");
    compare(narrow, narrow, mixed_keypoints(30, 40, 3, 20), mixed_keypoints(30, 40, 4, 20), 0, 20, "narrow");
    compare(a, a, std::vector<Keypoint>(), std::vector<Keypoint>(), 0, 0, "capacity 0");
}

void test_repeat_is_bit_identical() {
    const Gray a = noise_image(120, 90, 9);
    const std::vector<Keypoint> kp = mixed_keypoints(120, 90, 10, 200);
    Fixture f(a, a, kp, kp, 0, 200);
    require(f.run() == ErrorCode::Success, "first run");
    const DeviceCounts c = f.read_counts();
    const std::vector<Descriptor> first = f.descriptors_a.read(c.descriptorsA);
    const std::vector<Keypoint> kept = f.keypoints_a.read(c.keypointsA);
    // Second run on the already compacted list: every keypoint is kept, same descriptors.
    require(f.run() == ErrorCode::Success, "second run");
    const DeviceCounts d = f.read_counts();
    require(d.keypointsA == c.keypointsA, "second run keeps all");
    require(descriptor_mismatch(first, f.descriptors_a.read(d.descriptorsA)).empty(), "repeat descriptors");
    require(keypoint_mismatch(kept, f.keypoints_a.read(d.keypointsA)).empty(), "repeat keypoints");
}

// Device-side errors: status InvalidArgument, keypoints unchanged, descriptor counts 0.
void test_device_errors() {
    const Gray a = noise_image(64, 64, 11);
    // All inside the patch border, so a successful image A keeps its list unchanged.
    std::vector<Keypoint> kp;
    for (int i = 0; i < 30; ++i) kp.push_back(keypoint(15.0f + i, 48.0f - i));
    std::vector<Keypoint> nan_x = kp, inf_y = kp;
    nan_x[17].x = std::nanf("");
    inf_y[29].y = INFINITY;
    for (int i = 0; i < 2; ++i) {
        // i = 0: A is bad, nothing is written. i = 1: B is bad after A succeeded.
        Fixture f(a, a, i == 0 ? nan_x : kp, i == 0 ? kp : inf_y, 0, 30);
        require(f.run() == ErrorCode::Success, "enqueue non-finite");
        const DeviceCounts c = f.read_counts();
        require(c.status == ErrorCode::InvalidArgument, "non-finite status");
        require(c.descriptorsA == 0 && c.descriptorsB == 0, "non-finite descriptor counts 0");
        require(c.keypointsA == 30 && c.keypointsB == 30, "non-finite keypoint counts unchanged");
        require(f.keypoints_untouched(), "non-finite keypoints unchanged");
        const std::vector<Descriptor> s(30, sentinel_descriptor());
        require(descriptor_mismatch(s, f.descriptors_b.read(30)).empty(), "no descriptor written for B");
        if (i == 0) require(descriptor_mismatch(s, f.descriptors_a.read(30)).empty(), "no descriptor written for A");
    }
    {
        Fixture f(a, a, kp, kp, 0, 30);
        DeviceCounts c = f.read_counts();
        c.keypointsA = 31;
        f.counts.upload(std::vector<DeviceCounts>(1, c));
        require(f.run() == ErrorCode::Success, "enqueue count over capacity");
        c = f.read_counts();
        require(c.status == ErrorCode::InvalidArgument && c.descriptorsA == 0 && c.descriptorsB == 0,
                "count over capacity");
        require(f.keypoints_untouched() && f.descriptors_untouched(), "count over capacity: outputs untouched");
    }
    {
        Fixture f(a, a, kp, kp, 0, 30);
        DeviceCounts c = f.read_counts();
        c.status = ErrorCode::InsufficientKeypoints;
        f.counts.upload(std::vector<DeviceCounts>(1, c));
        require(f.run() == ErrorCode::Success, "enqueue after earlier error");
        const DeviceCounts d = f.read_counts();
        require(d.status == ErrorCode::InsufficientKeypoints && d.descriptorsA == 999 && d.keypointsA == 30,
                "earlier error: counts unchanged");
        require(f.keypoints_untouched() && f.descriptors_untouched(), "earlier error: outputs untouched");
    }
}

template <class Mutate>
void expect_error(const std::string& label, ErrorCode code, Mutate mutate) {
    const Gray a = noise_image(64, 48, 13);
    const std::vector<Keypoint> kp = mixed_keypoints(64, 48, 14, 16);
    Fixture f(a, a, kp, kp, 0, 16);
    mutate(f.w);
    require(f.run() == code, label + ": error code");
    const DeviceCounts c = f.read_counts();
    require(c.descriptorsA == 999 && c.keypointsA == 16 && c.status == ErrorCode::Success, label + ": counts untouched");
    require(f.keypoints_untouched() && f.descriptors_untouched(), label + ": outputs untouched");
}

void test_bad_calls() {
    expect_error("A null", ErrorCode::InvalidImage, [](DeviceWorkspace& w) { w.grayA.data = nullptr; });
    expect_error("B channels", ErrorCode::InvalidImage, [](DeviceWorkspace& w) { w.grayB.channels = 3; });
    expect_error("A stride in elements", ErrorCode::InvalidImage, [](DeviceWorkspace& w) { w.grayA.stride = 64; });
    expect_error("B width 0", ErrorCode::InvalidImage, [](DeviceWorkspace& w) { w.grayB.width = 0; });
    expect_error("image before workspace", ErrorCode::InvalidImage, [](DeviceWorkspace& w) {
        w.grayA.channels = 2;
        w.d_counts = nullptr;
    });
    expect_error("counts null", ErrorCode::InvalidArgument, [](DeviceWorkspace& w) { w.d_counts = nullptr; });
    expect_error("keypoints A null", ErrorCode::InvalidArgument, [](DeviceWorkspace& w) { w.d_keypointsA = nullptr; });
    expect_error("descriptors B null", ErrorCode::InvalidArgument,
                 [](DeviceWorkspace& w) { w.d_descriptorsB = nullptr; });
    expect_error("descriptor capacity small", ErrorCode::InvalidArgument,
                 [](DeviceWorkspace& w) { w.descriptor_capacityA = 15; });
    expect_error("scratch null", ErrorCode::InvalidArgument, [](DeviceWorkspace& w) { w.d_scratch = nullptr; });
    expect_error("scratch small", ErrorCode::InvalidArgument, [](DeviceWorkspace& w) { w.scratch_capacity_bytes -= 1; });
    expect_error("scratch misaligned", ErrorCode::InvalidArgument, [](DeviceWorkspace& w) {
        w.d_scratch += 4;
        w.scratch_capacity_bytes -= 4;
    });
}

void test_scratch_bytes() {
    // 31 x 31: smoothed 3856 (aligned), temp 3856, counter 16, keep 16, 2 keypoints of 16 bytes.
    require(v1_describe_scratch_bytes(31, 31, 2) == 3856 + 3856 + 16 + 16 + 32, "31x31 layout");
    require(v1_describe_scratch_bytes(0, 31, 2) == 0, "width 0");
    require(v1_describe_scratch_bytes(31, 31, 0) == 3856 + 3856 + 16, "capacity 0");
}

// S1 -> S2 -> S3 -> S4 of V1 on the Device, against V0 S1 -> S3 and v0_match.
void compare_chain(RgbImage left, RgbImage right, const std::string& name) {
    Config config;
    require(make_v0_config(left.width, left.height, config) == ErrorCode::Success, "V0 config");
    V0Features expected[2];
    require(compute_v0_features(left.view(), config, expected[0]) == ErrorCode::Success, "chain V0 A");
    require(compute_v0_features(right.view(), config, expected[1]) == ErrorCode::Success, "chain V0 B");

    const std::size_t capacity = static_cast<std::size_t>(config.max_keypoints);
    DeviceBuffer<std::uint8_t> rgb_a(left.bytes.size()), rgb_b(right.bytes.size());
    DeviceBuffer<float> gray_a(expected[0].gray_pixels.size()), gray_b(expected[1].gray_pixels.size());
    DeviceBuffer<Keypoint> kp_a(capacity), kp_b(capacity);
    DeviceBuffer<Descriptor> ds_a(capacity), ds_b(capacity);
    DeviceBuffer<Match> matches(capacity);
    DeviceBuffer<DeviceCounts> counts(1);
    std::size_t scratch_bytes = v1_match_scratch_bytes(capacity);
    const RgbImage* images[2] = {&left, &right};
    for (const RgbImage* image : images) {
        scratch_bytes = std::max(scratch_bytes, v1_preprocess_scratch_bytes(image->width, image->height));
        scratch_bytes = std::max(scratch_bytes, v1_detect_scratch_bytes(image->width, image->height));
        scratch_bytes = std::max(scratch_bytes, v1_describe_scratch_bytes(image->width, image->height, capacity));
    }
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
    w.d_descriptorsA = ds_a.data;
    w.d_descriptorsB = ds_b.data;
    w.d_matches = matches.data;
    w.keypoint_capacityA = w.keypoint_capacityB = capacity;
    w.descriptor_capacityA = w.descriptor_capacityB = capacity;
    w.match_capacity = capacity;
    w.d_counts = counts.data;
    w.d_scratch = scratch.data;
    w.scratch_capacity_bytes = scratch.count;
    Stream stream;
    require(v1_preprocess(w, config, stream.value) == ErrorCode::Success, name + ": V1 S1");
    require(v1_detect(w, config, stream.value) == ErrorCode::Success, name + ": V1 S2");
    require(v1_describe(w, config, stream.value) == ErrorCode::Success, name + ": V1 S3");
    require(v1_match(w, config, stream.value) == ErrorCode::Success, name + ": V1 S4");
    stream.wait();
    const DeviceCounts c = counts.read(1)[0];
    const std::vector<Keypoint> keypoints[2] = {kp_a.read(c.keypointsA), kp_b.read(c.keypointsB)};
    const std::vector<Descriptor> descriptors[2] = {ds_a.read(c.descriptorsA), ds_b.read(c.descriptorsB)};
    for (int i = 0; i < 2; ++i) {
        const std::string side = i ? " chain B: " : " chain A: ";
        const std::string kp = keypoint_mismatch(expected[i].keypoints, keypoints[i]);
        require(kp.empty(), name + side + "keypoints " + kp);
        const std::string ds = descriptor_mismatch(expected[i].descriptors, descriptors[i]);
        require(ds.empty(), name + side + "descriptors " + ds);
        g_descriptors += descriptors[i].size();
    }

    std::vector<Match> reference;
    const ErrorCode s4 = v0_match(
        FeatureView<Descriptor>(expected[0].descriptors.data(), static_cast<std::int32_t>(expected[0].descriptors.size()),
                                expected[0].descriptors.size()),
        FeatureView<Descriptor>(expected[1].descriptors.data(), static_cast<std::int32_t>(expected[1].descriptors.size()),
                                expected[1].descriptors.size()),
        reference, config);
    require(c.status == s4, name + ": S4 status parity");
    const std::vector<Match> actual = matches.read(c.matches);
    require(actual.size() == (s4 == ErrorCode::Success ? reference.size() : 0), name + ": match count");
    for (std::size_t i = 0; i < actual.size(); ++i) {
        require(actual[i].indexA == reference[i].indexA && actual[i].indexB == reference[i].indexB &&
                    actual[i].distance == reference[i].distance,
                name + ": match " + std::to_string(i));
    }
    std::cout << "S3 chain " << name << " " << left.width << "x" << left.height << ": descriptors A="
              << c.descriptorsA << " B=" << c.descriptorsB << " matches=" << c.matches
              << " identical to V0 (S1-S4)\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        print_gpu();
        if (argc != 1 && argc != 3) throw std::runtime_error("usage: gpu_s3 [<left> <right>]");
        test_scratch_bytes();
        test_matches_v0();
        test_empty_and_narrow();
        test_repeat_is_bit_identical();
        test_device_errors();
        test_bad_calls();
        RgbImage left = make_test_image(320, 240, 41), right = left;
        // B is A shifted by (-7, 5), so S4 finds many matches.
        for (std::int32_t y = 0; y < right.height; ++y) {
            for (std::int32_t x = 0; x < right.width; ++x) {
                const std::int32_t sx = std::min(std::max(x + 7, 0), left.width - 1);
                const std::int32_t sy = std::min(std::max(y - 5, 0), left.height - 1);
                for (int ch = 0; ch < 3; ++ch) {
                    right.bytes[(static_cast<std::size_t>(y) * right.width + x) * 3 + ch] =
                        left.bytes[(static_cast<std::size_t>(sy) * left.width + sx) * 3 + ch];
                }
            }
        }
        compare_chain(left, right, "shifted rectangles");
        if (argc == 3) {
            RgbImage real_left, real_right;
            require(load_rgb_image(argv[1], real_left), std::string("load ") + argv[1]);
            require(load_rgb_image(argv[2], real_right), std::string("load ") + argv[2]);
            compare_chain(real_left, real_right, "real images");
        }
        std::cout << "S3 descriptors compared=" << g_descriptors << " mismatches=0\n";
        std::cout << "PASS GPU S3: " << checks() << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
