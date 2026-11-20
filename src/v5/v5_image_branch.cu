// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v5/v5_image_branch.h"
#include "common/brief_pattern.h"
#include "common/fast_corner.h"
#include "common/feature_border.h"
#include "common/image_layout.h"
#include "common/kernel_timing.cuh"
#include "v1/common/v1_gaussian_blur.h"
#include "v1/common/v1_nvtx.cuh"
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
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

// -----------------------------------------------------------------------------
// S1 Kernels & Helpers (Grayscale)
// -----------------------------------------------------------------------------
constexpr unsigned kGrayBlockX = 32;
constexpr unsigned kGrayBlockY = 8;

__global__ void v5_grayscale_kernel(const std::uint8_t* rgb, std::size_t rgb_stride, unsigned char* gray,
                                    std::size_t gray_stride, std::int32_t width, std::int32_t height) {
    const std::int32_t x = static_cast<std::int32_t>(blockIdx.x * blockDim.x + threadIdx.x);
    const std::int32_t y = static_cast<std::int32_t>(blockIdx.y * blockDim.y + threadIdx.y);
    if (x >= width || y >= height) return;
    const std::uint8_t* in = rgb + static_cast<std::size_t>(y) * rgb_stride + 3 * static_cast<std::size_t>(x);
    const float r = static_cast<float>(in[0]);
    const float g = static_cast<float>(in[1]);
    const float b = static_cast<float>(in[2]);
    reinterpret_cast<float*>(gray + static_cast<std::size_t>(y) * gray_stride)[x] =
        (0.299f * r + 0.587f * g + 0.114f * b) / 255.0f;
}

inline void v5_launch_grayscale(const Image& input, const GrayImage& gray, cudaStream_t stream) {
    const dim3 block(kGrayBlockX, kGrayBlockY);
    const dim3 grid((static_cast<unsigned>(input.width) + kGrayBlockX - 1) / kGrayBlockX,
                    (static_cast<unsigned>(input.height) + kGrayBlockY - 1) / kGrayBlockY);
    PANORAMA_LAUNCH_KERNEL(stream, v5_grayscale_kernel<<<grid, block, 0, stream>>>(
        input.data, input.stride, reinterpret_cast<unsigned char*>(gray.data), gray.stride,
        input.width, input.height));
}

// -----------------------------------------------------------------------------
// S2 Kernels & Helpers (FAST Corner, NMS, Bitonic Sort)
// -----------------------------------------------------------------------------
static __constant__ std::int32_t v5_fast_circle[kFastCircleSize][2] = {
    {0, -3}, {1, -3}, {2, -2}, {3, -1}, {3, 0}, {3, 1}, {2, 2}, {1, 3},
    {0, 3}, {-1, 3}, {-2, 2}, {-3, 1}, {-3, 0}, {-3, -1}, {-2, -2}, {-1, -3}};

constexpr unsigned long long v5_kPaddingKey = ~0ULL;
constexpr unsigned v5_kSortThreads = 256;

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

inline std::uint32_t v5_next_power_of_two(std::uint32_t n) {
    std::uint32_t p = 1;
    while (p < n) p <<= 1;
    return p;
}

inline unsigned v5_blocks_for(std::uint32_t n) { return (n + v5_kSortThreads - 1) / v5_kSortThreads; }

