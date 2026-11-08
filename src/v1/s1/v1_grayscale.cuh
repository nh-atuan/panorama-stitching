// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_GRAYSCALE_CUH
#define GROUP16_V1_GRAYSCALE_CUH

#include "common/kernel_timing.cuh"
#include "common/common.h"
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>

namespace panorama {
namespace v1_s1 {

// 32 x 8: one warp reads 32 consecutive pixels of a row (S1 design, section 6.2).
constexpr unsigned kGrayBlockX = 32;
constexpr unsigned kGrayBlockY = 8;

// One thread per pixel. Same expression and evaluation order as convert_to_gray of V0, so
// the value matches bit for bit with --fmad=false. Padding of both images is not touched.
__global__ void grayscale_kernel(const std::uint8_t* rgb, std::size_t rgb_stride, unsigned char* gray,
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

// Enqueues the grayscale kernel; views must be validated by the caller.
inline void launch_grayscale(const Image& input, const GrayImage& gray, cudaStream_t stream) {
    const dim3 block(kGrayBlockX, kGrayBlockY);
    const dim3 grid((static_cast<unsigned>(input.width) + kGrayBlockX - 1) / kGrayBlockX,
                    (static_cast<unsigned>(input.height) + kGrayBlockY - 1) / kGrayBlockY);
    PANORAMA_LAUNCH_KERNEL(stream, grayscale_kernel<<<grid, block, 0, stream>>>(input.data, input.stride,
                                                 reinterpret_cast<unsigned char*>(gray.data), gray.stride,
                                                 input.width, input.height));
}

}  // namespace v1_s1
}  // namespace panorama

#endif  // GROUP16_V1_GRAYSCALE_CUH
