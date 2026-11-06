// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// Integration test suite for the complete V1 GPU pipeline (S1..S6 end-to-end):
// verifies v1_prepare, v1_run_stages, homography, canvas geometry, and output pixels
// against the golden sequential V0 pipeline on synthetic and dataset image pairs.

#include "v1/v1_pipeline.h"
#include "v0/v0_pipeline.h"
#include "common/v0_config.h"
#include "gpu/s45_test_support.cuh"
#include "support/gpu_compare.h"
#include "support/v0_reference.h"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

using namespace panorama;
using namespace gpu_test;

namespace {

int g_comparisons = 0;
int g_max_rgb_diff = 0;

struct V0Output {
    V0Workspace workspace;
    ErrorCode status = ErrorCode::Success;
    Stage failed_stage = Stage::Preprocess;
    HomographyReport report{};
};

V0Output run_v0(const Image& left, const Image& right, const Config& config) {
    V0Output out;
    ErrorCode prep = v0_prepare(left, right, config, out.workspace);
    if (prep != ErrorCode::Success) {
        out.status = prep;
        return out;
    }
    out.status = v0_run(left, right, config, out.workspace, nullptr, &out.failed_stage, &out.report);
    return out;
}

struct V1Output {
    V1DeviceOwner owner;
    ErrorCode status = ErrorCode::Success;
    V1StageFailure failure{};
    std::vector<std::uint8_t> canvas_pixels;
    DeviceCounts counts{};
    Homography homography{};
};

V1Output run_v1(const Image& left, const Image& right, const Config& config, Stream& stream) {
    V1Output out;
    out.status = v1_prepare(left, right, config, out.owner);
    if (out.status != ErrorCode::Success) return out;

    cuda(cudaMemcpyAsync(out.owner.view.d_imageA, left.data,
                         left.stride * static_cast<std::size_t>(left.height),
                         cudaMemcpyHostToDevice, stream.value));
    cuda(cudaMemcpyAsync(out.owner.view.d_imageB, right.data,
                         right.stride * static_cast<std::size_t>(right.height),
                         cudaMemcpyHostToDevice, stream.value));
    DeviceCounts zero_counts{};
    cuda(cudaMemcpyAsync(out.owner.view.d_counts, &zero_counts, sizeof(zero_counts),
                         cudaMemcpyHostToDevice, stream.value));
    stream.wait();

    V1StageTrace trace{};
    out.status = v1_run_stages(out.owner.view, config, stream.value, trace, out.failure);
    stream.wait();

    if (out.status == ErrorCode::Success) {
        out.counts = v1_read_counts(out.owner.view, stream.value);
        cuda(cudaMemcpyAsync(&out.homography, out.owner.view.d_homography,
                             sizeof(Homography), cudaMemcpyDeviceToHost, stream.value));
        const std::size_t canvas_bytes = out.owner.view.canvas.image.stride *
                                         static_cast<std::size_t>(out.owner.view.canvas.image.height);
        out.canvas_pixels.resize(canvas_bytes);
        if (canvas_bytes > 0 && out.owner.view.d_canvas) {
            cuda(cudaMemcpyAsync(out.canvas_pixels.data(), out.owner.view.d_canvas,
                                 canvas_bytes, cudaMemcpyDeviceToHost, stream.value));
        }
        stream.wait();
    }
    return out;
}

void compare_v0_v1(const Image& left, const Image& right, const Config& config,
                   Stream& stream, const std::string& case_name) {
    V0Output v0 = run_v0(left, right, config);
    V1Output v1 = run_v1(left, right, config, stream);

    require(v0.status == v1.status, case_name + ": status mismatch: v0=" +
            std::to_string(static_cast<int>(v0.status)) + ", v1=" +
            std::to_string(static_cast<int>(v1.status)));

    if (v0.status != ErrorCode::Success) {
        // Both rejected with the same error (e.g. failure case).
        return;
    }

    ++g_comparisons;

    // 1. Homography comparison
    const Homography& h0 = v0.workspace.homography;
    const Homography& h1 = v1.homography;
    for (int k = 0; k < 9; ++k) {
        const float diff = std::fabs(h0.data[k] - h1.data[k]);
        require(diff <= 1e-3f, case_name + ": homography component [" + std::to_string(k) +
                "] diff=" + std::to_string(diff));
    }

    // 2. Canvas geometry comparison
    const Panorama& c0 = v0.workspace.panorama;
    const Panorama& c1 = v1.owner.view.canvas;
    require(c0.image.width == c1.image.width, case_name + ": canvas width mismatch");
    require(c0.image.height == c1.image.height, case_name + ": canvas height mismatch");
    require(c0.offset_x == c1.offset_x, case_name + ": offset_x mismatch");
    require(c0.offset_y == c1.offset_y, case_name + ": offset_y mismatch");

    // 3. Output pixel comparison (tolerance: max RGB error <= 1 code per channel)
    const std::int32_t width = c0.image.width;
    const std::int32_t height = c0.image.height;
    const std::size_t stride0 = c0.image.stride;
    const std::size_t stride1 = c1.image.stride;
    const std::uint8_t* p0 = c0.image.data;
    const std::uint8_t* p1 = v1.canvas_pixels.data();

    int local_max_diff = 0;
    for (std::int32_t y = 0; y < height; ++y) {
        const std::uint8_t* row0 = p0 + static_cast<std::size_t>(y) * stride0;
        const std::uint8_t* row1 = p1 + static_cast<std::size_t>(y) * stride1;
        for (std::int32_t x = 0; x < width * 3; ++x) {
            const int diff = std::abs(static_cast<int>(row0[x]) - static_cast<int>(row1[x]));
            if (diff > local_max_diff) local_max_diff = diff;
        }
    }
    if (local_max_diff > g_max_rgb_diff) g_max_rgb_diff = local_max_diff;
    require(local_max_diff <= 1, case_name + ": max RGB diff=" + std::to_string(local_max_diff) + " > 1");
}

// Generates an overlapping pair by translating a textured scene
struct SyntheticTranslatedPair {
    RgbImage scene;
    RgbImage a;
    RgbImage b;

