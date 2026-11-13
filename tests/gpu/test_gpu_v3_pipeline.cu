// Authors: Le Ha Thanh Chuong (23120195)
// External source: none

#include "gpu/pipeline_test_support.cuh"
#include "v0/v0_pipeline.h"
#include "v2/v2_pipeline.h"

#ifdef V3_PIPELINE_AVAILABLE
#include "v3/v3_pipeline.h"
#else
// Permit a compile-only check before P8-T02 supplies the production adapter.
// The test runner links this suite only against the real implementation.
namespace panorama {
ErrorCode v3_prepare(const Image&, const Image&, const Config&, V1DeviceOwner&);
ErrorCode v3_run_stages(DeviceWorkspace&, const Config&, cudaStream_t,
                        const V1StageTrace&, V1StageFailure&);
}  // namespace panorama
#endif

using namespace pipeline_test;

namespace {

struct Summary {
    int panoramas = 0;
    int expected_failures = 0;
    int max_rgb = 0;
};

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

template<class Prepare, class RunStages>
ErrorCode run_version(const Image& a, const Image& b, const Config& config, GpuOutput& output,
                      Prepare prepare, RunStages stages, const std::string& label) {
    try {
        return run_gpu(a, b, config, output, prepare, stages);
    } catch (const std::exception& error) {
        throw std::runtime_error(label + ": pipeline/CUDA exception: " + error.what());
    }
}

void check_acceptance_fixtures(const Options& options) {
    if (options.dataset.empty() || options.synthetic.empty()) {
        throw std::runtime_error("V3 acceptance requires --dataset and all six --synthetic-pair fixtures");
    }
    for (const std::string kind : {"translation", "projective"}) {
        for (const std::string size : {"small", "medium", "large"}) {
            const std::string label = kind + "/" + size;
            const auto count = std::count_if(options.synthetic.begin(), options.synthetic.end(),
                                            [&](const SyntheticFilePair& pair) { return pair.label == label; });
            if (count != 1) throw std::runtime_error("V3 acceptance requires exactly one fixture for " + label);
        }
    }
}

void compare_case(const Image& a, const Image& b, const Config& config, const std::string& name,
                  ErrorCode expected, const Matrix* truth, Summary& summary) {
    const std::string context = case_context(a, b, config, name);
    const std::string labels[] = {context + " V0", context + " V1", context + " V2", context + " V3"};
    V0Workspace v0;
    ErrorCode status0 = v0_prepare(a, b, config, v0);
    if (status0 == ErrorCode::Success) status0 = v0_run(a, b, config, v0, nullptr, nullptr);
    GpuOutput v1, v2, v3;
    const ErrorCode statuses[] = {
        status0,
        run_version(a, b, config, v1, v1_prepare, v1_run_stages, labels[1]),
        run_version(a, b, config, v2, v2_prepare, v2_run_stages, labels[2]),
        run_version(a, b, config, v3, v3_prepare, v3_run_stages, labels[3]),
    };

    // Tier 1: compare status before reading any homography or canvas.
    for (int version = 0; version < 4; ++version) {
        require(statuses[version] == expected, labels[version] + " Tier 1: expected " +
                status_text(expected) + ", got " + status_text(statuses[version]));
    }
    if (expected != ErrorCode::Success) {
        ++summary.expected_failures;
        std::cout << name << ": Tier 1 V0/V1/V2/V3 expected " << status_text(expected) << '\n';
        return;
    }

    // Tier 2: measure B->A distances on P7's 20x20 grid. H_gt alone masks synthetic Q.
    const Matrix matrices[] = {
        as_matrix(v0.homography), read_homography(v1, labels[1]),
        read_homography(v2, labels[2]), read_homography(v3, labels[3]),
    };
    if (truth) {
        for (int version = 0; version < 4; ++version) {
            const std::string label = labels[version] + " Tier 2 vs H_gt";
            const ProjectionError error = projection_error(a, b, matrices[version], *truth, truth, label);
            std::cout << label << ": " << metric_text(error) << '\n';
            require(error.rmse <= kTruthRmsePx && error.maximum <= kTruthMaxPx,
                    label + ": " + metric_text(error) + "; expected RMSE <= " +
                    std::to_string(kTruthRmsePx) + " px and max <= " + std::to_string(kTruthMaxPx) + " px");
        }
    }
    ProjectionError drifts[3];
    for (int version = 0; version < 3; ++version) {
        const std::string label = labels[version] + "/V3 Tier 2";
        drifts[version] = projection_error(a, b, matrices[3], matrices[version], truth, label);
        const std::string result = label + ": " + metric_text(drifts[version]) +
                                   "; expected max < " + std::to_string(kDriftPx) + " px";
        std::cout << result << '\n';
        require(drifts[version].maximum < kDriftPx, result);
    }

    // Tier 3: compare every canvas before downloading RGB.
    const Panorama canvases[] = {v0.panorama, v1.canvas, v2.canvas};
    for (int version = 0; version < 3; ++version) {
        check_canvas(canvases[version], v3.canvas, labels[version] + "/V3 Tier 3");
    }
    canvas_bytes(v0.panorama.image, labels[0] + " Tier 3");

    // Tier 4: compare active RGB bytes, including the defined background and excluding padding.
    auto candidate_pixels = download_canvas(v3, labels[3] + " Tier 4");
    Image candidate = v3.canvas.image;
    candidate.data = candidate_pixels.data();
    const GpuOutput* gpu_baselines[] = {&v1, &v2};
    int case_max_rgb = 0;
    for (int version = 0; version < 3; ++version) {
        const std::string label = labels[version] + "/V3 Tier 4";
        Image baseline = canvases[version].image;
        std::vector<std::uint8_t> pixels;
        if (version > 0) {
            pixels = download_canvas(*gpu_baselines[version - 1], label);
            baseline.data = pixels.data();
        }
        const PixelError error = compare_rgb(baseline, candidate);
        case_max_rgb = std::max(case_max_rgb, error.maximum);
        require(error.maximum <= kRgbTolerance,
                label + ": max RGB delta=" + std::to_string(error.maximum) +
                " at (" + std::to_string(error.x) + "," + std::to_string(error.y) + ") channel=" +
                std::to_string(error.channel) + "; expected <= " + std::to_string(kRgbTolerance) +
                "; Tier 2 " + metric_text(drifts[version]) + "; Tier 3 exact " + geometry(v3.canvas));
    }
    summary.max_rgb = std::max(summary.max_rgb, case_max_rgb);
    ++summary.panoramas;
    std::cout << name << ": Tier 3 exact " << geometry(v3.canvas)
              << "; Tier 4 max RGB delta=" << case_max_rgb << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv, "--require-v3-pipeline");
        const bool acceptance = options.require_production || !options.synthetic.empty() || !options.dataset.empty();
        if (acceptance) check_acceptance_fixtures(options);
        gpu_test::print_gpu();
        std::cout << "V3 production pipeline: " << (acceptance ? "full acceptance" : "smoke")
                  << "; B->A grid=" << kGrid << 'x' << kGrid << "; H_gt RMSE <= " << kTruthRmsePx
                  << " px, max <= " << kTruthMaxPx << " px; drift < " << kDriftPx
                  << " px; RGB max <= " << kRgbTolerance << '\n';
        Summary summary;
        run_fixtures(options, [&](const Image& a, const Image& b, const Config& config,
                                  const std::string& name, ErrorCode expected, const Matrix* truth) {
            compare_case(a, b, config, name, expected, truth, summary);
        });
        std::cout << "PASS GPU V3 pipeline (" << (acceptance ? "full acceptance" : "smoke") << "): "
                  << gpu_test::checks() << " checks, " << summary.panoramas << " panoramas, "
                  << summary.expected_failures << " expected errors, max RGB error=" << summary.max_rgb << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL GPU V3 pipeline: " << error.what() << '\n';
        return 1;
    }
}
