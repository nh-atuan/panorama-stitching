// Authors: Le Ha Thanh Chuong (23120195)
// External source: none
// Shared fixture and comparison helpers extracted from the P7 V2 pipeline suite.

#ifndef GROUP16_GPU_PIPELINE_TEST_SUPPORT_CUH
#define GROUP16_GPU_PIPELINE_TEST_SUPPORT_CUH

#include "common/v0_config.h"
#include "gpu/s45_test_support.cuh"
#include "support/v0_reference.h"
#include "v1/v1_pipeline.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace pipeline_test {

using namespace panorama;
using gpu_test::RgbImage;
using gpu_test::Stream;
using gpu_test::cuda;
using gpu_test::load_rgb_image;
using gpu_test::make_test_image;
using gpu_test::require;

constexpr int kGrid = 20;
constexpr double kTruthRmsePx = 0.5;
constexpr double kTruthMaxPx = 1.0;
constexpr double kDriftPx = 0.1;
constexpr int kRgbTolerance = 1;
using Matrix = std::array<double, 9>;

struct GpuOutput {
    V1DeviceOwner owner;
    Panorama canvas;
};

inline void upload_images(const Image& a, const Image& b, DeviceWorkspace& ws, cudaStream_t stream) {
    cuda(cudaMemcpyAsync(ws.d_imageA, a.data, a.stride * static_cast<std::size_t>(a.height),
                         cudaMemcpyHostToDevice, stream));
    cuda(cudaMemcpyAsync(ws.d_imageB, b.data, b.stride * static_cast<std::size_t>(b.height),
                         cudaMemcpyHostToDevice, stream));
}

template<class Prepare, class RunStages>
ErrorCode run_gpu(const Image& a, const Image& b, const Config& config, GpuOutput& output,
                  Prepare prepare, RunStages run_stages) {
    const ErrorCode prepared = prepare(a, b, config, output.owner);
    if (prepared != ErrorCode::Success) return prepared;

    Stream stream;
    DeviceWorkspace& ws = output.owner.view;
    upload_images(a, b, ws, stream.value);
    V1StageFailure failure{};
    const ErrorCode status = run_stages(ws, config, stream.value, V1StageTrace{}, failure);
    stream.wait();
    output.canvas = ws.canvas;
    return status;
}

inline ErrorCode run_v1(const Image& a, const Image& b, const Config& config, GpuOutput& output) {
    return run_gpu(a, b, config, output, v1_prepare, v1_run_stages);
}

inline Matrix as_matrix(const Homography& homography) {
    Matrix result{};
    std::copy_n(homography.data, result.size(), result.begin());
    return result;
}

inline Matrix read_homography(const GpuOutput& output, const std::string& label) {
    require(output.owner.view.d_homography != nullptr, label + ": missing Device H");
    Homography homography{};
    cuda(cudaMemcpy(&homography, output.owner.view.d_homography, sizeof(homography),
                    cudaMemcpyDeviceToHost));
    return as_matrix(homography);
}

struct Projection {
    double x, y, w;
};

inline Projection project(const Matrix& h, double x, double y, const std::string& label) {
    const double w = h[6] * x + h[7] * y + h[8];
    if (w == 0.0 || !std::isfinite(w)) throw std::runtime_error(label + ": invalid H denominator");
    const double px = (h[0] * x + h[1] * y + h[2]) / w;
    const double py = (h[3] * x + h[4] * y + h[5]) / w;
    if (!std::isfinite(px) || !std::isfinite(py)) {
        throw std::runtime_error(label + ": non-finite H projection");
    }
    return {px, py, w};
}

struct ProjectionError {
    double rmse = 0.0, maximum = 0.0;
    int points = 0;
};

inline ProjectionError projection_error(const Image& a, const Image& b, const Matrix& estimate,
                                        const Matrix& reference, const Matrix* truth, const std::string& label) {
    ProjectionError result;
    double squared = 0.0;
    double estimate_w = 0.0, reference_w = 0.0;
    for (int iy = 0; iy < kGrid; ++iy) {
        const double y = static_cast<double>(b.height - 1) * iy / (kGrid - 1);
        for (int ix = 0; ix < kGrid; ++ix) {
            const double x = static_cast<double>(b.width - 1) * ix / (kGrid - 1);
            // For synthetic images the mask is defined only by H_gt, never by the estimate.
            if (truth) {
                const Projection q = project(*truth, x, y, label);
                if (q.x < 0.0 || q.x > a.width - 1 || q.y < 0.0 || q.y > a.height - 1) continue;
            }
            const Projection p = project(estimate, x, y, label);
            const Projection q = project(reference, x, y, label);
            if (result.points && (std::signbit(p.w) != std::signbit(estimate_w) ||
                                  std::signbit(q.w) != std::signbit(reference_w))) {
                throw std::runtime_error(label + ": H crosses the projective horizon on Q");
            }
            estimate_w = p.w;
            reference_w = q.w;
            const double error = std::hypot(p.x - q.x, p.y - q.y);
            squared += error * error;
            result.maximum = std::max(result.maximum, error);
            ++result.points;
        }
    }
    require(result.points > 0, label + ": empty projection grid");
    result.rmse = std::sqrt(squared / result.points);
    return result;
}

