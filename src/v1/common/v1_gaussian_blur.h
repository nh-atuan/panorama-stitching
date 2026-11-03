// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_GAUSSIAN_BLUR_H
#define GROUP16_V1_GAUSSIAN_BLUR_H

#include "common/common.h"
#include "common/gaussian_kernel.h"
#include <cuda_runtime.h>

namespace panorama {

// Weights of one separable Gaussian, index i for offset i - radius (make_gaussian_weights).
// Passed to the kernels by value: kernel parameters live in a constant bank on sm_75, and
// no copy to the Device is needed inside the timed stage.
struct V1GaussianWeights {
    float values[2 * kMaxGaussianRadius + 1];
    std::int32_t radius;
};

// Fills `weights` from sigma and radius on the Host. Returns InvalidConfig like V0.
ErrorCode v1_make_gaussian_weights(float sigma, std::int32_t radius, V1GaussianWeights& weights);

// Separable blur with clamped borders, the same taps and summation order as
// gaussian_blur_in_place (S1 and S3 of V0), so the result matches V0 bit for bit with --fmad=false.
// src, dst: Device float views, strides in bytes, same width and height; dst may equal src.
// temp: Device buffer of width * height floats, packed. Padding of src and dst is not touched.
// Enqueues two kernels on `stream`; returns InvalidImage, InvalidConfig, InvalidArgument for a
// bad call and CudaFailure when a launch fails. Asynchronous errors surface on the stream.
ErrorCode v1_gaussian_blur(const GrayImage& src, const GrayImage& dst, float* temp,
                           const V1GaussianWeights& weights, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V1_GAUSSIAN_BLUR_H
