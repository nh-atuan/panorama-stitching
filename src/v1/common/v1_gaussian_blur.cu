// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#include "common/kernel_timing.cuh"
#include "v1/common/v1_gaussian_blur.h"
#include "common/image_layout.h"
#include <cstddef>

namespace panorama {
namespace {

// 32 x 8: one warp reads 32 consecutive pixels of a row (S1 design, section 6.2).
constexpr unsigned kBlockX = 32;
constexpr unsigned kBlockY = 8;

__device__ std::int32_t clamp_index(std::int32_t i, std::int32_t size) {
    return i < 0 ? 0 : (i >= size ? size - 1 : i);
}

// temp (packed) = horizontal blur of src, one thread per pixel.
__global__ void blur_rows(const unsigned char* src, std::size_t src_stride, float* temp,
                          std::int32_t width, std::int32_t height, V1GaussianWeights weights) {
    const std::int32_t x = static_cast<std::int32_t>(blockIdx.x * blockDim.x + threadIdx.x);
    const std::int32_t y = static_cast<std::int32_t>(blockIdx.y * blockDim.y + threadIdx.y);
    if (x >= width || y >= height) return;
    const float* in = reinterpret_cast<const float*>(src + static_cast<std::size_t>(y) * src_stride);
    const std::int32_t radius = weights.radius;
    float sum = 0.0f;
    for (std::int32_t k = -radius; k <= radius; ++k) {
        sum += weights.values[k + radius] * in[clamp_index(x + k, width)];
    }
    temp[static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + x] = sum;
}

// dst = vertical blur of temp; taps summed from -radius to +radius like V0.
__global__ void blur_columns(const float* temp, unsigned char* dst, std::size_t dst_stride,
                             std::int32_t width, std::int32_t height, V1GaussianWeights weights) {
    const std::int32_t x = static_cast<std::int32_t>(blockIdx.x * blockDim.x + threadIdx.x);
    const std::int32_t y = static_cast<std::int32_t>(blockIdx.y * blockDim.y + threadIdx.y);
    if (x >= width || y >= height) return;
    const std::int32_t radius = weights.radius;
    const std::size_t w = static_cast<std::size_t>(width);
    float sum = 0.0f;
    for (std::int32_t k = -radius; k <= radius; ++k) {
        sum += weights.values[k + radius] * temp[static_cast<std::size_t>(clamp_index(y + k, height)) * w + x];
    }
    reinterpret_cast<float*>(dst + static_cast<std::size_t>(y) * dst_stride)[x] = sum;
}

}  // namespace

ErrorCode v1_make_gaussian_weights(float sigma, std::int32_t radius, V1GaussianWeights& weights) {
    V1GaussianWeights result = {};
    const ErrorCode status = make_gaussian_weights(sigma, radius, result.values);
    if (status != ErrorCode::Success) return status;
    result.radius = radius;
    weights = result;
    return ErrorCode::Success;
}

ErrorCode v1_gaussian_blur(const GrayImage& src, const GrayImage& dst, float* temp,
                           const V1GaussianWeights& weights, cudaStream_t stream) {
    if (!valid_gray_image(src) || !valid_gray_image(dst) || src.width != dst.width ||
        src.height != dst.height) {
        return ErrorCode::InvalidImage;
    }
    std::size_t pixels = 0;
    if (!gray_pixel_count(src.width, src.height, pixels)) return ErrorCode::InvalidImage;
    if (weights.radius < 1 || weights.radius > kMaxGaussianRadius) return ErrorCode::InvalidConfig;
    if (!temp) return ErrorCode::InvalidArgument;

    const dim3 block(kBlockX, kBlockY);
    const dim3 grid((static_cast<unsigned>(src.width) + kBlockX - 1) / kBlockX,
                    (static_cast<unsigned>(src.height) + kBlockY - 1) / kBlockY);
    PANORAMA_LAUNCH_KERNEL(stream, blur_rows<<<grid, block, 0, stream>>>(reinterpret_cast<const unsigned char*>(src.data), src.stride,
                                          temp, src.width, src.height, weights));
    PANORAMA_LAUNCH_KERNEL(stream, blur_columns<<<grid, block, 0, stream>>>(temp, reinterpret_cast<unsigned char*>(dst.data), dst.stride,
                                             dst.width, dst.height, weights));
    return cudaPeekAtLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

}  // namespace panorama
