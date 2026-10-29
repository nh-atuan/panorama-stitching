// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0/v0_preprocess.h"
#include "common/gaussian_blur.h"
#include "common/gaussian_kernel.h"
#include "common/image_layout.h"
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <new>

namespace panorama {
namespace {

bool valid_input(const Image& input) {
    return input.channels == 3 && rows_fit(input.data, input.stride, input.width, input.height, 3, 1);
}

bool valid_output(const GrayImage& output, const Image& input) {
    return valid_gray_image(output) && output.width == input.width &&
           output.height == input.height;
}

// Y = (0.299 R + 0.587 G + 0.114 B) / 255, one independent value per pixel.
void convert_to_gray(const Image& input, GrayImage& gray) {
    for (std::int32_t y = 0; y < input.height; ++y) {
        const std::uint8_t* in = input.data + static_cast<std::size_t>(y) * input.stride;
        float* out = gray_row(gray, y);
        for (std::int32_t x = 0; x < input.width; ++x) {
            const float r = static_cast<float>(in[3 * x]);
            const float g = static_cast<float>(in[3 * x + 1]);
            const float b = static_cast<float>(in[3 * x + 2]);
            out[x] = (0.299f * r + 0.587f * g + 0.114f * b) / 255.0f;
        }
    }
}

}  // namespace

ErrorCode v0_preprocess(const Image& input, GrayImage& output,
                        const Config& config, bool debug_mode) {
    if (!valid_input(input) || !valid_output(output, input)) return ErrorCode::InvalidImage;

    float weights[2 * kMaxGaussianRadius + 1];
    const std::int32_t radius = config.gaussian_radius;
    const ErrorCode kernel_status = make_gaussian_weights(config.gaussian_sigma, radius, weights);
    if (kernel_status != ErrorCode::Success) return kernel_status;

    std::size_t pixels = 0;
    if (!gray_pixel_count(input.width, input.height, pixels)) return ErrorCode::InvalidImage;

    std::unique_ptr<float[]> temp;
    try {
        temp.reset(new float[pixels]);
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    }

    convert_to_gray(input, output);
    gaussian_blur_in_place(output, temp.get(), weights, radius);

    if (debug_mode) {
        std::cerr << "[S1] " << input.width << "x" << input.height << " sigma="
                  << config.gaussian_sigma << " radius=" << radius << " temp_bytes="
                  << pixels * sizeof(float) << '\n';
    }
    return ErrorCode::Success;
}

}  // namespace panorama
