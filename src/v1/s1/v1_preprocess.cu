// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#include "v1/s1/v1_preprocess.h"
#include "common/image_layout.h"
#include "v1/common/v1_gaussian_blur.h"
#include "v1/common/v1_nvtx.cuh"
#include "v1/s1/v1_grayscale.cuh"
#include <algorithm>
#include <cstdint>

namespace panorama {
namespace {

// Same checks as v0_preprocess: RGB input with stride in bytes, gray output of the same size.
bool valid_pair(const Image& input, const GrayImage& gray) {
    std::size_t pixels = 0;
    return input.channels == 3 && rows_fit(input.data, input.stride, input.width, input.height, 3, 1) &&
           valid_gray_image(gray) && gray.width == input.width && gray.height == input.height &&
           gray_pixel_count(input.width, input.height, pixels);
}

ErrorCode preprocess_one(const Image& input, const GrayImage& gray, float* temp,
                         const V1GaussianWeights& weights, cudaStream_t stream) {
    v1_s1::launch_grayscale(input, gray, stream);
    if (cudaPeekAtLastError() != cudaSuccess) return ErrorCode::CudaFailure;
    return v1_gaussian_blur(gray, gray, temp, weights, stream);
}

}  // namespace

std::size_t v1_preprocess_scratch_bytes(std::int32_t width, std::int32_t height) {
    std::size_t pixels = 0;
    if (!gray_pixel_count(width, height, pixels)) return 0;
    return pixels * sizeof(float);
}

ErrorCode v1_preprocess(DeviceWorkspace& w, const Config& config, cudaStream_t stream) {
    V1NvtxRange stage("S1.preprocess");
    if (!valid_pair(w.imageA, w.grayA) || !valid_pair(w.imageB, w.grayB)) return ErrorCode::InvalidImage;

    V1GaussianWeights weights;
    const ErrorCode status = v1_make_gaussian_weights(config.gaussian_sigma, config.gaussian_radius, weights);
    if (status != ErrorCode::Success) return status;

    const std::size_t bytes = std::max(v1_preprocess_scratch_bytes(w.imageA.width, w.imageA.height),
                                       v1_preprocess_scratch_bytes(w.imageB.width, w.imageB.height));
    if (!w.d_scratch || w.scratch_capacity_bytes < bytes ||
        reinterpret_cast<std::uintptr_t>(w.d_scratch) % alignof(float) != 0) {
        return ErrorCode::InvalidArgument;
    }
    float* temp = reinterpret_cast<float*>(w.d_scratch);

    ErrorCode result = ErrorCode::Success;
    {
        V1NvtxRange range("S1.image_a");
        result = preprocess_one(w.imageA, w.grayA, temp, weights, stream);
    }
    if (result != ErrorCode::Success) return result;
    V1NvtxRange range("S1.image_b");
    return preprocess_one(w.imageB, w.grayB, temp, weights, stream);
}

}  // namespace panorama