inline bool make_detect_layout(std::int32_t width, std::int32_t height, DetectLayout& layout) {
    layout = DetectLayout();
    if (!gray_pixel_count(width, height, layout.pixels)) return false;
    if (layout.pixels > std::numeric_limits<std::uint32_t>::max()) return false;
    if (!has_region(width, height)) return true;
    const std::size_t half_w = (static_cast<std::size_t>(width) + 1) / 2;
    const std::size_t half_h = (static_cast<std::size_t>(height) + 1) / 2;
    layout.capacity = static_cast<std::uint32_t>(half_w * half_h);
    const std::size_t slots = v5_next_power_of_two(layout.capacity);
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

__device__ inline float v5_gray_at(const unsigned char* gray, std::size_t stride, std::int32_t x, std::int32_t y) {
    return reinterpret_cast<const float*>(gray + static_cast<std::size_t>(y) * stride)[x];
}

__device__ inline float v5_fast_score_at(const unsigned char* gray, std::size_t stride, std::int32_t x,
                                         std::int32_t y, float threshold) {
    const float center = v5_gray_at(gray, stride, x, y);
    float ring[kFastCircleSize];
    std::int32_t state[kFastCircleSize];
    for (std::int32_t i = 0; i < kFastCircleSize; ++i) {
        ring[i] = v5_gray_at(gray, stride, x + v5_fast_circle[i][0], y + v5_fast_circle[i][1]);
        const float d = ring[i] - center;
        state[i] = d > threshold ? 1 : (d < -threshold ? -1 : 0);
    }
    bool corner = false;
    std::int32_t bright_run = 0, dark_run = 0;
    for (std::int32_t step = 0; step < kFastCircleSize + kFastArcLength - 1; ++step) {
        const std::int32_t s = state[step % kFastCircleSize];
        bright_run = s > 0 ? bright_run + 1 : 0;
        dark_run = s < 0 ? dark_run + 1 : 0;
        if (bright_run >= kFastArcLength || dark_run >= kFastArcLength) {
            corner = true;
            break;
        }
    }
    if (!corner) return 0.0f;
    float bright_sum = 0.0f, dark_sum = 0.0f;
    for (std::int32_t i = 0; i < kFastCircleSize; ++i) {
        const float d = ring[i] - center;
        if (state[i] > 0) bright_sum += d - threshold;
        if (state[i] < 0) dark_sum += -d - threshold;
    }
    return bright_sum > dark_sum ? bright_sum : dark_sum;
}

__global__ void v5_fast_score_kernel(const unsigned char* gray, std::size_t stride, std::int32_t width,
                                     std::int32_t height, float threshold, float* scores) {
    const std::int32_t x = kFeatureBorder + static_cast<std::int32_t>(blockIdx.x * blockDim.x + threadIdx.x);
    const std::int32_t y = kFeatureBorder + static_cast<std::int32_t>(blockIdx.y * blockDim.y + threadIdx.y);
    if (x >= width - kFeatureBorder || y >= height - kFeatureBorder) return;
    scores[static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + x] =
        v5_fast_score_at(gray, stride, x, y, threshold);
}

__device__ inline unsigned long long v5_candidate_key(float score, std::uint32_t raster) {
    const std::uint32_t high = ~static_cast<std::uint32_t>(__float_as_uint(score));
    return (static_cast<unsigned long long>(high) << 32) | raster;
}

__device__ inline float v5_key_score(unsigned long long key) {
    return __uint_as_float(~static_cast<std::uint32_t>(key >> 32));
}

__device__ inline std::uint32_t v5_key_raster(unsigned long long key) {
    return static_cast<std::uint32_t>(key & 0xFFFFFFFFULL);
}

__global__ void v5_nms_kernel(const float* scores, std::int32_t width, std::int32_t height,
                              std::uint32_t* count, unsigned long long* keys, std::uint32_t capacity) {
    const std::int32_t x = kFeatureBorder + static_cast<std::int32_t>(blockIdx.x * blockDim.x + threadIdx.x);
    const std::int32_t y = kFeatureBorder + static_cast<std::int32_t>(blockIdx.y * blockDim.y + threadIdx.y);
    if (x >= width - kFeatureBorder || y >= height - kFeatureBorder) return;
    const std::size_t w = static_cast<std::size_t>(width);
    const float s = scores[static_cast<std::size_t>(y) * w + x];
    if (!(s > 0.0f)) return;
    for (std::int32_t dy = -1; dy <= 1; ++dy) {
        for (std::int32_t dx = -1; dx <= 1; ++dx) {
            if (dx == 0 && dy == 0) continue;
            const float q = scores[static_cast<std::size_t>(y + dy) * w + (x + dx)];
            const bool earlier = dy < 0 || (dy == 0 && dx < 0);
            if (q > s || (earlier && q == s)) return;
        }
    }
    const std::uint32_t slot = atomicAdd(count, 1u);
    const std::uint32_t raster =
        static_cast<std::uint32_t>(y) * static_cast<std::uint32_t>(width) + static_cast<std::uint32_t>(x);
    if (slot < capacity) keys[slot] = v5_candidate_key(s, raster);
}

__global__ void v5_pad_keys_kernel(unsigned long long* keys, std::uint32_t count, std::uint32_t padded) {
    const std::uint32_t i = count + blockIdx.x * blockDim.x + threadIdx.x;
    if (i < padded) keys[i] = v5_kPaddingKey;
}

__global__ void v5_bitonic_step_kernel(unsigned long long* keys, std::uint32_t n, std::uint32_t j, std::uint32_t k) {
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const std::uint32_t partner = i ^ j;
    if (partner <= i) return;
    const unsigned long long a = keys[i], b = keys[partner];
    const bool ascending = (i & k) == 0;
    if ((a > b) == ascending) {
        keys[i] = b;
        keys[partner] = a;
    }
}

__global__ void v5_write_keypoints_kernel(const unsigned long long* keys, std::uint32_t count, std::uint32_t width,
                                          Keypoint* keypoints) {
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= count) return;
    const unsigned long long key = keys[i];
    const std::uint32_t raster = v5_key_raster(key);
    Keypoint k;
    k.x = static_cast<float>(raster % width);
    k.y = static_cast<float>(raster / width);
    k.score = v5_key_score(key);
    k.angle = 0.0f;
    keypoints[i] = k;
}

