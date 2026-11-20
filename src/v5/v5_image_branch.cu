// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v5/v5_image_branch.h"
#include "common/brief_pattern.h"
#include "common/feature_border.h"
#include "common/image_layout.h"
#include "common/kernel_timing.cuh"
#include "v1/common/v1_gaussian_blur.h"
#include "v1/common/v1_nvtx.cuh"
#include "v1/s1/v1_grayscale.cuh"
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
#include "v1/s2/v1_fast_score.cuh"
#include "v1/s2/v1_nms.cuh"
#include "v1/s2/v1_topk_sort.cuh"
#include "v1/s3/v1_brief_kernel.cuh"
#include "v1/s3/v1_compact.cuh"
#include "v1/s3/v1_describe.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

namespace panorama {
namespace {

constexpr unsigned kBlockX = 32;
constexpr unsigned kBlockY = 8;
constexpr std::size_t kScratchAlignment = 16;

inline std::size_t align_up(std::size_t bytes) {
    return (bytes + kScratchAlignment - 1) / kScratchAlignment * kScratchAlignment;
}

struct DetectLayout {
    std::size_t pixels = 0;
    std::uint32_t capacity = 0;
    std::size_t scores_offset = kScratchAlignment;
    std::size_t keys_offset = 0;
    std::size_t total = 0;
};

inline bool has_region(std::int32_t width, std::int32_t height) {
    return width > 2 * kFeatureBorder && height > 2 * kFeatureBorder;
}

inline bool make_detect_layout(std::int32_t width, std::int32_t height, DetectLayout& layout) {
    layout = DetectLayout();
    if (!gray_pixel_count(width, height, layout.pixels)) return false;
    if (layout.pixels > std::numeric_limits<std::uint32_t>::max()) return false;
    if (!has_region(width, height)) return true;
    const std::size_t half_w = (static_cast<std::size_t>(width) + 1) / 2;
    const std::size_t half_h = (static_cast<std::size_t>(height) + 1) / 2;
    layout.capacity = static_cast<std::uint32_t>(half_w * half_h);
    const std::size_t slots = v1_s2::next_power_of_two(layout.capacity);
    const std::size_t scores_end = layout.scores_offset + layout.pixels * sizeof(float);
    layout.keys_offset = align_up(scores_end);
    layout.total = layout.keys_offset + slots * sizeof(unsigned long long);
    return true;
}

inline dim3 region_grid(const GrayImage& gray) {
    const unsigned w = static_cast<unsigned>(gray.width - 2 * kFeatureBorder);
    const unsigned h = static_cast<unsigned>(gray.height - 2 * kFeatureBorder);
    return dim3((w + kBlockX - 1) / kBlockX, (h + kBlockY - 1) / kBlockY);
}

struct DescribeLayout {
    std::size_t smoothed = 0;
    std::size_t temp = 0;
    std::size_t total_counter = 0;
    std::size_t keep = 0;
    std::size_t compacted = 0;
    std::size_t total = 0;
};

inline DescribeLayout make_describe_layout(std::int32_t width, std::int32_t height, std::size_t capacity) {
    DescribeLayout layout;
    std::size_t pixels = 0;
    const std::size_t max = std::numeric_limits<std::size_t>::max();
    if (!gray_pixel_count(width, height, pixels) || pixels > max / 8 - kScratchAlignment ||
        capacity > (max / 4) / (sizeof(Keypoint) + sizeof(std::uint32_t))) {
        return layout;
    }
    layout.temp = align_up(pixels * sizeof(float));
    layout.total_counter = layout.temp + align_up(pixels * sizeof(float));
    layout.keep = layout.total_counter + kScratchAlignment;
    layout.compacted = layout.keep + align_up(capacity * sizeof(std::uint32_t));
    const std::size_t end = layout.compacted + capacity * sizeof(Keypoint);
    if (end < layout.compacted) return DescribeLayout();
    layout.total = end;
    return layout;
}

inline unsigned describe_blocks_for(std::size_t n) {
    return static_cast<unsigned>(std::max<std::size_t>(1, (n + v1_s3::kThreads - 1) / v1_s3::kThreads));
}

__global__ void publish_count_kernel(std::uint32_t* field, std::uint32_t value) {
    if (threadIdx.x || blockIdx.x) return;
    *field = value;
}

}  // namespace

ErrorCode v5_image_scratch_bytes(const Image& host, const Config& config, std::size_t& bytes) {
    bytes = 0;
    if (host.width <= 0 || host.height <= 0 || host.channels != 3) return ErrorCode::InvalidImage;
    if (config.max_keypoints <= 0) return ErrorCode::InvalidConfig;

    const std::size_t s1 = v1_preprocess_scratch_bytes(host.width, host.height);
    const std::size_t s2 = v1_detect_scratch_bytes(host.width, host.height);
    const std::size_t s3 = v1_describe_scratch_bytes(host.width, host.height, static_cast<std::size_t>(config.max_keypoints));
    if (s1 == 0 || s3 == 0) return ErrorCode::InvalidArgument;

    bytes = align_up(std::max({s1, s2, s3}));
    return ErrorCode::Success;
}

ErrorCode v5_initialize_features(const Config& config, cudaStream_t stream) {
    (void)config;
    if (cudaMemcpyToSymbolAsync(v1_s3::c_brief_pattern, kBriefPattern, sizeof(kBriefPattern), 0,
                                cudaMemcpyHostToDevice, stream) != cudaSuccess) {
        return ErrorCode::CudaFailure;
    }
    if (cudaStreamSynchronize(stream) != cudaSuccess) {
        return ErrorCode::CudaFailure;
    }
    return ErrorCode::Success;
}

ErrorCode v5_reset_image(V5ImageBranch& branch, cudaStream_t stream) {
    if (!branch.counts) return ErrorCode::InvalidArgument;
    if (cudaMemsetAsync(branch.counts, 0, sizeof(DeviceCounts), stream) != cudaSuccess) {
        return ErrorCode::CudaFailure;
    }
    if (branch.host_candidates) {
        *branch.host_candidates = 0;
    }
    return cudaGetLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

ErrorCode v5_upload_image(const Image& pinned_host, V5ImageBranch& branch, cudaStream_t stream) {
    if (!pinned_host.data || !branch.image.data ||
        pinned_host.width != branch.image.width || pinned_host.height != branch.image.height ||
        pinned_host.channels != 3 || branch.image.channels != 3) {
        return ErrorCode::InvalidImage;
    }
    const std::size_t row_bytes = static_cast<std::size_t>(pinned_host.width) * 3;
    if (cudaMemcpy2DAsync(branch.image.data, branch.image.stride, pinned_host.data, pinned_host.stride,
                          row_bytes, pinned_host.height, cudaMemcpyHostToDevice, stream) != cudaSuccess) {
        return ErrorCode::CudaFailure;
    }
    return cudaGetLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

ErrorCode v5_preprocess_image(V5ImageBranch& branch, const Config& config, cudaStream_t stream) {
    if (!branch.image.data || !branch.gray.data || !branch.scratch) return ErrorCode::InvalidArgument;
    V1GaussianWeights weights;
    const ErrorCode status = v1_make_gaussian_weights(config.gaussian_sigma, config.gaussian_radius, weights);
    if (status != ErrorCode::Success) return status;

    v1_s1::launch_grayscale(branch.image, branch.gray, stream);
    if (cudaPeekAtLastError() != cudaSuccess) return ErrorCode::CudaFailure;

    float* temp = reinterpret_cast<float*>(branch.scratch);
    return v1_gaussian_blur(branch.gray, branch.gray, temp, weights, stream);
}

ErrorCode v5_detect_candidates(V5ImageBranch& branch, const Config& config, cudaStream_t stream) {
    if (!branch.gray.data || !branch.scratch || !branch.host_candidates) return ErrorCode::InvalidArgument;
    DetectLayout layout;
    if (!make_detect_layout(branch.gray.width, branch.gray.height, layout)) return ErrorCode::InvalidArgument;

    uint32_t* d_count = reinterpret_cast<uint32_t*>(branch.scratch);
    if (layout.total != 0) {
        float* scores = reinterpret_cast<float*>(branch.scratch + layout.scores_offset);
        unsigned long long* keys = reinterpret_cast<unsigned long long*>(branch.scratch + layout.keys_offset);
        const unsigned char* pixels = reinterpret_cast<const unsigned char*>(branch.gray.data);
        const dim3 block(kBlockX, kBlockY), grid = region_grid(branch.gray);

        if (cudaMemsetAsync(d_count, 0, sizeof(uint32_t), stream) != cudaSuccess ||
            cudaMemsetAsync(scores, 0, layout.pixels * sizeof(float), stream) != cudaSuccess) {
            return ErrorCode::CudaFailure;
        }
        PANORAMA_LAUNCH_KERNEL(stream, v1_s2::fast_score_kernel<<<grid, block, 0, stream>>>(
            pixels, branch.gray.stride, branch.gray.width, branch.gray.height,
            config.fast_threshold, scores));
        PANORAMA_LAUNCH_KERNEL(stream, v1_s2::nms_kernel<<<grid, block, 0, stream>>>(
            scores, branch.gray.width, branch.gray.height, d_count, keys, layout.capacity));
    } else {
        if (cudaMemsetAsync(d_count, 0, sizeof(uint32_t), stream) != cudaSuccess) {
            return ErrorCode::CudaFailure;
        }
    }
    if (cudaPeekAtLastError() != cudaSuccess) return ErrorCode::CudaFailure;
    if (cudaMemcpyAsync(branch.host_candidates, d_count, sizeof(uint32_t), cudaMemcpyDeviceToHost, stream) != cudaSuccess) {
        return ErrorCode::CudaFailure;
    }
    return ErrorCode::Success;
}

ErrorCode v5_finish_detect(V5ImageBranch& branch, const Config& config, cudaStream_t stream) {
    if (!branch.gray.data || !branch.scratch || !branch.keypoints || !branch.counts || !branch.host_candidates)
        return ErrorCode::InvalidArgument;
    DetectLayout layout;
    if (!make_detect_layout(branch.gray.width, branch.gray.height, layout)) return ErrorCode::InvalidArgument;

    uint32_t kept = 0;
    if (layout.total != 0) {
        uint32_t candidates = std::min(*branch.host_candidates, layout.capacity);
        kept = std::min(candidates, static_cast<uint32_t>(config.max_keypoints));
        unsigned long long* keys = reinterpret_cast<unsigned long long*>(branch.scratch + layout.keys_offset);
        if (v1_s2::sort_keys(keys, candidates, stream) != cudaSuccess) return ErrorCode::CudaFailure;
        if (kept > 0) {
            PANORAMA_LAUNCH_KERNEL(stream, v1_s2::write_keypoints_kernel<<<v1_s2::blocks_for(kept), v1_s2::kSortThreads, 0, stream>>>(
                keys, kept, static_cast<uint32_t>(branch.gray.width), branch.keypoints));
        }
    }
    PANORAMA_LAUNCH_KERNEL(stream, publish_count_kernel<<<1, 1, 0, stream>>>(&branch.counts->keypointsA, kept));
    return cudaPeekAtLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

ErrorCode v5_describe_image(V5ImageBranch& branch, const Config& config, cudaStream_t stream) {
    (void)config;
    if (!branch.gray.data || !branch.scratch || !branch.keypoints || !branch.descriptors || !branch.counts)
        return ErrorCode::InvalidArgument;
    const DescribeLayout layout = make_describe_layout(branch.gray.width, branch.gray.height, branch.feature_capacity);
    if (layout.total == 0) return ErrorCode::InvalidArgument;

    float* smoothed_data = reinterpret_cast<float*>(branch.scratch + layout.smoothed);
    float* temp = reinterpret_cast<float*>(branch.scratch + layout.temp);
    uint32_t* total = reinterpret_cast<uint32_t*>(branch.scratch + layout.total_counter);
    uint32_t* keep = reinterpret_cast<uint32_t*>(branch.scratch + layout.keep);
    Keypoint* compacted = reinterpret_cast<Keypoint*>(branch.scratch + layout.compacted);

    V1GaussianWeights weights;
    ErrorCode status = v1_make_gaussian_weights(kBriefSmoothSigma, kBriefSmoothRadius, weights);
    if (status != ErrorCode::Success) return status;

    GrayImage smoothed;
    smoothed.data = smoothed_data;
    smoothed.stride = static_cast<std::size_t>(branch.gray.width) * sizeof(float);
    smoothed.width = branch.gray.width;
    smoothed.height = branch.gray.height;
    smoothed.channels = 1;

    status = v1_gaussian_blur(branch.gray, smoothed, temp, weights, stream);
    if (status != ErrorCode::Success) return status;

    const uint32_t capacity = static_cast<uint32_t>(branch.feature_capacity);
    const unsigned grid = describe_blocks_for(branch.feature_capacity);

    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::validate_kernel<<<1, v1_s3::kThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, branch.keypoints, capacity));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::keep_flags_kernel<<<grid, v1_s3::kThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, branch.keypoints, branch.gray.width, branch.gray.height, keep));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::exclusive_scan_kernel<<<1, v1_s3::kScanThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, keep, total));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::describe_kernel<<<grid, v1_s3::kThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, branch.keypoints, smoothed_data, branch.gray.width,
        branch.gray.height, keep, branch.descriptors, compacted));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::copy_back_kernel<<<grid, v1_s3::kThreads, 0, stream>>>(
        branch.counts, total, compacted, branch.keypoints));
    PANORAMA_LAUNCH_KERNEL(stream, v1_s3::publish_kernel<<<1, 1, 0, stream>>>(
        branch.counts, total, true));

    return cudaPeekAtLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

}  // namespace panorama
