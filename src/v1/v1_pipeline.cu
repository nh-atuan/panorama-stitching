// Authors: Le Ha Thanh Chuong (23120195), Tran Huu Kim Thanh (23120166)
// External source: none

#include "v1/v1_pipeline.h"
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
#include "v1/s3/v1_describe.h"
#include "v1/s4/v1_match.h"
#include "v1/s5/v1_homography.h"
#include "v1/v1_warp_blend.h"

#include <algorithm>
#include <limits>

namespace panorama {
namespace {

bool valid_rgb(const Image& image) {
    return image.data && image.width > 0 && image.height > 0 && image.channels == 3 &&
           image.stride >= static_cast<std::size_t>(image.width) * 3 &&
           static_cast<std::size_t>(image.height) <=
               std::numeric_limits<std::size_t>::max() / image.stride;
}

GrayImage packed_gray(float* data, const Image& rgb) {
    GrayImage gray;
    gray.data = data;
    gray.width = rgb.width;
    gray.height = rgb.height;
    gray.channels = 1;
    gray.stride = static_cast<std::size_t>(rgb.width) * sizeof(float);
    return gray;
}

// Per-thread Device stack for the recursive summation tree of S5. The S5 design
// (docs/stages/s5-homography.md, section 11) leaves this global limit to the caller,
// with the same value its tests and driver use.
constexpr std::size_t kV1StackBytes = 32768;

std::size_t v1_s5_scratch(std::size_t capacity) {
    return v1_homography_scratch_bytes(capacity);
}

}  // namespace

V1DeviceOwner::~V1DeviceOwner() {
    // d_panorama aliases d_canvas, so it is never freed on its own.
    device_free(view.d_scratch);
    device_free(view.d_canvas_info);
    device_free(view.d_counts);
    device_free(view.d_canvas);
    device_free(view.d_homography);
    device_free(view.d_matches);
    device_free(view.d_descriptorsB);
    device_free(view.d_descriptorsA);
    device_free(view.d_keypointsB);
    device_free(view.d_keypointsA);
    device_free(view.d_grayB);
    device_free(view.d_grayA);
    device_free(view.d_imageB);
    device_free(view.d_imageA);
}

static std::size_t gpu_scratch_bytes(const Image& a, const Image& b, std::size_t feature_capacity,
                                    HomographyScratchBytes homography_scratch) {
    std::size_t needed = 0;
    bool valid = true;
    auto take = [&](std::size_t bytes, bool zero_allowed) {
        if (!bytes && !zero_allowed) valid = false;
        needed = std::max(needed, bytes);
    };
    const Image* images[] = {&a, &b};
    for (const Image* image : images) {
        take(v1_preprocess_scratch_bytes(image->width, image->height), false);
        // 0 for a side <= 30 (no candidates) or W*H >= 2^32, which S2 itself rejects.
        take(v1_detect_scratch_bytes(image->width, image->height), true);
        take(v1_describe_scratch_bytes(image->width, image->height, feature_capacity), false);
    }
    take(v1_match_scratch_bytes(feature_capacity), feature_capacity == 0);
    take(homography_scratch(feature_capacity), false);
    const std::size_t alignment = 16;
    if (!valid || needed > std::numeric_limits<std::size_t>::max() - (alignment - 1)) return 0;
    return (needed + alignment - 1) / alignment * alignment;
}

std::size_t v1_scratch_bytes(const Image& a, const Image& b, std::size_t feature_capacity) {
    return gpu_scratch_bytes(a, b, feature_capacity, v1_s5_scratch);
}

ErrorCode v1_prepare(const Image& left, const Image& right, const Config& config,
                     V1DeviceOwner& owner) {
    return prepare_gpu_pipeline(left, right, config, owner, v1_s5_scratch);
}

ErrorCode prepare_gpu_pipeline(const Image& left, const Image& right, const Config& config,
                               V1DeviceOwner& owner, HomographyScratchBytes homography_scratch) {
    if (!valid_rgb(left) || !valid_rgb(right)) return ErrorCode::InvalidImage;
    if (config.max_keypoints <= 0) return ErrorCode::InvalidConfig;
    const std::size_t features = static_cast<std::size_t>(config.max_keypoints);
    const std::size_t scratch = gpu_scratch_bytes(left, right, features, homography_scratch);
    if (!scratch) return ErrorCode::InvalidImage;

    std::size_t stack_bytes = 0;
    CUDA_CHECK(cudaDeviceGetLimit(&stack_bytes, cudaLimitStackSize));
    if (stack_bytes < kV1StackBytes) {
        CUDA_CHECK(cudaDeviceSetLimit(cudaLimitStackSize, kV1StackBytes));
    }

    DeviceWorkspace& w = owner.view;
    device_allocate(w.d_imageA, left.stride * static_cast<std::size_t>(left.height));
    device_allocate(w.d_imageB, right.stride * static_cast<std::size_t>(right.height));
    w.imageA = left;
    w.imageB = right;
    w.imageA.data = w.d_imageA;
    w.imageB.data = w.d_imageB;
    device_allocate(w.d_grayA, static_cast<std::size_t>(left.width) * left.height);
    device_allocate(w.d_grayB, static_cast<std::size_t>(right.width) * right.height);
    w.grayA = packed_gray(w.d_grayA, left);
    w.grayB = packed_gray(w.d_grayB, right);
    device_allocate(w.d_keypointsA, features);
    device_allocate(w.d_keypointsB, features);
    device_allocate(w.d_descriptorsA, features);
    device_allocate(w.d_descriptorsB, features);
    device_allocate(w.d_matches, features);
    device_allocate(w.d_homography, 1);
    device_allocate(w.d_counts, 1);
    device_allocate(w.d_canvas_info, 1);
    device_allocate(w.d_scratch, scratch);  // cudaMalloc returns at least 256-byte alignment.
    CUDA_CHECK(cudaMemset(w.d_counts, 0, sizeof(DeviceCounts)));
    CUDA_CHECK(cudaMemset(w.d_canvas_info, 0, sizeof(DeviceCanvasInfo)));
    CUDA_CHECK(cudaMemset(w.d_homography, 0, sizeof(Homography)));
    w.keypoint_capacityA = w.keypoint_capacityB = features;
    w.descriptor_capacityA = w.descriptor_capacityB = features;
    w.match_capacity = features;
    w.scratch_capacity_bytes = scratch;
    // No canvas yet: S6 computes the geometry from H and allocates d_canvas itself.
    w.d_canvas = nullptr;
    w.d_panorama = nullptr;
    w.canvas = Panorama();
    w.canvas_capacity_bytes = 0;
    return ErrorCode::Success;
}

DeviceCounts v1_read_counts(const DeviceWorkspace& workspace, cudaStream_t stream) {
    DeviceCounts counts;
    CUDA_CHECK(cudaMemcpyAsync(&counts, workspace.d_counts, sizeof(counts),
                               cudaMemcpyDeviceToHost, stream));
    CUDA_CHECK(cudaStreamSynchronize(stream));
    return counts;
}

ErrorCode v1_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure) {
    return run_gpu_stages(workspace, config, stream, trace, failure, v1_homography);
}

