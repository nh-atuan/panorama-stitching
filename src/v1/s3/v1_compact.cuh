// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_COMPACT_CUH
#define GROUP16_V1_COMPACT_CUH

#include "common/common.h"
#include "v1/s3/v1_brief_kernel.cuh"
#include <cuda_runtime.h>
#include <cstdint>

namespace panorama {
namespace v1_s3 {

constexpr unsigned kThreads = 256;
constexpr unsigned kScanThreads = 1024;

// Every kernel below does nothing once d_counts->status holds an error, like S4.
// `count` points at d_counts->keypointsA or keypointsB.

// Rejects a count above the buffer capacity and non-finite coordinates, as V0 does with
// InvalidArgument; keypoints stay unchanged and both descriptor counts become 0.
__global__ void validate_kernel(DeviceCounts* counts, const std::uint32_t* count, const Keypoint* keypoints,
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

// keep[i] = 1 when the patch of keypoint i lies inside the image.
__global__ void keep_flags_kernel(const DeviceCounts* counts, const std::uint32_t* count, const Keypoint* keypoints,
                                  std::int32_t width, std::int32_t height, std::uint32_t* keep) {
    if (counts->status != ErrorCode::Success) return;
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= *count) return;
    std::int32_t cx = 0, cy = 0;
    keep[i] = patch_centre(keypoints[i], width, height, cx, cy) ? 1u : 0u;
}

// One block: keep[] becomes its exclusive prefix sum, *total the number kept.
__global__ void exclusive_scan_kernel(const DeviceCounts* counts, const std::uint32_t* count, std::uint32_t* keep,
                                      std::uint32_t* total) {
    if (counts->status != ErrorCode::Success) return;
    __shared__ std::uint32_t buffer[kScanThreads];
    __shared__ std::uint32_t carry;
    const unsigned t = threadIdx.x;
    if (t == 0) carry = 0;
    __syncthreads();
    const std::uint32_t n = *count;
    for (std::uint32_t base = 0; base < n; base += kScanThreads) {
        const std::uint32_t i = base + t;
        const std::uint32_t value = i < n ? keep[i] : 0u;
        buffer[t] = value;
        __syncthreads();
        for (unsigned offset = 1; offset < kScanThreads; offset <<= 1) {
            const std::uint32_t add = t >= offset ? buffer[t - offset] : 0u;
            __syncthreads();
            buffer[t] += add;
            __syncthreads();
        }
        if (i < n) keep[i] = carry + buffer[t] - value;
        __syncthreads();
        if (t == kScanThreads - 1) carry += buffer[t];
        __syncthreads();
    }
    if (t == 0) *total = carry;
}

// Kept keypoint i goes to slot offset[i]: its descriptor straight into `descriptors`, the
// keypoint into `compacted` (scratch), so the input list is not overwritten while being read.
__global__ void describe_kernel(const DeviceCounts* counts, const std::uint32_t* count, const Keypoint* keypoints,
                                const float* smoothed, std::int32_t width, std::int32_t height,
                                const std::uint32_t* offset, Descriptor* descriptors, Keypoint* compacted) {
    if (counts->status != ErrorCode::Success) return;
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= *count) return;
    const Keypoint keypoint = keypoints[i];
    std::int32_t cx = 0, cy = 0;
    if (!patch_centre(keypoint, width, height, cx, cy)) return;
    const std::uint32_t slot = offset[i];
    descriptors[slot] = describe_patch(smoothed, width, cx, cy);
    compacted[slot] = keypoint;
}

__global__ void copy_back_kernel(const DeviceCounts* counts, const std::uint32_t* total, const Keypoint* compacted,
                                 Keypoint* keypoints) {
    if (counts->status != ErrorCode::Success) return;
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < *total) keypoints[i] = compacted[i];
}

// Publishes the kept count as both the keypoint and the descriptor count of the image.
__global__ void publish_kernel(DeviceCounts* counts, const std::uint32_t* total, bool image_a) {
    if (counts->status != ErrorCode::Success) return;
    if (image_a) {
        counts->keypointsA = counts->descriptorsA = *total;
    } else {
        counts->keypointsB = counts->descriptorsB = *total;
    }
}

}  // namespace v1_s3
}  // namespace panorama

#endif  // GROUP16_V1_COMPACT_CUH
