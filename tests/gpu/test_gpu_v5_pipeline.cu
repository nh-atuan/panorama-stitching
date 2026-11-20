// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: tests/gpu/test_gpu_v4_pipeline.cu by Nguyen Ho Anh Tuan (23120185)
// Changes: Extended integration verification to V5 pipeline (both sequential and dual scheduling), comparing against V0, V1, V2, V3, and V4.

#include "gpu/pipeline_test_support.cuh"
#include "v0/v0_pipeline.h"
#include "v2/v2_pipeline.h"
#include "v3/v3_pipeline.h"
#include "v4/v4_pipeline.h"
#include "v5/v5_pipeline.h"

using namespace pipeline_test;

namespace {

struct Summary {
    int panoramas = 0;
    int expected_failures = 0;
    int max_rgb = 0;
    bool expanded_canvas = false;
};

constexpr double kNormalizedScaleTolerance = std::numeric_limits<float>::epsilon();

void check_normalization(const Matrix& h, const std::string& label) {
    double maximum = 0.0;
    for (double value : h) {
        require(std::isfinite(value), label + ": Tier 2 non-finite H coefficient");
        maximum = std::max(maximum, std::abs(value));
    }
    require(std::abs(maximum - 1.0) <= kNormalizedScaleTolerance,
            label + ": Tier 2 expected max(abs(H)) = 1 within float epsilon, got " +
            std::to_string(maximum));
}

void check_image_a_coverage(const Panorama& canvas, const Image& a, const std::string& label) {
    const auto right = static_cast<std::int64_t>(canvas.offset_x) + a.width;
    const auto bottom = static_cast<std::int64_t>(canvas.offset_y) + a.height;
    require(canvas.offset_x >= 0 && canvas.offset_y >= 0 &&
                right <= canvas.image.width && bottom <= canvas.image.height,
            label + ": Tier 3 canvas does not contain A at a valid offset: " + geometry(canvas));
}

std::string status_text(ErrorCode status) {
    const std::string code = std::to_string(static_cast<unsigned>(status));
    switch (status) {
        case ErrorCode::Success: return "Success (" + code + ")";
        case ErrorCode::InvalidImage: return "InvalidImage (" + code + ")";
        case ErrorCode::InvalidConfig: return "InvalidConfig (" + code + ")";
        case ErrorCode::InsufficientKeypoints: return "InsufficientKeypoints (" + code + ")";
        case ErrorCode::InsufficientMatches: return "InsufficientMatches (" + code + ")";
        case ErrorCode::DegenerateHomography: return "DegenerateHomography (" + code + ")";
        case ErrorCode::NumericalFailure: return "NumericalFailure (" + code + ")";
        case ErrorCode::InvalidCanvas: return "InvalidCanvas (" + code + ")";
        case ErrorCode::AllocationFailed: return "AllocationFailed (" + code + ")";
        case ErrorCode::CudaFailure: return "CudaFailure (" + code + ")";
        default: return "ErrorCode " + code;
    }
}

std::string case_context(const Image& a, const Image& b, const Config& config, const std::string& name) {
    std::ostringstream context;
    context << name << " A=" << a.width << 'x' << a.height << " B=" << b.width << 'x' << b.height << ' ';
    write_config(context, config);
    return context.str();
}

struct V5RunResult {
    V5DeviceOwner owner;
    Panorama canvas;
    std::vector<std::uint8_t> pixels;
};

ErrorCode run_v5(const Image& a, const Image& b, const Config& config,
                V5Schedule schedule, V5RunResult& result, const std::string& label) {
    try {
        const ErrorCode prep = v5_prepare(a, b, config, result.owner);
        if (prep != ErrorCode::Success) return prep;

        KernelTiming kernels;
        V1StageFailure failure;
        const ErrorCode status = v5_run_stages(a, b, config, result.owner, schedule, kernels, false, failure);
        if (status != ErrorCode::Success) return status;

        result.canvas = result.owner.view.canvas;
        const Image& img = result.canvas.image;
        if (img.width > 0 && img.height > 0) {
            const std::size_t cap = static_cast<std::size_t>(img.stride) * img.height;
            result.pixels.resize(cap);
            TimingStats stats;
            V5TimingDetail detail;
            const ErrorCode dl = v5_download(result.owner, result.pixels.data(), cap, false, stats, detail);
            if (dl != ErrorCode::Success) return dl;
            result.canvas.image.data = result.pixels.data();
        }
        return ErrorCode::Success;
    } catch (const std::exception& error) {
        throw std::runtime_error(label + ": V5 pipeline/CUDA exception: " + error.what());
    }
}

Matrix read_v5_homography(const V5RunResult& result, const std::string& label) {
    require(result.owner.view.d_homography != nullptr, label + ": missing Device H");
    Homography homography{};
    cuda(cudaMemcpy(&homography, result.owner.view.d_homography, sizeof(homography),
                    cudaMemcpyDeviceToHost));
    return as_matrix(homography);
}

void check_acceptance_fixtures(const Options& options) {
    if (options.dataset.empty() || options.synthetic.empty()) {
        throw std::runtime_error("V5 acceptance requires --dataset and all six --synthetic-pair fixtures");
    }
    for (const std::string kind : {"translation", "projective"}) {
        for (const std::string size : {"small", "medium", "large"}) {
            const std::string label = kind + "/" + size;
            const auto count = std::count_if(options.synthetic.begin(), options.synthetic.end(),
                                            [&](const SyntheticFilePair& pair) { return pair.label == label; });
            if (count != 1) throw std::runtime_error("V5 acceptance requires exactly one fixture for " + label);
        }
    }
}

void compare_case(const Image& a, const Image& b, const Config& config, const std::string& name,
                  ErrorCode expected, const Matrix* truth, Summary& summary) {
    const std::string context = case_context(a, b, config, name);
    const std::string labels[] = {
        context + " V0", context + " V4", context + " V5_seq", context + " V5_dual"
    };

    V0Workspace v0;
    ErrorCode status0 = v0_prepare(a, b, config, v0);
    if (status0 == ErrorCode::Success) status0 = v0_run(a, b, config, v0, nullptr, nullptr);

    GpuOutput v4;
    const ErrorCode status4 = run_gpu(a, b, config, v4, v4_prepare, v4_run_stages);

    V5RunResult v5_seq, v5_dual;
    const ErrorCode status5_seq = run_v5(a, b, config, V5Schedule::Sequential, v5_seq, labels[2]);
    const ErrorCode status5_dual = run_v5(a, b, config, V5Schedule::DualStream, v5_dual, labels[3]);

    const ErrorCode statuses[] = {status0, status4, status5_seq, status5_dual};

    // Tier 1: compare status before reading any homography or canvas.
    for (int i = 0; i < 4; ++i) {
        require(statuses[i] == expected, labels[i] + " Tier 1: expected " +
                status_text(expected) + ", got " + status_text(statuses[i]));
    }
    if (expected != ErrorCode::Success) {
        ++summary.expected_failures;
        std::cout << name << ": Tier 1 V0/V4/V5 expected " << status_text(expected) << '\n';
        return;
    }

    // Tier 2: check homography matrix.
    const Matrix matrices[] = {
        as_matrix(v0.homography),
        read_homography(v4, labels[1]),
        read_v5_homography(v5_seq, labels[2]),
        read_v5_homography(v5_dual, labels[3])
    };
    for (int i = 0; i < 4; ++i) {
        check_normalization(matrices[i], labels[i]);
    }

    // Check drift vs H_gt on synthetic
    ProjectionError candidate_truth{};
    if (truth) {
        for (int i = 0; i < 4; ++i) {
            const std::string label = labels[i] + " Tier 2 vs H_gt";
            const ProjectionError error = projection_error(a, b, matrices[i], *truth, truth, label);
            if (i == 3) candidate_truth = error;
            require(error.rmse <= kTruthRmsePx && error.maximum <= kTruthMaxPx,
                    label + ": " + metric_text(error) + "; expected RMSE <= " +
                    std::to_string(kTruthRmsePx) + " px and max <= " + std::to_string(kTruthMaxPx) + " px");
        }
    }

    // Check drift of V5 vs V4
    const ProjectionError drift_seq = projection_error(a, b, matrices[2], matrices[1], truth, labels[2] + "/V4 Tier 2");
    const ProjectionError drift_dual = projection_error(a, b, matrices[3], matrices[1], truth, labels[3] + "/V4 Tier 2");
    const ProjectionError drift_modes = projection_error(a, b, matrices[3], matrices[2], truth, "V5_dual/V5_seq Tier 2");

    require(drift_seq.maximum < kDriftPx, labels[2] + "/V4 Tier 2: max drift " + std::to_string(drift_seq.maximum));
    require(drift_dual.maximum < kDriftPx, labels[3] + "/V4 Tier 2: max drift " + std::to_string(drift_dual.maximum));
    require(drift_modes.maximum < 1e-9, "V5 dual vs sequential mode drift must be zero, got " + std::to_string(drift_modes.maximum));

    // Tier 3: check canvas
    check_image_a_coverage(v5_dual.canvas, a, labels[3]);
    check_canvas(v4.canvas, v5_seq.canvas, labels[2] + "/V4 Tier 3");
    check_canvas(v4.canvas, v5_dual.canvas, labels[3] + "/V4 Tier 3");

    // Tier 4: check RGB pixels
    auto v4_pixels = download_canvas(v4, labels[1] + " Tier 4");
    Image v4_img = v4.canvas.image;
    v4_img.data = v4_pixels.data();

    // V5 dual vs V4
    const PixelError error_dual_v4 = compare_rgb(v4_img, v5_dual.canvas.image);
    require(error_dual_v4.maximum <= kRgbTolerance,
            labels[3] + "/V4 Tier 4: max RGB delta=" + std::to_string(error_dual_v4.maximum) +
            "; expected <= " + std::to_string(kRgbTolerance));

    // V5 dual vs V5 seq (must be bit-for-bit identical)
    const PixelError error_modes = compare_rgb(v5_seq.canvas.image, v5_dual.canvas.image);
    require(error_modes.maximum == 0,
            "V5 dual vs seq Tier 4: expected bit-for-bit 0 delta, got " + std::to_string(error_modes.maximum));

    const int case_max_rgb = std::max(error_dual_v4.maximum, error_modes.maximum);
    summary.max_rgb = std::max(summary.max_rgb, case_max_rgb);
    summary.expanded_canvas |= v5_dual.canvas.image.width > a.width || v5_dual.canvas.image.height > a.height;
    ++summary.panoramas;

    std::cout << name << ": V5 max drift vs V4=" << drift_dual.maximum << " px";
    if (truth) std::cout << "; vs H_gt " << metric_text(candidate_truth);
    std::cout << "; canvas=" << geometry(v5_dual.canvas) << "; Max RGB delta vs V4=" << error_dual_v4.maximum << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv, "--require-v5-pipeline");
        const bool acceptance = options.require_production || !options.synthetic.empty() || !options.dataset.empty();
        if (acceptance) check_acceptance_fixtures(options);
        gpu_test::print_gpu();
        std::cout << "V5 dual-stream pipeline: " << (acceptance ? "full acceptance" : "smoke")
                  << "; B->A grid=" << kGrid << 'x' << kGrid << "; H_gt RMSE <= " << kTruthRmsePx
                  << " px, max <= " << kTruthMaxPx << " px; drift < " << kDriftPx
                  << " px; RGB max <= " << kRgbTolerance << '\n';
        Summary summary;
        run_fixtures(options, [&](const Image& a, const Image& b, const Config& config,
                                  const std::string& name, ErrorCode expected, const Matrix* truth) {
            compare_case(a, b, config, name, expected, truth, summary);
        });
        if (acceptance) {
            require(summary.expanded_canvas, "V5 acceptance did not verify any canvas larger than image A");
        }
        std::cout << "PASS GPU V5 pipeline (" << (acceptance ? "full acceptance" : "smoke") << "): "
                  << gpu_test::checks() << " checks, " << summary.panoramas << " panoramas, "
                  << summary.expected_failures << " expected errors, max RGB error=" << summary.max_rgb << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL GPU V5 pipeline: " << error.what() << '\n';
        return 1;
    }
}
