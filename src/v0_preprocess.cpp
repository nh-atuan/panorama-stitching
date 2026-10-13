// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0_preprocess.h"
#include "gaussian_kernel.h"
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <new>

namespace panorama {
namespace {

// Rows are addressed by byte stride; the first width * bytes_per_pixel bytes of a row hold pixels.
bool rows_fit(const void* data, std::size_t stride, std::int32_t width, std::int32_t height,
              std::size_t bytes_per_pixel, std::size_t alignment) {
    if (data == nullptr || width <= 0 || height <= 0) return false;
    const std::size_t max_size = std::numeric_limits<std::size_t>::max();
    const std::size_t w = static_cast<std::size_t>(width);
    if (w > max_size / bytes_per_pixel) return false;
    const std::size_t row_bytes = w * bytes_per_pixel;
    if (stride < row_bytes || stride % alignment != 0) return false;
    if (stride > max_size / static_cast<std::size_t>(height)) return false;
    return reinterpret_cast<std::uintptr_t>(data) % alignment == 0;
}

bool valid_input(const Image& input) {
    return input.channels == 3 && rows_fit(input.data, input.stride, input.width, input.height, 3, 1);
}

bool valid_output(const GrayImage& output, const Image& input) {
    return output.channels == 1 && output.width == input.width && output.height == input.height &&
           rows_fit(output.data, output.stride, output.width, output.height, sizeof(float),
                    sizeof(float));
}

float* float_row(GrayImage& image, std::int32_t y) {
    unsigned char* base = reinterpret_cast<unsigned char*>(image.data);
    return reinterpret_cast<float*>(base + static_cast<std::size_t>(y) * image.stride);
}

std::int32_t clamp_index(std::int32_t i, std::int32_t size) {
    return i < 0 ? 0 : (i >= size ? size - 1 : i);
}

// Y = (0.299 R + 0.587 G + 0.114 B) / 255, one independent value per pixel.
void convert_to_gray(const Image& input, GrayImage& gray) {
    for (std::int32_t y = 0; y < input.height; ++y) {
        const std::uint8_t* in = input.data + static_cast<std::size_t>(y) * input.stride;
        float* out = float_row(gray, y);
        for (std::int32_t x = 0; x < input.width; ++x) {
            const float r = static_cast<float>(in[3 * x]);
            const float g = static_cast<float>(in[3 * x + 1]);
            const float b = static_cast<float>(in[3 * x + 2]);
            out[x] = (0.299f * r + 0.587f * g + 0.114f * b) / 255.0f;
        }
    }
}

// temp (packed, width floats per row) = horizontal blur of src, clamped at the borders.
void blur_horizontal(GrayImage& src, float* temp, const float* weights, std::int32_t radius) {
    const std::int32_t width = src.width;
    for (std::int32_t y = 0; y < src.height; ++y) {
        const float* in = float_row(src, y);
        float* out = temp + static_cast<std::size_t>(y) * static_cast<std::size_t>(width);
        for (std::int32_t x = 0; x < width; ++x) {
            float sum = 0.0f;
            for (std::int32_t k = -radius; k <= radius; ++k) {
                sum += weights[k + radius] * in[clamp_index(x + k, width)];
            }
            out[x] = sum;
        }
    }
}

// dst = vertical blur of temp. Accumulates row by row so memory is read along rows;
// each pixel still sums its taps from -radius to +radius in the same order.
void blur_vertical(const float* temp, GrayImage& dst, const float* weights, std::int32_t radius) {
    const std::int32_t width = dst.width;
    const std::int32_t height = dst.height;
    for (std::int32_t y = 0; y < height; ++y) {
        float* out = float_row(dst, y);
        for (std::int32_t x = 0; x < width; ++x) out[x] = 0.0f;
        for (std::int32_t k = -radius; k <= radius; ++k) {
            const float* in = temp + static_cast<std::size_t>(clamp_index(y + k, height)) *
                                         static_cast<std::size_t>(width);
            const float w = weights[k + radius];
            for (std::int32_t x = 0; x < width; ++x) out[x] += w * in[x];
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

    const std::size_t width = static_cast<std::size_t>(input.width);
    const std::size_t height = static_cast<std::size_t>(input.height);
    if (width > std::numeric_limits<std::size_t>::max() / height) return ErrorCode::InvalidImage;
    const std::size_t pixels = width * height;
    if (pixels > std::numeric_limits<std::size_t>::max() / sizeof(float)) {
        return ErrorCode::InvalidImage;
    }

    std::unique_ptr<float[]> temp;
    try {
        temp.reset(new float[pixels]);
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    }

    convert_to_gray(input, output);
    blur_horizontal(output, temp.get(), weights, radius);
    blur_vertical(temp.get(), output, weights, radius);

    if (debug_mode) {
        std::cerr << "[S1] " << input.width << "x" << input.height << " sigma="
                  << config.gaussian_sigma << " radius=" << radius << " temp_bytes="
                  << pixels * sizeof(float) << '\n';
    }
    return ErrorCode::Success;
}

}  // namespace panorama
