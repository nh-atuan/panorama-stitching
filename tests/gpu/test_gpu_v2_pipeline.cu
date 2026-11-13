// Authors: Le Ha Thanh Chuong (23120195)
// External source: none
// Adapted from: tests/gpu/test_gpu_v1_pipeline.cu by Nguyen Ho Anh Tuan (23120185)

#include "gpu/pipeline_test_support.cuh"
#include "v0/v0_pipeline.h"
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

using namespace panorama;
using namespace gpu_test;
using namespace pipeline_test;

namespace {

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

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv, "--require-v2-pipeline");
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
        run_fixtures(options, [&](const Image& a, const Image& b, const Config& config,
                                  const std::string& name, ErrorCode expected, const Matrix* truth) {
            compare_case(a, b, config, name, expected, summary, truth);
        });
        std::cout << "PASS GPU V2 pipeline (" << mode << "): " << checks() << " checks, "
                  << summary.comparisons << " successful comparisons, " << summary.expected_failures
                  << " expected errors, max RGB error=" << summary.max_rgb << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL GPU V2 pipeline: " << error.what() << '\n';
        return 1;
    }
}
