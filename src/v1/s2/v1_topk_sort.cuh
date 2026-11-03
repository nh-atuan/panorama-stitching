// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_TOPK_SORT_CUH
#define GROUP16_V1_TOPK_SORT_CUH

#include "common/common.h"
#include "v1/s2/v1_nms.cuh"
#include <cuda_runtime.h>
#include <cstdint>

namespace panorama {
namespace v1_s2 {

constexpr unsigned kSortThreads = 256;

inline unsigned blocks_for(std::uint32_t n) { return (n + kSortThreads - 1) / kSortThreads; }

// Smallest power of two >= n, for n >= 1 and n <= 2^31.
inline std::uint32_t next_power_of_two(std::uint32_t n) {
    std::uint32_t p = 1;
    while (p < n) p <<= 1;
    return p;
}

// keys[count .. padded) = kPaddingKey, so padding sorts after every real key.
__global__ void pad_keys_kernel(unsigned long long* keys, std::uint32_t count, std::uint32_t padded) {
    const std::uint32_t i = count + blockIdx.x * blockDim.x + threadIdx.x;
    if (i < padded) keys[i] = kPaddingKey;
}

// One compare-exchange step (k, j) of an ascending bitonic sort over n = 2^m keys.
__global__ void bitonic_step_kernel(unsigned long long* keys, std::uint32_t n, std::uint32_t j, std::uint32_t k) {
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

// The first `count` sorted keys become keypoints: integer pixel centre, score V, angle 0.
__global__ void write_keypoints_kernel(const unsigned long long* keys, std::uint32_t count, std::uint32_t width,
                                       Keypoint* keypoints) {
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= count) return;
    const unsigned long long key = keys[i];
    const std::uint32_t raster = key_raster(key);
    Keypoint k;
    k.x = static_cast<float>(raster % width);
    k.y = static_cast<float>(raster / width);
    k.score = key_score(key);
    k.angle = 0.0f;
    keypoints[i] = k;
}

// Ascending sort of keys[0 .. count) in place; keys must hold next_power_of_two(count) slots.
inline cudaError_t sort_keys(unsigned long long* keys, std::uint32_t count, cudaStream_t stream) {
    if (count < 2) return cudaSuccess;
    const std::uint32_t n = next_power_of_two(count);
    if (n > count) pad_keys_kernel<<<blocks_for(n - count), kSortThreads, 0, stream>>>(keys, count, n);
    for (std::uint32_t k = 2; k <= n; k <<= 1) {
        for (std::uint32_t j = k >> 1; j > 0; j >>= 1) {
            bitonic_step_kernel<<<blocks_for(n), kSortThreads, 0, stream>>>(keys, n, j, k);
        }
    }
    return cudaPeekAtLastError();
}

}  // namespace v1_s2
}  // namespace panorama

#endif  // GROUP16_V1_TOPK_SORT_CUH
