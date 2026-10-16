// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "gaussian_blur.h"
#include "image_layout.h"
#include <cstddef>

namespace panorama {
namespace {

std::int32_t clamp_index(std::int32_t i, std::int32_t size) {
    return i < 0 ? 0 : (i >= size ? size - 1 : i);
}

// temp (packed, width floats per row) = horizontal blur of src, clamped at the borders.
void blur_horizontal(const GrayImage& src, float* temp, const float* weights,
                     std::int32_t radius) {
    const std::int32_t width = src.width;
    for (std::int32_t y = 0; y < src.height; ++y) {
        const float* in = gray_row(src, y);
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
        float* out = gray_row(dst, y);
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

void gaussian_blur_in_place(GrayImage& image, float* temp, const float* weights,
                            std::int32_t radius) {
    blur_horizontal(image, temp, weights, radius);
    blur_vertical(temp, image, weights, radius);
}

}  // namespace panorama
