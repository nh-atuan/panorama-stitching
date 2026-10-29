// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "common/gaussian_kernel.h"
#include <cmath>

namespace panorama {

ErrorCode validate_gaussian_params(float sigma, std::int32_t radius) {
    if (!std::isfinite(sigma) || !(sigma > 0.0f)) return ErrorCode::InvalidConfig;
    if (radius < 1 || radius > kMaxGaussianRadius) return ErrorCode::InvalidConfig;
    // radius >= ceil(2 * sigma) is the same as radius >= 2 * sigma for an integer radius.
    if (static_cast<double>(radius) < 2.0 * static_cast<double>(sigma)) {
        return ErrorCode::InvalidConfig;
    }
    return ErrorCode::Success;
}

ErrorCode make_gaussian_weights(float sigma, std::int32_t radius, float* weights) {
    const ErrorCode status = validate_gaussian_params(sigma, radius);
    if (status != ErrorCode::Success) return status;
    if (weights == nullptr) return ErrorCode::InvalidArgument;

    const std::int32_t taps = 2 * radius + 1;
    double raw[2 * kMaxGaussianRadius + 1];
    const double s = static_cast<double>(sigma);
    double sum = 0.0;
    for (std::int32_t i = 0; i < taps; ++i) {
        const double d = static_cast<double>(i - radius);
        raw[i] = std::exp(-(d * d) / (2.0 * s * s));
        sum += raw[i];
    }
    for (std::int32_t i = 0; i < taps; ++i) {
        weights[i] = static_cast<float>(raw[i] / sum);
    }
    return ErrorCode::Success;
}

}  // namespace panorama
