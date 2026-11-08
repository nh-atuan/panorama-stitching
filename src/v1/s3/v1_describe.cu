// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#include "common/kernel_timing.cuh"
#include "v1/s3/v1_describe.h"
#include "common/brief_pattern.h"
#include "common/image_layout.h"
#include "v1/common/v1_gaussian_blur.h"
#include "v1/common/v1_nvtx.cuh"
#include "v1/s3/v1_brief_kernel.cuh"
#include "v1/s3/v1_compact.cuh"
#include <algorithm>
#include <limits>

namespace panorama {
namespace {

constexpr std::size_t kAlignment = 16;

std::size_t align_up(std::size_t bytes) { return (bytes + kAlignment - 1) / kAlignment * kAlignment; }

// Offsets of one image's buffers inside d_scratch; total == 0 when the size is invalid.
struct DescribeLayout {
    std::size_t smoothed = 0, temp = 0, total_counter = 0, keep = 0, compacted = 0, total = 0;
};

DescribeLayout make_layout(std::int32_t width, std::int32_t height, std::size_t capacity) {
    DescribeLayout layout;
    std::size_t pixels = 0;
    const std::size_t max = std::numeric_limits<std::size_t>::max();
    if (!gray_pixel_count(width, height, pixels) || pixels > max / 8 - kAlignment ||
        capacity > (max / 4) / (sizeof(Keypoint) + sizeof(std::uint32_t))) {
        return layout;
    }
    layout.temp = align_up(pixels * sizeof(float));
    layout.total_counter = layout.temp + align_up(pixels * sizeof(float));
    layout.keep = layout.total_counter + kAlignment;
    layout.compacted = layout.keep + align_up(capacity * sizeof(std::uint32_t));
    const std::size_t end = layout.compacted + capacity * sizeof(Keypoint);
    if (end < layout.compacted) return DescribeLayout();
    layout.total = end;
    return layout;
}

bool valid_gray(const GrayImage& gray) {
    std::size_t pixels = 0;
    return valid_gray_image(gray) && gray_pixel_count(gray.width, gray.height, pixels);
}

// Copies kBriefPattern to constant memory once per process (warm-up run).
ErrorCode load_pattern(cudaStream_t stream) {
    static bool loaded = false;
    if (loaded) return ErrorCode::Success;
    if (cudaMemcpyToSymbolAsync(v1_s3::c_brief_pattern, kBriefPattern, sizeof(kBriefPattern), 0,
                                cudaMemcpyHostToDevice, stream) != cudaSuccess ||
        cudaStreamSynchronize(stream) != cudaSuccess) {
        return ErrorCode::CudaFailure;
    }
    loaded = true;
    return ErrorCode::Success;
}

unsigned blocks_for(std::size_t n) {
    return static_cast<unsigned>(std::max<std::size_t>(1, (n + v1_s3::kThreads - 1) / v1_s3::kThreads));
}

struct ImageJob {
    const GrayImage* gray;
    Keypoint* keypoints;
    Descriptor* descriptors;
    std::uint32_t* count;
    std::size_t capacity;
    bool image_a;
};

ErrorCode describe_one(const ImageJob& job, DeviceCounts* counts, const V1GaussianWeights& weights,
                       std::uint8_t* scratch, cudaStream_t stream) {
    const GrayImage& gray = *job.gray;
    const DescribeLayout layout = make_layout(gray.width, gray.height, job.capacity);
    float* smoothed_data = reinterpret_cast<float*>(scratch + layout.smoothed);
    float* temp = reinterpret_cast<float*>(scratch + layout.temp);
    std::uint32_t* total = reinterpret_cast<std::uint32_t*>(scratch + layout.total_counter);
    std::uint32_t* keep = reinterpret_cast<std::uint32_t*>(scratch + layout.keep);
    Keypoint* compacted = reinterpret_cast<Keypoint*>(scratch + layout.compacted);

    GrayImage smoothed;
    smoothed.data = smoothed_data;
    smoothed.stride = static_cast<std::size_t>(gray.width) * sizeof(float);
    smoothed.width = gray.width;
    smoothed.height = gray.height;
    smoothed.channels = 1;
    {
        V1NvtxRange range("S3.smooth");
        const ErrorCode status = v1_gaussian_blur(gray, smoothed, temp, weights, stream);
        if (status != ErrorCode::Success) return status;
    }
    V1NvtxRange range("S3.brief_compact");
    const std::uint32_t capacity = static_cast<std::uint32_t>(job.capacity);
    const unsigned grid = blocks_for(job.capacity);
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::validate_kernel<<<1, v1_s3::kThreads, 0, stream>>>(counts, job.count, job.keypoints, capacity));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::keep_flags_kernel<<<grid, v1_s3::kThreads, 0, stream>>>(counts, job.count, job.keypoints, gray.width,
                                                                   gray.height, keep));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::exclusive_scan_kernel<<<1, v1_s3::kScanThreads, 0, stream>>>(counts, job.count, keep, total));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::describe_kernel<<<grid, v1_s3::kThreads, 0, stream>>>(counts, job.count, job.keypoints, smoothed_data,
                                                                 gray.width, gray.height, keep, job.descriptors,
                                                                 compacted));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::copy_back_kernel<<<grid, v1_s3::kThreads, 0, stream>>>(counts, total, compacted, job.keypoints));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::publish_kernel<<<1, 1, 0, stream>>>(counts, total, job.image_a));
    return cudaPeekAtLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

}  // namespace

