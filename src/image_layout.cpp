// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "image_layout.h"
#include <limits>

namespace panorama {

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

bool valid_gray_image(const GrayImage& image) {
    return image.channels == 1 &&
           rows_fit(image.data, image.stride, image.width, image.height, sizeof(float),
                    sizeof(float));
}

bool gray_pixel_count(std::int32_t width, std::int32_t height, std::size_t& pixels) {
    if (width <= 0 || height <= 0) return false;
    const std::size_t w = static_cast<std::size_t>(width);
    const std::size_t h = static_cast<std::size_t>(height);
    if (w > std::numeric_limits<std::size_t>::max() / h) return false;
    if (w * h > std::numeric_limits<std::size_t>::max() / sizeof(float)) return false;
    pixels = w * h;
    return true;
}

}  // namespace panorama