ErrorCode run_gpu_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure, GpuStage homography) {
    const GpuStage stages[kStageCount] = {
        v1_preprocess, v1_detect, v1_describe, v1_match, homography, v1_warp_blend
    };
    failure = V1StageFailure();
    for (std::size_t i = 0; i < kStageCount; ++i) {
        const Stage stage = static_cast<Stage>(i);
        if (trace.stage_start) trace.stage_start[i].record(stream);
        const ErrorCode status = stages[i](workspace, config, stream);
        if (status != ErrorCode::Success) {
            failure.stage = stage;
            if (stage == Stage::WarpBlend) {
                // S3-S5 skip their work after an error and leave H at zero; report the cause.
                const DeviceCounts counts = v1_read_counts(workspace, stream);
                if (counts.status != ErrorCode::Success) {
                    failure.on_device = true;
                    return counts.status;
                }
            }
            return status;
        }
        CUDA_CHECK(cudaGetLastError());  // Catch immediate launch errors as kernels arrive.
        if (trace.stage_stop) trace.stage_stop[i].record(stream);
        if (stage == Stage::Detect && trace.after_s2) {
            *trace.after_s2 = v1_read_counts(workspace, stream);
        }
    }
    return ErrorCode::Success;
}

V1Diagnostics v1_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream) {
    return collect_gpu_diagnostics(workspace, stream, v1_homography_diagnostics(workspace));
}

}  // namespace panorama
