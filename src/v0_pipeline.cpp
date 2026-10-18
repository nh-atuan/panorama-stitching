// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0_pipeline.h"
#include "feature_support.h"
#include "v0_describe.h"
#include "v0_detect.h"
#include "v0_match.h"
#include "v0_preprocess.h"
#include "v0_warp_blend.h"
#include <chrono>
#include <limits>
#include <new>

namespace panorama {
namespace {

using Clock = std::chrono::high_resolution_clock;

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

template <typename T>
FeatureView<T> view_of(const std::vector<T>& values) {
    return FeatureView<T>(values.data(), static_cast<std::int32_t>(values.size()),
                          values.capacity());
}

ErrorCode allocate_gray(const Image& source, std::vector<float>& storage, GrayImage& gray) {
    if (source.width <= 0 || source.height <= 0) return ErrorCode::InvalidImage;
    const std::size_t width = static_cast<std::size_t>(source.width);
    const std::size_t height = static_cast<std::size_t>(source.height);
    if (width > std::numeric_limits<std::size_t>::max() / sizeof(float) / height)
        return ErrorCode::InvalidImage;
    try {
        storage.assign(width * height, 0.0f);
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    } catch (const std::length_error&) {
        return ErrorCode::AllocationFailed;
    }
    gray = GrayImage();
    gray.data = storage.data();
    gray.width = source.width;
    gray.height = source.height;
    gray.channels = 1;
    gray.stride = width * sizeof(float);
    return ErrorCode::Success;
}

// Times one stage when `timing` is non-null; the stage itself never sees the clock.
template <typename Function>
ErrorCode timed(Stage stage, TimingStats* timing, Function function) {
    if (!timing) return function();
    const Clock::time_point start = Clock::now();
    const ErrorCode status = function();
    timing->stage_ms[static_cast<std::size_t>(stage)] = elapsed_ms(start, Clock::now());
    return status;
}

ErrorCode run_stages(const Image& left, const Image& right, const Config& config,
                     V0Workspace& ws, TimingStats* timing, Stage& stage,
                     HomographyReport* report) {
    stage = Stage::Preprocess;
    ErrorCode status = timed(stage, timing, [&]() -> ErrorCode {
        const ErrorCode a = v0_preprocess(left, ws.gray_a, config);
        return a != ErrorCode::Success ? a : v0_preprocess(right, ws.gray_b, config);
    });
    if (status != ErrorCode::Success) return status;

    stage = Stage::Detect;
    status = timed(stage, timing, [&]() -> ErrorCode {
        const ErrorCode a = v0_detect(ws.gray_a, ws.keypoints_a, config);
        return a != ErrorCode::Success ? a : v0_detect(ws.gray_b, ws.keypoints_b, config);
    });
    if (status != ErrorCode::Success) return status;
    ws.detected_a = ws.keypoints_a.size();
    ws.detected_b = ws.keypoints_b.size();

    stage = Stage::Describe;
    status = timed(stage, timing, [&]() -> ErrorCode {
        const ErrorCode a = v0_describe(ws.gray_a, ws.keypoints_a, ws.descriptors_a, config);
        return a != ErrorCode::Success
            ? a : v0_describe(ws.gray_b, ws.keypoints_b, ws.descriptors_b, config);
    });
    if (status != ErrorCode::Success) return status;

    stage = Stage::Match;
    status = timed(stage, timing, [&]() -> ErrorCode {
        return v0_match(view_of(ws.descriptors_a), view_of(ws.descriptors_b), ws.matches, config);
    });
    if (status != ErrorCode::Success) return status;

    stage = Stage::Homography;
    status = timed(stage, timing, [&]() -> ErrorCode {
        return v0_homography(view_of(ws.keypoints_a), view_of(ws.keypoints_b),
                             view_of(ws.matches), ws.homography, config, report);
    });
    if (status != ErrorCode::Success) return status;

    stage = Stage::WarpBlend;
    return timed(stage, timing, [&]() -> ErrorCode {
        return v0_warp_blend(left, right, ws.homography, ws.panorama, config);
    });
}

}  // namespace

V0Workspace::~V0Workspace() {
    v0_release_output(*this);
}

ErrorCode v0_prepare(const Image& left, const Image& right, const Config& config,
                     V0Workspace& workspace) {
    if (config.max_keypoints <= 0) return ErrorCode::InvalidConfig;
    ErrorCode status = allocate_gray(left, workspace.gray_storage_a, workspace.gray_a);
    if (status != ErrorCode::Success) return status;
    status = allocate_gray(right, workspace.gray_storage_b, workspace.gray_b);
    if (status != ErrorCode::Success) return status;
    const std::size_t capacity = static_cast<std::size_t>(config.max_keypoints);
    try {
        workspace.keypoints_a.reserve(capacity);
        workspace.keypoints_b.reserve(capacity);
        workspace.descriptors_a.reserve(capacity);
        workspace.descriptors_b.reserve(capacity);
        workspace.matches.reserve(capacity);
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    } catch (const std::length_error&) {
        return ErrorCode::AllocationFailed;
    }
    return ErrorCode::Success;
}

ErrorCode v0_run(const Image& left, const Image& right, const Config& config,
                 V0Workspace& workspace, TimingStats* timing, Stage* failed_stage,
                 HomographyReport* report) {
    v0_release_output(workspace);
    if (timing) *timing = TimingStats();
    Stage stage = Stage::Preprocess;
    // Untimed runs (warm-up, tools) never read the clock.
    const Clock::time_point start = timing ? Clock::now() : Clock::time_point();
    const ErrorCode status = run_stages(left, right, config, workspace, timing, stage, report);
    if (timing) timing->end_to_end_ms = elapsed_ms(start, Clock::now());
    if (status != ErrorCode::Success && failed_stage) *failed_stage = stage;
    return status;
}

void v0_release_output(V0Workspace& workspace) {
    delete[] workspace.panorama.image.data;
    workspace.panorama = Panorama();
}

const char* stage_name(Stage stage) {
    switch (stage) {
        case Stage::Preprocess: return "S1 preprocess";
        case Stage::Detect: return "S2 detect";
        case Stage::Describe: return "S3 describe";
        case Stage::Match: return "S4 match";
        case Stage::Homography: return "S5 homography";
        case Stage::WarpBlend: return "S6 warp_blend";
    }
    return "unknown stage";
}

}  // namespace panorama