inline std::string metric_text(const ProjectionError& error) {
    std::ostringstream message;
    message << std::setprecision(9) << "points=" << error.points << " rmse=" << error.rmse
            << " px max=" << error.maximum << " px";
    return message.str();
}

inline std::string geometry(const Panorama& canvas) {
    return std::to_string(canvas.image.width) + "x" + std::to_string(canvas.image.height) + " offset=(" +
           std::to_string(canvas.offset_x) + "," + std::to_string(canvas.offset_y) + ")";
}

inline void check_canvas(const Panorama& expected, const Panorama& actual, const std::string& label) {
    require(expected.image.width == actual.image.width && expected.image.height == actual.image.height &&
                expected.offset_x == actual.offset_x && expected.offset_y == actual.offset_y,
            label + ": S5 -> S6 canvas mismatch: expected " + geometry(expected) + ", got " + geometry(actual));
}

inline std::size_t canvas_bytes(const Image& image, const std::string& label) {
    require(image.width > 0 && image.height > 0 && image.channels == 3 && image.data &&
                image.stride >= static_cast<std::size_t>(image.width) * 3 &&
                static_cast<std::size_t>(image.height) <= std::numeric_limits<std::size_t>::max() / image.stride,
            label + ": invalid RGB canvas layout");
    return image.stride * static_cast<std::size_t>(image.height);
}

inline std::vector<std::uint8_t> download_canvas(const GpuOutput& output, const std::string& label) {
    const Image& image = output.canvas.image;
    const DeviceWorkspace& ws = output.owner.view;
    const std::size_t bytes = canvas_bytes(image, label);
    require(image.data == ws.d_canvas && ws.d_panorama == ws.d_canvas && bytes <= ws.canvas_capacity_bytes,
            label + ": invalid Device canvas ownership or capacity");
    std::vector<std::uint8_t> pixels(bytes);
    cuda(cudaMemcpy(pixels.data(), image.data, bytes, cudaMemcpyDeviceToHost));
    return pixels;
}

struct PixelError {
    int maximum = 0;
    int x = 0, y = 0, channel = 0;
};

inline PixelError compare_rgb(const Image& a, const Image& b) {
    PixelError result;
    const std::size_t active_bytes = static_cast<std::size_t>(a.width) * 3;
    for (int y = 0; y < a.height; ++y) {
        const auto* row_a = a.data + static_cast<std::size_t>(y) * a.stride;
        const auto* row_b = b.data + static_cast<std::size_t>(y) * b.stride;
        for (std::size_t i = 0; i < active_bytes; ++i) {
            const int delta = std::abs(static_cast<int>(row_a[i]) - static_cast<int>(row_b[i]));
            if (delta > result.maximum) {
                result.maximum = delta;
                result.x = static_cast<int>(i / 3);
                result.y = y;
                result.channel = static_cast<int>(i % 3);
            }
        }
    }
    return result;
}

inline Config fixture_config(const Image& image) {
    Config config;
    require(make_v0_config(image.width, image.height, config) == ErrorCode::Success, "fixture config");
    return config;
}

inline RgbImage crop(const RgbImage& scene, int width, int height, int ox, int oy) {
    RgbImage result;
    result.width = width;
    result.height = height;
    const std::size_t row_bytes = static_cast<std::size_t>(width) * 3;
    result.bytes.resize(row_bytes * height);
    for (int y = 0; y < height; ++y) {
        std::memcpy(result.bytes.data() + static_cast<std::size_t>(y) * row_bytes,
                    scene.bytes.data() + (static_cast<std::size_t>(oy + y) * scene.width + ox) * 3,
                    row_bytes);
    }
    return result;
}

template<class Compare>
void test_embedded_synthetic(const Compare& compare) {
    const struct Fixture { int width, height, dx, dy; std::uint32_t seed; } fixtures[] = {
        {320, 240, 28, -6, 2026}, {480, 320, 37, -11, 42}, {640, 480, -40, 14, 999},
        {320, 240, -24, 10, 2026}, {480, 320, -33, -9, 42}, {640, 480, 44, 12, 999},
    };
    for (const auto& fixture : fixtures) {
        const auto scene = make_test_image(fixture.width + std::abs(fixture.dx) + 40,
                                           fixture.height + std::abs(fixture.dy) + 40, fixture.seed);
        // Retain the V1 origins where they fit, and keep negative shifts inside the scene.
        const int x = std::max(20, -fixture.dx), y = std::max(20, -fixture.dy);
        auto left = crop(scene, fixture.width, fixture.height, x, y);
        auto right = crop(scene, fixture.width, fixture.height, x + fixture.dx, y + fixture.dy);
        const Matrix truth = {{1, 0, static_cast<double>(fixture.dx), 0, 1,
                               static_cast<double>(fixture.dy), 0, 0, 1}};
        const std::string name = "translation " + std::to_string(fixture.width) + "x" +
                                 std::to_string(fixture.height) + " dx=" + std::to_string(fixture.dx) +
                                 " dy=" + std::to_string(fixture.dy);
        compare(left.view(), right.view(), fixture_config(left.view()), name, ErrorCode::Success, &truth);
    }
}