std::size_t v1_describe_scratch_bytes(std::int32_t width, std::int32_t height, std::size_t keypoint_capacity) {
    return make_layout(width, height, keypoint_capacity).total;
}

ErrorCode v1_describe(DeviceWorkspace& w, const Config& config, cudaStream_t stream) {
    (void)config;  // S3 has no Config fields, as in V0.
    V1NvtxRange stage("S3.describe");
    if (!valid_gray(w.grayA) || !valid_gray(w.grayB)) return ErrorCode::InvalidImage;

    const std::size_t int_max = static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max());
    if (!w.d_counts || !w.d_keypointsA || !w.d_keypointsB || !w.d_descriptorsA || !w.d_descriptorsB ||
        w.descriptor_capacityA < w.keypoint_capacityA || w.descriptor_capacityB < w.keypoint_capacityB ||
        w.keypoint_capacityA > int_max || w.keypoint_capacityB > int_max) {
        return ErrorCode::InvalidArgument;
    }
    const std::size_t a = v1_describe_scratch_bytes(w.grayA.width, w.grayA.height, w.keypoint_capacityA);
    const std::size_t b = v1_describe_scratch_bytes(w.grayB.width, w.grayB.height, w.keypoint_capacityB);
    if (a == 0 || b == 0 || !w.d_scratch || w.scratch_capacity_bytes < std::max(a, b) ||
        reinterpret_cast<std::uintptr_t>(w.d_scratch) % kAlignment != 0) {
        return ErrorCode::InvalidArgument;
    }

    V1GaussianWeights weights;
    ErrorCode status = v1_make_gaussian_weights(kBriefSmoothSigma, kBriefSmoothRadius, weights);
    if (status != ErrorCode::Success) return status;
    status = load_pattern(stream);
    if (status != ErrorCode::Success) return status;

    const ImageJob jobs[2] = {
        {&w.grayA, w.d_keypointsA, w.d_descriptorsA, &w.d_counts->keypointsA, w.keypoint_capacityA, true},
        {&w.grayB, w.d_keypointsB, w.d_descriptorsB, &w.d_counts->keypointsB, w.keypoint_capacityB, false}};
    for (const ImageJob& job : jobs) {
        V1NvtxRange range(job.image_a ? "S3.image_a" : "S3.image_b");
        status = describe_one(job, w.d_counts, weights, w.d_scratch, stream);
        if (status != ErrorCode::Success) return status;
    }
    return ErrorCode::Success;
}

}  // namespace panorama
