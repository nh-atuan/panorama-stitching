// Authors: Le Ha Thanh Chuong (23120195)
// External source: none
// Adapted from: tests/gpu/test_gpu_v1_pipeline.cu by Nguyen Ho Anh Tuan (23120185)

#include "common/v0_config.h"
#include "gpu/s45_test_support.cuh"
#include "support/v0_reference.h"
#include "v0/v0_pipeline.h"
#include "v1/v1_pipeline.h"
#include "v1/v1_warp_blend.h"

#ifdef V2_PIPELINE_AVAILABLE
#include "v2/v2_pipeline.h"
#else
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
#include "v1/s3/v1_describe.h"
#include "v1/s4/v1_match.h"
#include "v2/s5/v2_homography.h"
#endif

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

using namespace panorama;
using namespace gpu_test;

namespace {

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

void upload_images(const Image& a, const Image& b, DeviceWorkspace& ws, cudaStream_t stream) {
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

ErrorCode run_v1(const Image& a, const Image& b, const Config& config, GpuOutput& output) {
    return run_gpu(a, b, config, output, v1_prepare, v1_run_stages);
}

#ifndef V2_PIPELINE_AVAILABLE
// Test-only dispatcher: exercise the real V2 S5 and the unchanged V1 stages.
ErrorCode run_v2_pipeline(const Image& imgA, const Image& imgB, const Config& config,
                          DeviceWorkspace& ws, Panorama& out_pano, TimingStats&) {
    V1DeviceOwner allocation;
    const ErrorCode prepared = v1_prepare(imgA, imgB, config, allocation);
    if (prepared != ErrorCode::Success) return prepared;

    DeviceWorkspace& prepared_ws = allocation.view;
    const std::size_t needed = v2_homography_scratch_bytes(prepared_ws.match_capacity);
    if (!needed) return ErrorCode::AllocationFailed;
    if (needed > prepared_ws.scratch_capacity_bytes) {
        device_free(prepared_ws.d_scratch);
        device_allocate(prepared_ws.d_scratch, needed);
        prepared_ws.scratch_capacity_bytes = needed;
    }
    ws = prepared_ws;
    prepared_ws = DeviceWorkspace{};

    Stream stream;
    upload_images(imgA, imgB, ws, stream.value);
    using StageFunction = ErrorCode (*)(DeviceWorkspace&, const Config&, cudaStream_t);
    const StageFunction stages[] = {
        v1_preprocess, v1_detect, v1_describe, v1_match, v2_homography, v1_warp_blend
    };
    for (const StageFunction stage : stages) {
        const ErrorCode status = stage(ws, config, stream.value);
        cuda(cudaGetLastError());
        if (status != ErrorCode::Success) {
            if (stage == v1_warp_blend) {
                const DeviceCounts counts = v1_read_counts(ws, stream.value);
                return counts.status == ErrorCode::Success ? status : counts.status;
            }
            stream.wait();
            return status;
        }
    }
    stream.wait();
    out_pano = ws.canvas;
    return ErrorCode::Success;
}
#endif

ErrorCode run_v2(const Image& a, const Image& b, const Config& config, GpuOutput& output) {
#ifdef V2_PIPELINE_AVAILABLE
    return run_gpu(a, b, config, output, v2_prepare, v2_run_stages);
#else
    TimingStats timing{};
    return run_v2_pipeline(a, b, config, output.owner.view, output.canvas, timing);
#endif
}

Matrix as_matrix(const Homography& homography) {
    Matrix result{};
    std::copy_n(homography.data, result.size(), result.begin());
    return result;
}

Matrix read_homography(const GpuOutput& output, const std::string& label) {
    require(output.owner.view.d_homography != nullptr, label + ": missing Device H");
    Homography homography{};
    cuda(cudaMemcpy(&homography, output.owner.view.d_homography, sizeof(homography),
                    cudaMemcpyDeviceToHost));
    return as_matrix(homography);
}

struct Projection {
    double x, y, w;
};

Projection project(const Matrix& h, double x, double y, const std::string& label) {
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

ProjectionError projection_error(const Image& a, const Image& b, const Matrix& estimate,
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

std::string metric_text(const ProjectionError& error) {
    std::ostringstream message;
    message << std::setprecision(9) << "points=" << error.points << " rmse=" << error.rmse
            << " px max=" << error.maximum << " px";
    return message.str();
}

std::string geometry(const Panorama& canvas) {
    return std::to_string(canvas.image.width) + "x" + std::to_string(canvas.image.height) + " offset=(" +
           std::to_string(canvas.offset_x) + "," + std::to_string(canvas.offset_y) + ")";
}

void check_canvas(const Panorama& expected, const Panorama& actual, const std::string& label) {
    require(expected.image.width == actual.image.width && expected.image.height == actual.image.height &&
                expected.offset_x == actual.offset_x && expected.offset_y == actual.offset_y,
            label + ": S5 -> S6 canvas mismatch: expected " + geometry(expected) + ", got " + geometry(actual));
}

std::size_t canvas_bytes(const Image& image, const std::string& label) {
    require(image.width > 0 && image.height > 0 && image.channels == 3 && image.data &&
                image.stride >= static_cast<std::size_t>(image.width) * 3 &&
                static_cast<std::size_t>(image.height) <= std::numeric_limits<std::size_t>::max() / image.stride,
            label + ": invalid RGB canvas layout");
    return image.stride * static_cast<std::size_t>(image.height);
}

std::vector<std::uint8_t> download_canvas(const GpuOutput& output, const std::string& label) {
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

PixelError compare_rgb(const Image& a, const Image& b) {
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

void replay_same_h(const Image& reference, const Panorama& reference_geometry, const Matrix& h,
                   bool same_estimate, const Config& config, GpuOutput& candidate) {
    try {
        DeviceWorkspace& ws = candidate.owner.view;
        Homography shared{};
        std::copy(h.begin(), h.end(), shared.data);
        Stream stream;
        cuda(cudaMemcpyAsync(ws.d_homography, &shared, sizeof(shared), cudaMemcpyHostToDevice, stream.value));
        const ErrorCode status = v1_warp_blend(ws, config, stream.value);
        stream.wait();
        require(status == ErrorCode::Success, "same-H S6 replay failed, status=" +
                std::to_string(static_cast<int>(status)));
        candidate.canvas = ws.canvas;
        check_canvas(reference_geometry, candidate.canvas, "same-H S6 replay");
        auto pixels = download_canvas(candidate, "same-H S6 replay");
        Image image = candidate.canvas.image;
        image.data = pixels.data();
        const int delta = compare_rgb(reference, image).maximum;
        std::cerr << "  same-H replay max RGB=" << delta << ": "
                  << (delta <= kRgbTolerance && !same_estimate ? "difference follows S5 H" :
                      "inspect S6 sampling or canvas handoff") << '\n';
    } catch (const std::exception& error) {
        std::cerr << "  same-H replay could not reproduce the reference canvas: " << error.what() << '\n';
    }
}

struct Summary {
    int comparisons = 0, expected_failures = 0, max_rgb = 0;
};

void compare_case(const Image& a, const Image& b, const Config& config, const std::string& name,
                  ErrorCode expected, Summary& summary, const Matrix* truth = nullptr) {
    V0Workspace v0;
    ErrorCode status0 = v0_prepare(a, b, config, v0);
    if (status0 == ErrorCode::Success) status0 = v0_run(a, b, config, v0, nullptr, nullptr);
    GpuOutput v1, v2;
    const ErrorCode status1 = run_v1(a, b, config, v1);
    const ErrorCode status2 = run_v2(a, b, config, v2);

    // Tier 1: require the expected result independently for each version.
    require(status0 == expected && status1 == expected && status2 == expected,
            name + ": Tier 1 expected=" + std::to_string(static_cast<int>(expected)) +
            " statuses V0/V1/V2=" + std::to_string(static_cast<int>(status0)) + "/" +
            std::to_string(static_cast<int>(status1)) + "/" + std::to_string(static_cast<int>(status2)));
    if (expected != ErrorCode::Success) {
        ++summary.expected_failures;
        std::cout << name << ": Tier 1 expected error=" << static_cast<int>(expected) << '\n';
        return;
    }

    // Tier 2: use geometric deltas so equivalent scalings of H compare equally.
    const Matrix matrices[] = {as_matrix(v0.homography), read_homography(v1, name + " V1"),
                               read_homography(v2, name + " V2")};
    if (truth) {
        for (int version = 0; version < 3; ++version) {
            const std::string label = name + " Tier 2 V" + std::to_string(version) + " vs H_gt";
            const ProjectionError error = projection_error(a, b, matrices[version], *truth, truth, label);
            std::cout << label << ": " << metric_text(error) << '\n';
            require(error.rmse <= kTruthRmsePx && error.maximum <= kTruthMaxPx,
                    label + ": ground-truth tolerance exceeded: " + metric_text(error));
        }
    }
    const std::string h01 = name + " Tier 2 V0/V1";
    const std::string h12 = name + " Tier 2 V1/V2";
    const std::string h02 = name + " Tier 2 V0/V2";
    const ProjectionError drift01 = projection_error(a, b, matrices[0], matrices[1], truth, h01);
    const ProjectionError drift12 = projection_error(a, b, matrices[1], matrices[2], truth, h12);
    const ProjectionError drift02 = projection_error(a, b, matrices[0], matrices[2], truth, h02);
    std::cout << h12 << ": " << metric_text(drift12) << " tolerance < " << kDriftPx << " px\n";
    require(drift01.maximum < kDriftPx, h01 + ": H drift exceeds tolerance: " + metric_text(drift01));
    require(drift12.maximum < kDriftPx, h12 + ": S5 H drift exceeds tolerance: " + metric_text(drift12));
    require(drift02.maximum < kDriftPx, h02 + ": S5 H drift exceeds tolerance: " + metric_text(drift02));

    // Tier 3: require exact dimensions and offsets before downloading either canvas.
    check_canvas(v0.panorama, v1.canvas, name + " Tier 3 V0/V1");
    check_canvas(v0.panorama, v2.canvas, name + " Tier 3 V0/V2");
    canvas_bytes(v0.panorama.image, name + " Tier 3 V0");
    auto pixels1 = download_canvas(v1, name + " Tier 3 V1");
    auto pixels2 = download_canvas(v2, name + " Tier 3 V2");

    // Tier 4: compare logical RGB bytes, including the defined black background, without padding.
    Image canvases[] = {v0.panorama.image, v1.canvas.image, v2.canvas.image};
    canvases[1].data = pixels1.data();
    canvases[2].data = pixels2.data();
    const int pairs[][2] = {{0, 1}, {1, 2}, {0, 2}};
    const ProjectionError drifts[] = {drift01, drift12, drift02};
    for (int i = 0; i < 3; ++i) {
        const int first = pairs[i][0], second = pairs[i][1];
        const PixelError error = compare_rgb(canvases[first], canvases[second]);
        summary.max_rgb = std::max(summary.max_rgb, error.maximum);
        if (error.maximum > kRgbTolerance) {
            std::cerr << name << " triage V" << first << "/V" << second << ": Tier 2 "
                      << metric_text(drifts[i]) << "; Tier 3 exact " << geometry(v0.panorama)
                      << "; RGB max=" << error.maximum << " at (" << error.x << ',' << error.y
                      << ") channel=" << error.channel << '\n';
            replay_same_h(canvases[first], v0.panorama, matrices[first], matrices[first] == matrices[second],
                          config, second == 1 ? v1 : v2);
        }
        require(error.maximum <= kRgbTolerance, name + " Tier 4: RGB tolerance exceeded");
    }
    ++summary.comparisons;
}

Config fixture_config(const Image& image) {
    Config config;
    require(make_v0_config(image.width, image.height, config) == ErrorCode::Success, "fixture config");
    return config;
}

RgbImage crop(const RgbImage& scene, int width, int height, int ox, int oy) {
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

void test_embedded_synthetic(Summary& summary) {
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
        compare_case(left.view(), right.view(), fixture_config(left.view()), name,
                     ErrorCode::Success, summary, &truth);
    }
}

void test_edge_cases(Summary& summary) {
    auto left = make_test_image(160, 120, 1);
    auto right = make_test_image(160, 120, 2);
    Image invalid = left.view();
    invalid.width = 0;
    const Config config = fixture_config(left.view());
    compare_case(invalid, right.view(), config, "zero width A", ErrorCode::InvalidImage, summary);
    compare_case(left.view(), invalid, config, "zero width B", ErrorCode::InvalidImage, summary);
    Config bad_config = config;
    bad_config.max_keypoints = 0;
    compare_case(left.view(), right.view(), bad_config, "zero max_keypoints", ErrorCode::InvalidConfig, summary);

    auto tiny_a = make_test_image(24, 24, 1);
    auto tiny_b = make_test_image(24, 24, 2);
    compare_case(tiny_a.view(), tiny_b.view(), fixture_config(tiny_a.view()), "tiny images",
                 ErrorCode::InsufficientKeypoints, summary);
    std::fill(left.bytes.begin(), left.bytes.end(), 128);
    compare_case(left.view(), left.view(), config, "blank images", ErrorCode::InsufficientKeypoints, summary);
}

void test_file_pair(const std::string& left_path, const std::string& right_path, const std::string& label,
                    ErrorCode expected, Summary& summary, const Matrix* truth = nullptr) {
    RgbImage left, right;
    require(load_rgb_image(left_path.c_str(), left), label + ": could not decode " + left_path);
    require(load_rgb_image(right_path.c_str(), right), label + ": could not decode " + right_path);
    compare_case(left.view(), right.view(), fixture_config(left.view()), label, expected, summary, truth);
}

void test_dataset(const std::string& root, Summary& summary) {
    for (const std::string site : {"site1", "site2", "site3", "challenge"}) {
        for (const std::string size : {"small", "medium", "large"}) {
            const std::string label = site + "/" + size;
            const std::string path = root + "/" + label;
            const ErrorCode expected = site == "challenge" && size != "small" ?
                                       ErrorCode::NumericalFailure : ErrorCode::Success;
            test_file_pair(path + "_left.jpg", path + "_right.jpg", label, expected, summary);
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

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--require-v2-pipeline") {
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

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
#ifdef V2_PIPELINE_AVAILABLE
        const char* mode = "production pipeline";
#else
        if (options.require_production) throw std::runtime_error("production V2 pipeline is unavailable");
        const char* mode = "test-only dispatcher smoke";
#endif
        print_gpu();
        std::cout << "V2 mode: " << mode << "; B->A grid=" << kGrid << 'x' << kGrid
                  << "; H_gt RMSE <= " << kTruthRmsePx << " px, max <= " << kTruthMaxPx
                  << " px; RGB max <= " << kRgbTolerance << '\n';

        Summary summary;
        if (options.synthetic.empty()) {
            test_embedded_synthetic(summary);
        } else {
            for (const auto& pair : options.synthetic) {
                test_file_pair(pair.left, pair.right, pair.label, ErrorCode::Success, summary, &pair.truth);
            }
        }
        test_edge_cases(summary);
        if (!options.dataset.empty()) {
            test_dataset(options.dataset, summary);
        } else if (!options.pair.empty()) {
            test_file_pair(options.pair[0], options.pair[1], "dataset_pair", ErrorCode::Success, summary);
        } else {
            const char* left = "dataset/site1/small_left.jpg";
            const char* right = "dataset/site1/small_right.jpg";
            if (std::ifstream(left).good() || std::ifstream(right).good()) {
                test_file_pair(left, right, "site1/small", ErrorCode::Success, summary);
            } else {
                std::cout << "SKIP dataset: default site1/small files are absent\n";
            }
        }
        std::cout << "PASS GPU V2 pipeline (" << mode << "): " << checks() << " checks, "
                  << summary.comparisons << " successful comparisons, " << summary.expected_failures
                  << " expected errors, max RGB error=" << summary.max_rgb << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL GPU V2 pipeline: " << error.what() << '\n';
        return 1;
    }
}
