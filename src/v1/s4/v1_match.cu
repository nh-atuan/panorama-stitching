// Authors: Le Thuong De (23120232)
// External source: none
// Implements the team's S4 design; V0 remains the independent scalar reference.

#include "v1/s4/v1_match.h"
#include "v1/s4/v1_match_internal.cuh"
#include "v1/common/v1_nvtx.cuh"
#include "common/feature_support.h"
#include <cmath>
#include <limits>

namespace panorama {
namespace {
using match_gpu::TopTwo;

__global__ void validate_matching(DeviceWorkspace w) {
    if (w.d_counts->status != ErrorCode::Success) return;
    w.d_counts->matches = 0;
    const DeviceCounts c = *w.d_counts;
    if (c.descriptorsA > w.descriptor_capacityA || c.descriptorsB > w.descriptor_capacityB)
        w.d_counts->status = ErrorCode::InvalidArgument;
    else if (c.descriptorsA == 0 || c.descriptorsB < 2)
        w.d_counts->status = ErrorCode::InsufficientKeypoints;
}

__global__ void nearest_two(DeviceWorkspace w, TopTwo* pairs) {
    if (w.d_counts->status != ErrorCode::Success || blockIdx.x >= w.d_counts->descriptorsA) return;
    __shared__ TopTwo partial[256];
    TopTwo pair = {{257u, -1}, {257u, -1}};
    const Descriptor a = w.d_descriptorsA[blockIdx.x];
    for (std::uint32_t j = threadIdx.x; j < w.d_counts->descriptorsB; j += blockDim.x) {
        std::uint32_t distance = 0;
        for (int word = 0; word < 8; ++word) distance += __popc(a.data[word] ^ w.d_descriptorsB[j].data[word]);
        match_gpu::insert({distance, static_cast<std::int32_t>(j)}, pair);
    }
    partial[threadIdx.x] = pair;
    __syncthreads();
    for (unsigned width = blockDim.x / 2; width > 0; width /= 2) {
        if (threadIdx.x < width) {
            match_gpu::insert(partial[threadIdx.x + width].best, partial[threadIdx.x]);
            match_gpu::insert(partial[threadIdx.x + width].second, partial[threadIdx.x]);
        }
        __syncthreads();
    }
    if (threadIdx.x == 0) pairs[blockIdx.x] = partial[0];
}

__global__ void prefix_matching(DeviceWorkspace w, const TopTwo* pairs, std::uint32_t* prefix) {
    if (w.d_counts->status != ErrorCode::Success) return;
    std::uint32_t total = 0;
    for (std::uint32_t i = 0; i < w.d_counts->descriptorsA; ++i) {
        prefix[i] = total;
        const TopTwo p = pairs[i];
        total += p.second.index >= 0 && 5u * p.best.distance < 4u * p.second.distance;
    }
    if (total < 4) w.d_counts->status = ErrorCode::InsufficientMatches;
    else if (total > w.match_capacity) w.d_counts->status = ErrorCode::InvalidArgument;
    else w.d_counts->matches = total;
}

__global__ void scatter_matching(DeviceWorkspace w, const TopTwo* pairs, const std::uint32_t* prefix) {
    const std::uint32_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (w.d_counts->status != ErrorCode::Success || i >= w.d_counts->descriptorsA) return;
    const TopTwo p = pairs[i];
    if (p.second.index >= 0 && 5u * p.best.distance < 4u * p.second.distance) {
        Match match;
        match.indexA = static_cast<std::int32_t>(i);
        match.indexB = p.best.index;
        match.distance = p.best.distance;
        w.d_matches[prefix[i]] = match;
    }
}
}  // namespace

std::size_t v1_match_scratch_bytes(std::size_t capacity) {
    const std::size_t unit = sizeof(TopTwo) + sizeof(std::uint32_t);
    if (capacity > static_cast<std::size_t>(INT32_MAX) || capacity > SIZE_MAX / unit) return 0;
    return capacity * unit;
}

ErrorCode v1_match_with_block_size(DeviceWorkspace& w, const Config& config, cudaStream_t stream, int threads) {
    V1NvtxRange stage("S4.match");
    if (!std::isfinite(config.match_ratio_threshold) || config.match_ratio_threshold != feature_policy::kRatio ||
        config.match_cross_check != 0u) return ErrorCode::InvalidConfig;
    if (threads < 32 || threads > 256 || (threads & (threads - 1))) return ErrorCode::InvalidArgument;
    if (!w.d_counts || (w.match_capacity && !w.d_matches) ||
        (w.descriptor_capacityA && !w.d_descriptorsA) || (w.descriptor_capacityB && !w.d_descriptorsB) ||
        w.descriptor_capacityA > static_cast<std::size_t>(INT32_MAX) ||
        w.descriptor_capacityB > static_cast<std::size_t>(INT32_MAX)) return ErrorCode::InvalidArgument;
    const std::size_t bytes = v1_match_scratch_bytes(w.descriptor_capacityA);
    if (bytes && (!w.d_scratch || w.scratch_capacity_bytes < bytes ||
                  reinterpret_cast<std::uintptr_t>(w.d_scratch) % alignof(TopTwo)))
        return ErrorCode::AllocationFailed;
    TopTwo* pairs = reinterpret_cast<TopTwo*>(w.d_scratch);
    std::uint32_t* prefix = bytes ? reinterpret_cast<std::uint32_t*>(pairs + w.descriptor_capacityA) : nullptr;
    validate_matching<<<1, 1, 0, stream>>>(w);
    if (w.descriptor_capacityA) {
        {
            V1NvtxRange range("S4.nearest_two");
            nearest_two<<<static_cast<unsigned>(w.descriptor_capacityA), threads, 0, stream>>>(w, pairs);
        }
        {
            V1NvtxRange range("S4.prefix");
            prefix_matching<<<1, 1, 0, stream>>>(w, pairs, prefix);
        }
        {
            V1NvtxRange range("S4.scatter");
            scatter_matching<<<static_cast<unsigned>((w.descriptor_capacityA + threads - 1) / threads), threads, 0, stream>>>(w, pairs, prefix);
        }
    }
    return cudaPeekAtLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

ErrorCode v1_match(DeviceWorkspace& w, const Config& config, cudaStream_t stream) {
    return v1_match_with_block_size(w, config, stream, 128);
}
}  // namespace panorama
