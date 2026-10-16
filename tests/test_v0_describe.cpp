// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0_describe.h"
#include "brief_pattern.h"
#include "feature_test_support.h"
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <set>
#include <utility>

using namespace panorama;

namespace {

Keypoint keypoint(float x, float y, float score = 1.0f) {
    Keypoint k;
    k.x = x;
    k.y = y;
    k.score = score;
    return k;
}

bool bit(const Descriptor& d, int k) { return ((d.data[k / 32] >> (k % 32)) & 1u) != 0; }

std::uint32_t hamming(const Descriptor& a, const Descriptor& b) {
    std::uint32_t distance = 0;
    for (int w = 0; w < 8; ++w) {
        std::uint32_t v = a.data[w] ^ b.data[w];
        while (v) {
            distance += v & 1u;
            v >>= 1;
        }
    }
    return distance;
}

bool same_descriptor(const Descriptor& a, const Descriptor& b) { return hamming(a, b) == 0; }

// Bitwise, so keypoints holding NaN compare equal to themselves.
bool same_keypoint(const Keypoint& a, const Keypoint& b) {
    return std::memcmp(&a, &b, sizeof(Keypoint)) == 0;
}

// Describes a single keypoint; requires that it survives.
Descriptor describe_one(const GrayImage& image, const Keypoint& k) {
    std::vector<Keypoint> kps(1, k);
    std::vector<Descriptor> ds;
    require(v0_describe(image, kps, ds, Config()) == ErrorCode::Success && ds.size() == 1,
            "single keypoint is described");
    return ds[0];
}

void fill_noise(GrayFixture& f, TestRandom& random) {
    for (std::int32_t y = 0; y < f.image.height; ++y)
        for (std::int32_t x = 0; x < f.image.width; ++x) f.at(x, y) = random.unit();
}

void test_pattern_table() {
    std::set<std::pair<std::pair<int, int>, std::pair<int, int>>> seen;
    for (int k = 0; k < kBriefTests; ++k) {
        const BriefTest& t = kBriefPattern[k];
        const int v[4] = {t.ax, t.ay, t.bx, t.by};
        for (int i = 0; i < 4; ++i)
            require(v[i] >= -kBriefPatchRadius && v[i] <= kBriefPatchRadius, "offset inside patch");
        require(t.ax != t.bx || t.ay != t.by, "test compares two different points");
        const auto first = std::make_pair(static_cast<int>(t.ax), static_cast<int>(t.ay));
        const auto second = std::make_pair(static_cast<int>(t.bx), static_cast<int>(t.by));
        require(seen.count(std::make_pair(first, second)) == 0 &&
                    seen.count(std::make_pair(second, first)) == 0,
                "no repeated or mirrored test");
        seen.insert(std::make_pair(first, second));
    }
}

void test_bit_convention_with_ramps() {
    // Horizontal ramp: the first point is darker exactly when ax < bx; equal x gives 0.
    GrayFixture horizontal(100, 60);
    GrayFixture vertical(60, 100);
    for (std::int32_t y = 0; y < 60; ++y)
        for (std::int32_t x = 0; x < 100; ++x) {
            horizontal.at(x, y) = 0.2f + 0.001f * static_cast<float>(x);
            vertical.at(y, x) = 0.2f + 0.001f * static_cast<float>(x);
        }
    const Descriptor h = describe_one(horizontal.image, keypoint(50.0f, 30.0f));
    const Descriptor v = describe_one(vertical.image, keypoint(30.0f, 50.0f));
    int ones = 0;
    for (int k = 0; k < kBriefTests; ++k) {
        const BriefTest& t = kBriefPattern[k];
        require(bit(h, k) == (t.ax < t.bx), "bit k of data[k / 32] follows the x ramp");
        require(bit(v, k) == (t.ay < t.by), "bit k of data[k / 32] follows the y ramp");
        ones += bit(h, k) ? 1 : 0;
    }
    require(ones > 64 && ones < 192, "ramp descriptor mixes zeros and ones");
}

void test_repeat_rounding_and_translation() {
    TestRandom random(21);
    GrayFixture a(200, 150);
    paint_rectangles(a, random, 150);
    const Descriptor d1 = describe_one(a.image, keypoint(100.0f, 80.0f));
    const Descriptor d2 = describe_one(a.image, keypoint(100.0f, 80.0f));
    require(same_descriptor(d1, d2), "same point, same image, same descriptor");
    require(same_descriptor(describe_one(a.image, keypoint(99.6f, 80.4f)), d1),
            "keypoint is sampled at its rounded centre");
    require(same_descriptor(describe_one(a.image, keypoint(100.49f, 79.5f)), d1),
            "x.5 rounds up, below x.5 rounds down");

    // B(x, y) = A(x + 7, y - 5): A's (100, 80) is B's (93, 85).
    GrayFixture b(200, 150, 0, 0.5f);
    for (std::int32_t y = 0; y < 150; ++y)
        for (std::int32_t x = 0; x < 200; ++x)
            if (x + 7 < 200 && y - 5 >= 0) b.at(x, y) = a.at(x + 7, y - 5);
    for (int i = 0; i < 40; ++i) {
        const std::int32_t xa = 40 + random.below(120);
        const std::int32_t ya = 40 + random.below(70);
        require(same_descriptor(describe_one(a.image, keypoint(static_cast<float>(xa), static_cast<float>(ya))),
                                describe_one(b.image, keypoint(static_cast<float>(xa - 7),
                                                               static_cast<float>(ya + 5)))),
                "integer translation keeps the descriptor");
    }
}

void test_compaction_and_order() {
    TestRandom random(4);
    const std::int32_t w = 90;
    const std::int32_t h = 70;
    GrayFixture f(w, h);
    fill_noise(f, random);
    std::vector<Keypoint> input;
    input.push_back(keypoint(15.0f, 15.0f, 1.0f));                // kept: smallest centre
    input.push_back(keypoint(14.4f, 20.0f, 2.0f));                // dropped: rounds to 14
    input.push_back(keypoint(14.5f, 20.0f, 3.0f));                // kept: rounds to 15
    input.push_back(keypoint(w - 16.0f, h - 16.0f, 4.0f));        // kept: largest centre
    input.push_back(keypoint(w - 15.5f, 30.0f, 5.0f));            // dropped: rounds to w - 15
    input.push_back(keypoint(40.0f, h - 15.0f, 6.0f));            // dropped
    input.push_back(keypoint(-1e30f, 30.0f, 7.0f));               // dropped
    input.push_back(keypoint(40.0f, 1e30f, 8.0f));                // dropped
    input.push_back(keypoint(45.0f, 35.0f, 9.0f));                // kept
    input.push_back(keypoint(45.0f, 35.0f, 10.0f));               // kept: duplicates stay
    const float kept_scores[] = {1.0f, 3.0f, 4.0f, 9.0f, 10.0f};

    std::vector<Keypoint> kps = input;
    std::vector<Descriptor> ds(3);
    require(v0_describe(f.image, kps, ds, Config()) == ErrorCode::Success, "mixed list succeeds");
    require(kps.size() == 5 && ds.size() == 5, "border keypoints are dropped from both arrays");
    for (std::size_t i = 0; i < kps.size(); ++i) {
        require(kps[i].score == kept_scores[i], "survivors keep their original order");
        require(same_descriptor(ds[i], describe_one(f.image, kps[i])), "descriptors[i] belongs to keypoints[i]");
    }
    require(same_descriptor(ds[3], ds[4]), "duplicate keypoints get equal descriptors");
    require(reinterpret_cast<std::uintptr_t>(ds.data()) % 16 == 0, "descriptor array is 16-byte aligned");

    GrayFixture tiny(30, 40);
    fill_noise(tiny, random);
    kps.assign(1, keypoint(15.0f, 20.0f));
    require(v0_describe(tiny.image, kps, ds, Config()) == ErrorCode::Success && kps.empty() && ds.empty(),
            "image narrower than the patch drops every keypoint");
    kps.clear();
    ds.assign(2, Descriptor());
    require(v0_describe(f.image, kps, ds, Config()) == ErrorCode::Success && kps.empty() && ds.empty(),
            "empty keypoint list gives empty arrays");
}

void test_distances_and_input_untouched() {
    TestRandom random(77);
    GrayFixture packed(160, 120);
    fill_noise(packed, random);
    GrayFixture padded(160, 120, 5);
    for (std::int32_t y = 0; y < 120; ++y)
        for (std::int32_t x = 0; x < 160; ++x) padded.at(x, y) = packed.at(x, y);
    const std::vector<float> before = padded.storage;

    std::vector<Keypoint> kps;
    for (int i = 0; i < 60; ++i)
        kps.push_back(keypoint(static_cast<float>(20 + random.below(120)),
                               static_cast<float>(20 + random.below(80))));
    std::vector<Keypoint> kps_padded = kps;
    std::vector<Descriptor> ds;
    std::vector<Descriptor> ds_padded;
    require(v0_describe(packed.image, kps, ds, Config()) == ErrorCode::Success, "noise succeeds");
    require(v0_describe(padded.image, kps_padded, ds_padded, Config()) == ErrorCode::Success,
            "padded noise succeeds");
    require(padded.storage == before, "input pixels and padding are not modified");
    require(ds.size() == ds_padded.size(), "padding keeps the count");
    double total = 0.0;
    int pairs = 0;
    for (std::size_t i = 0; i < ds.size(); ++i) {
        require(same_descriptor(ds[i], ds_padded[i]), "row padding does not change descriptors");
        for (std::size_t j = i + 1; j < ds.size(); ++j) {
            if (kps[i].x == kps[j].x && kps[i].y == kps[j].y) continue;
            total += hamming(ds[i], ds[j]);
            ++pairs;
        }
    }
    const double mean = total / pairs;
    require(mean > 110.0 && mean < 146.0, "different points on noise differ in about half the bits");
}

void test_invalid_inputs_and_allocation() {
    TestRandom random(9);
    GrayFixture f(64, 64);
    fill_noise(f, random);
    const float nan = std::numeric_limits<float>::quiet_NaN();
    const float inf = std::numeric_limits<float>::infinity();
    const std::vector<Keypoint> good(3, keypoint(30.0f, 30.0f));
    auto expect = [&](const GrayImage& image, std::vector<Keypoint> kps, ErrorCode code,
                      const char* message) {
        const std::vector<Keypoint> original = kps;
        std::vector<Descriptor> ds(2);
        require(v0_describe(image, kps, ds, Config()) == code && ds.empty(), message);
        require(kps.size() == original.size(), "keypoints unchanged on error");
        for (std::size_t i = 0; i < kps.size(); ++i)
            require(same_keypoint(kps[i], original[i]), "keypoints unchanged on error");
    };

    std::vector<Keypoint> bad_points = good;
    bad_points[1].x = nan;
    expect(f.image, bad_points, ErrorCode::InvalidArgument, "NaN x");
    bad_points = good;
    bad_points[2].y = -inf;
    expect(f.image, bad_points, ErrorCode::InvalidArgument, "infinite y");

    GrayImage bad = f.image;
    bad.data = nullptr;
    expect(bad, good, ErrorCode::InvalidImage, "null image");
    expect(bad, bad_points, ErrorCode::InvalidImage, "image error reported before keypoint error");
    bad = f.image;
    bad.channels = 3;
    expect(bad, good, ErrorCode::InvalidImage, "three channels");
    bad = f.image;
    bad.stride = 64;
    expect(bad, good, ErrorCode::InvalidImage, "stride in elements");
    bad = f.image;
    bad.width = 0;
    expect(bad, good, ErrorCode::InvalidImage, "zero width");

    std::vector<Keypoint> kps = good;
    kps.reserve(16);
    std::vector<Descriptor> ds(1);
    ds.reserve(16);
    fail_allocations = true;
    const ErrorCode status = v0_describe(f.image, kps, ds, Config());
    fail_allocations = false;
    require(status == ErrorCode::AllocationFailed && ds.empty() && kps.size() == good.size(),
            "bad_alloc maps to AllocationFailed and keeps keypoints");
}

}  // namespace

int main() {
    try {
        test_pattern_table();
        test_bit_convention_with_ramps();
        test_repeat_rounding_and_translation();
        test_compaction_and_order();
        test_distances_and_input_untouched();
        test_invalid_inputs_and_allocation();
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " assertions: " << error.what() << '\n';
        return 1;
    }
    std::cout << "PASS: " << checks << " assertions for S3 BRIEF description" << '\n';
    return 0;
}