template<class Compare>
void test_edge_cases(const Compare& compare) {
    auto left = make_test_image(160, 120, 1);
    auto right = make_test_image(160, 120, 2);
    Image invalid = left.view();
    invalid.width = 0;
    const Config config = fixture_config(left.view());
    compare(invalid, right.view(), config, "zero width A", ErrorCode::InvalidImage, nullptr);
    compare(left.view(), invalid, config, "zero width B", ErrorCode::InvalidImage, nullptr);
    Config bad_config = config;
    bad_config.max_keypoints = 0;
    compare(left.view(), right.view(), bad_config, "zero max_keypoints", ErrorCode::InvalidConfig, nullptr);

    auto tiny_a = make_test_image(24, 24, 1);
    auto tiny_b = make_test_image(24, 24, 2);
    compare(tiny_a.view(), tiny_b.view(), fixture_config(tiny_a.view()), "tiny images",
            ErrorCode::InsufficientKeypoints, nullptr);
    std::fill(left.bytes.begin(), left.bytes.end(), 128);
    compare(left.view(), left.view(), config, "blank images", ErrorCode::InsufficientKeypoints, nullptr);
}

template<class Compare>
void test_file_pair(const std::string& left_path, const std::string& right_path, const std::string& label,
                    ErrorCode expected, const Compare& compare, const Matrix* truth = nullptr) {
    RgbImage left, right;
    require(load_rgb_image(left_path.c_str(), left), label + ": could not decode " + left_path);
    require(load_rgb_image(right_path.c_str(), right), label + ": could not decode " + right_path);
    compare(left.view(), right.view(), fixture_config(left.view()), label, expected, truth);
}

template<class Compare>
void test_dataset(const std::string& root, const Compare& compare) {
    for (const std::string site : {"site1", "site2", "site3", "challenge"}) {
        for (const std::string size : {"small", "medium", "large"}) {
            const std::string label = site + "/" + size;
            const std::string path = root + "/" + label;
            const ErrorCode expected = site == "challenge" && size != "small" ?
                                       ErrorCode::NumericalFailure : ErrorCode::Success;
            test_file_pair(path + "_left.jpg", path + "_right.jpg", label, expected, compare);
        }
    }
}

struct SyntheticFilePair {
    std::string label, left, right;
    Matrix truth{};
};

struct Options {
    bool require_production = false;
    std::string dataset;
    std::vector<std::string> pair;
    std::vector<SyntheticFilePair> synthetic;
};

inline Options parse_options(int argc, char** argv, const char* require_pipeline_flag) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == require_pipeline_flag) {
            options.require_production = true;
        } else if (arg == "--dataset" && i + 1 < argc && options.dataset.empty()) {
            options.dataset = argv[++i];
        } else if (arg == "--synthetic-pair" && argc - i > 12) {
            SyntheticFilePair pair;
            pair.label = argv[++i];
            pair.left = argv[++i];
            pair.right = argv[++i];
            for (double& value : pair.truth) {
                const char* token = argv[++i];
                char* end = nullptr;
                value = std::strtod(token, &end);
                if (end == token || *end || !std::isfinite(value)) {
                    throw std::runtime_error(pair.label + ": invalid H_gt coefficient");
                }
            }
            options.synthetic.push_back(pair);
        } else if (!arg.empty() && arg[0] != '-' && options.pair.size() < 2) {
            options.pair.push_back(arg);
        } else {
            throw std::runtime_error("invalid argument: " + arg);
        }
    }
    if ((!options.pair.empty() && options.pair.size() != 2) ||
        (!options.pair.empty() && !options.dataset.empty())) {
        throw std::runtime_error("provide either --dataset DIR or two positional image paths");
    }
    if (!options.synthetic.empty() && options.synthetic.size() != 6) {
        throw std::runtime_error("provide all six synthetic pairs");
    }
    return options;
}

template<class Compare>
void run_fixtures(const Options& options, const Compare& compare) {
    if (options.synthetic.empty()) {
        test_embedded_synthetic(compare);
    } else {
        for (const auto& pair : options.synthetic) {
            test_file_pair(pair.left, pair.right, pair.label, ErrorCode::Success, compare, &pair.truth);
        }
    }
    test_edge_cases(compare);
    if (!options.dataset.empty()) {
        test_dataset(options.dataset, compare);
    } else if (!options.pair.empty()) {
        test_file_pair(options.pair[0], options.pair[1], "dataset_pair", ErrorCode::Success, compare);
    } else {
        const char* left = "dataset/site1/small_left.jpg";
        const char* right = "dataset/site1/small_right.jpg";
        if (std::ifstream(left).good() || std::ifstream(right).good()) {
            test_file_pair(left, right, "site1/small", ErrorCode::Success, compare);
        } else {
            std::cout << "SKIP dataset: default site1/small files are absent\n";
        }
    }
}

}  // namespace pipeline_test

#endif