inline cudaError_t v5_sort_keys(unsigned long long* keys, std::uint32_t count, cudaStream_t stream) {
    if (count < 2) return cudaSuccess;
    const std::uint32_t n = v5_next_power_of_two(count);
    if (n > count) {
        PANORAMA_LAUNCH_KERNEL(stream, v5_pad_keys_kernel<<<v5_blocks_for(n - count), v5_kSortThreads, 0, stream>>>(keys, count, n));
    }
    for (std::uint32_t k = 2; k <= n; k <<= 1) {
        for (std::uint32_t j = k >> 1; j > 0; j >>= 1) {
            PANORAMA_LAUNCH_KERNEL(stream, v5_bitonic_step_kernel<<<v5_blocks_for(n), v5_kSortThreads, 0, stream>>>(keys, n, j, k));
        }
    }
    return cudaPeekAtLastError();
}

__global__ void v5_publish_count_kernel(std::uint32_t* field, std::uint32_t value) {
    if (threadIdx.x || blockIdx.x) return;
    *field = value;
}

// -----------------------------------------------------------------------------
// S3 Kernels & Helpers (BRIEF Descriptor & Compaction)
// -----------------------------------------------------------------------------
static __constant__ BriefTest v5_c_brief_pattern[kBriefTests];
constexpr unsigned v5_kThreads = 256;
constexpr unsigned v5_kScanThreads = 1024;

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
    return static_cast<unsigned>(std::max<std::size_t>(1, (n + v5_kThreads - 1) / v5_kThreads));
}

__device__ inline bool v5_patch_centre(const Keypoint& keypoint, std::int32_t width, std::int32_t height,
                                       std::int32_t& cx, std::int32_t& cy) {
    const double rx = floor(static_cast<double>(keypoint.x) + 0.5);
    const double ry = floor(static_cast<double>(keypoint.y) + 0.5);
    if (rx < kBriefPatchRadius || rx > width - 1 - kBriefPatchRadius) return false;
    if (ry < kBriefPatchRadius || ry > height - 1 - kBriefPatchRadius) return false;
    cx = static_cast<std::int32_t>(rx);
    cy = static_cast<std::int32_t>(ry);
    return true;
}

__device__ inline Descriptor v5_describe_patch(const float* smoothed, std::int32_t width, std::int32_t cx,
                                               std::int32_t cy) {
    const std::ptrdiff_t stride = static_cast<std::ptrdiff_t>(width);
    const float* centre = smoothed + static_cast<std::size_t>(cy) * static_cast<std::size_t>(width) + cx;
    Descriptor d;
    for (std::int32_t k = 0; k < kBriefTests; ++k) {
        const BriefTest t = v5_c_brief_pattern[k];
        const float first = centre[t.ay * stride + t.ax];
        const float second = centre[t.by * stride + t.bx];
        if (first < second) d.data[k / 32] |= 1u << (k % 32);
    }
    return d;
}

__global__ void v5_validate_kernel(DeviceCounts* counts, const std::uint32_t* count, const Keypoint* keypoints,
                                   std::uint32_t capacity) {
    if (counts->status != ErrorCode::Success) return;
    const std::uint32_t n = *count;
    int bad = n > capacity;
    for (std::uint32_t i = threadIdx.x; !bad && i < n; i += blockDim.x) {
        bad = !isfinite(keypoints[i].x) || !isfinite(keypoints[i].y);
    }
    bad = __syncthreads_or(bad);
    if (bad && threadIdx.x == 0) {
        counts->status = ErrorCode::InvalidArgument;
        counts->descriptorsA = counts->descriptorsB = 0;
    }
}

__global__ void v5_keep_flags_kernel(const DeviceCounts* counts, const std::uint32_t* count, const Keypoint* keypoints,
                                     std::int32_t width, std::int32_t height, std::uint32_t* keep) {
    if (counts->status != ErrorCode::Success) return;
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= *count) return;
    std::int32_t cx = 0, cy = 0;
    keep[i] = v5_patch_centre(keypoints[i], width, height, cx, cy) ? 1u : 0u;
}