    SyntheticTranslatedPair(std::int32_t w, std::int32_t h, std::int32_t shift_x, std::int32_t shift_y,
                            std::uint32_t seed) {
        const std::int32_t scene_w = w + std::abs(shift_x) + 40;
        const std::int32_t scene_h = h + std::abs(shift_y) + 40;
        scene = make_test_image(scene_w, scene_h, seed);

        const std::int32_t x0_a = 20;
        const std::int32_t y0_a = 20;
        const std::int32_t x0_b = x0_a + shift_x;
        const std::int32_t y0_b = y0_a + shift_y;

        a.width = w;
        a.height = h;
        a.bytes.resize(static_cast<std::size_t>(w) * h * 3);
        b.width = w;
        b.height = h;
        b.bytes.resize(static_cast<std::size_t>(w) * h * 3);

        for (std::int32_t y = 0; y < h; ++y) {
            std::memcpy(a.bytes.data() + static_cast<std::size_t>(y) * w * 3,
                        scene.bytes.data() + (static_cast<std::size_t>(y0_a + y) * scene_w + x0_a) * 3,
                        static_cast<std::size_t>(w) * 3);
            std::memcpy(b.bytes.data() + static_cast<std::size_t>(y) * w * 3,
                        scene.bytes.data() + (static_cast<std::size_t>(y0_b + y) * scene_w + x0_b) * 3,
                        static_cast<std::size_t>(w) * 3);
        }
    }
};

void test_synthetic_cases(Stream& stream) {
    const struct TestCase {
        std::int32_t w;
        std::int32_t h;
        std::int32_t dx;
        std::int32_t dy;
        std::uint32_t seed;
    } cases[] = {
        {320, 240, 28, -6, 2026},
        {480, 320, 37, -11, 42},
        {640, 480, -40, 14, 999},
    };

    for (const auto& c : cases) {
        SyntheticTranslatedPair pair(c.w, c.h, c.dx, c.dy, c.seed);
        Image imgA = pair.a.view();
        Image imgB = pair.b.view();
        Config config;
        require(make_v0_config(c.w, c.h, config) == ErrorCode::Success, "synthetic config");
        const std::string name = "synthetic_" + std::to_string(c.w) + "x" + std::to_string(c.h);
        compare_v0_v1(imgA, imgB, config, stream, name);
    }
}

void test_edge_cases(Stream& stream) {
    // 1. Invalid dimensions
    {
        Image zero_w{};
        zero_w.width = 0; zero_w.height = 100; zero_w.channels = 3; zero_w.stride = 100;
        zero_w.data = reinterpret_cast<std::uint8_t*>(1);
        Image normal = make_test_image(160, 120, 1).view();
        Config config;
        make_v0_config(160, 120, config);
        V1DeviceOwner owner;
        require(v1_prepare(zero_w, normal, config, owner) == ErrorCode::InvalidImage,
                "zero width rejected");
        require(v1_prepare(normal, zero_w, config, owner) == ErrorCode::InvalidImage,
                "zero width right rejected");
    }

    // 2. Negative or zero max_keypoints
    {
        RgbImage a = make_test_image(160, 120, 1);
        RgbImage b = make_test_image(160, 120, 2);
        Config config;
        make_v0_config(160, 120, config);
        config.max_keypoints = 0;
        V1DeviceOwner owner;
        require(v1_prepare(a.view(), b.view(), config, owner) == ErrorCode::InvalidConfig,
                "zero max_keypoints rejected");
    }

    // 3. Side too small for FAST ring (side <= 30)
    {
        RgbImage tiny_a = make_test_image(24, 24, 1);
        RgbImage tiny_b = make_test_image(24, 24, 2);
        Config config;
        make_v0_config(24, 24, config);
        V1DeviceOwner owner;
        // Scratch bytes returns 0 because S2 detects side <= 30, so v1_prepare returns InvalidImage
        require(v1_prepare(tiny_a.view(), tiny_b.view(), config, owner) == ErrorCode::InvalidImage,
                "tiny image <= 30 rejected by v1_prepare");
    }

    // 4. Flat / blank image (insufficient keypoints)
    {
        RgbImage blank_a;
        blank_a.width = 160; blank_a.height = 120;
        blank_a.bytes.assign(160 * 120 * 3, 128);
        RgbImage blank_b = blank_a;
        Config config;
        make_v0_config(160, 120, config);

        V1Output v1 = run_v1(blank_a.view(), blank_b.view(), config, stream);
        require(v1.status == ErrorCode::InsufficientKeypoints,
                "blank image gives InsufficientKeypoints");
    }
}

void test_dataset_if_present(Stream& stream, int argc, char** argv) {
    std::string left_path, right_path;
    if (argc >= 3) {
        left_path = argv[1];
        right_path = argv[2];
    } else {
        left_path = "dataset/site1/small_left.jpg";
        right_path = "dataset/site1/small_right.jpg";
    }

    RgbImage left, right;
    if (!load_rgb_image(left_path.c_str(), left) || !load_rgb_image(right_path.c_str(), right)) {
        return;  // Skip gracefully if dataset files not on local machine
    }

    Config config;
    require(make_v0_config(left.width, left.height, config) == ErrorCode::Success, "dataset config");
    compare_v0_v1(left.view(), right.view(), config, stream, "dataset_pair");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        print_gpu();
        Stream stream;

        test_synthetic_cases(stream);
        test_edge_cases(stream);
        test_dataset_if_present(stream, argc, argv);

        std::cout << "PASS GPU pipeline: " << checks() << " checks, " << g_comparisons
                  << " V0/V1 comparisons; max RGB error=" << g_max_rgb_diff << ", threshold=1\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL GPU pipeline: " << error.what() << '\n';
        return 1;
    }
}