__global__ void v5_exclusive_scan_kernel(const DeviceCounts* counts, const std::uint32_t* count, std::uint32_t* keep,
                                         std::uint32_t* total) {
    if (counts->status != ErrorCode::Success) return;
    __shared__ std::uint32_t buffer[v5_kScanThreads];
    __shared__ std::uint32_t carry;
    const unsigned t = threadIdx.x;
    if (t == 0) carry = 0;
    __syncthreads();
    const std::uint32_t n = *count;
    for (std::uint32_t base = 0; base < n; base += v5_kScanThreads) {
        const std::uint32_t i = base + t;
        const std::uint32_t value = i < n ? keep[i] : 0u;
        buffer[t] = value;
        __syncthreads();
        for (unsigned offset = 1; offset < v5_kScanThreads; offset <<= 1) {
            const std::uint32_t add = t >= offset ? buffer[t - offset] : 0u;
            __syncthreads();
            buffer[t] += add;
            __syncthreads();
        }
        if (i < n) keep[i] = carry + buffer[t] - value;
        __syncthreads();
        if (t == v5_kScanThreads - 1) carry += buffer[t];
        __syncthreads();
    }
    if (t == 0) *total = carry;
}

__global__ void v5_describe_kernel(const DeviceCounts* counts, const std::uint32_t* count, const Keypoint* keypoints,
                                   const float* smoothed, std::int32_t width, std::int32_t height,
                                   const std::uint32_t* offset, Descriptor* descriptors, Keypoint* compacted) {
    if (counts->status != ErrorCode::Success) return;
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= *count) return;
    const Keypoint keypoint = keypoints[i];
    std::int32_t cx = 0, cy = 0;
    if (!v5_patch_centre(keypoint, width, height, cx, cy)) return;
    const std::uint32_t slot = offset[i];
    descriptors[slot] = v5_describe_patch(smoothed, width, cx, cy);
    compacted[slot] = keypoint;
}

__global__ void v5_copy_back_kernel(const DeviceCounts* counts, const std::uint32_t* total, const Keypoint* compacted,
                                    Keypoint* keypoints) {
    if (counts->status != ErrorCode::Success) return;
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < *total) keypoints[i] = compacted[i];
}

__global__ void v5_publish_kernel(DeviceCounts* counts, const std::uint32_t* total) {
    if (counts->status != ErrorCode::Success) return;
    counts->keypointsA = counts->descriptorsA = *total;
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
    if (cudaMemcpyToSymbolAsync(v5_c_brief_pattern, kBriefPattern, sizeof(kBriefPattern), 0,
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

    v5_launch_grayscale(branch.image, branch.gray, stream);
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
        PANORAMA_LAUNCH_KERNEL(stream, v5_fast_score_kernel<<<grid, block, 0, stream>>>(
            pixels, branch.gray.stride, branch.gray.width, branch.gray.height,
            config.fast_threshold, scores));
        PANORAMA_LAUNCH_KERNEL(stream, v5_nms_kernel<<<grid, block, 0, stream>>>(
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
        if (v5_sort_keys(keys, candidates, stream) != cudaSuccess) return ErrorCode::CudaFailure;
        if (kept > 0) {
            PANORAMA_LAUNCH_KERNEL(stream, v5_write_keypoints_kernel<<<v5_blocks_for(kept), v5_kSortThreads, 0, stream>>>(
                keys, kept, static_cast<uint32_t>(branch.gray.width), branch.keypoints));
        }
    }
    PANORAMA_LAUNCH_KERNEL(stream, v5_publish_count_kernel<<<1, 1, 0, stream>>>(&branch.counts->keypointsA, kept));
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

    PANORAMA_LAUNCH_KERNEL(stream, v5_validate_kernel<<<1, v5_kThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, branch.keypoints, capacity));
    PANORAMA_LAUNCH_KERNEL(stream, v5_keep_flags_kernel<<<grid, v5_kThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, branch.keypoints, branch.gray.width, branch.gray.height, keep));
    PANORAMA_LAUNCH_KERNEL(stream, v5_exclusive_scan_kernel<<<1, v5_kScanThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, keep, total));
    PANORAMA_LAUNCH_KERNEL(stream, v5_describe_kernel<<<grid, v5_kThreads, 0, stream>>>(
        branch.counts, &branch.counts->keypointsA, branch.keypoints, smoothed_data, branch.gray.width,
        branch.gray.height, keep, branch.descriptors, compacted));
    PANORAMA_LAUNCH_KERNEL(stream, v5_copy_back_kernel<<<grid, v5_kThreads, 0, stream>>>(
        branch.counts, total, compacted, branch.keypoints));
    PANORAMA_LAUNCH_KERNEL(stream, v5_publish_kernel<<<1, 1, 0, stream>>>(
        branch.counts, total));

    return cudaPeekAtLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

}  // namespace panorama
