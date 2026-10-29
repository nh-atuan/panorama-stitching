// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_IMAGE_LAYOUT_H
#define GROUP16_IMAGE_LAYOUT_H

#include "common/common.h"
#include <cstddef>
#include <cstdint>

namespace panorama {

// Rows are addressed by byte stride; the first width * bytes_per_pixel bytes of a row hold pixels.
// True when data is non-null and aligned, sizes are positive, the stride holds one row, is a
// multiple of `alignment`, and stride * height does not overflow.
bool rows_fit(const void* data, std::size_t stride, std::int32_t width, std::int32_t height,
              std::size_t bytes_per_pixel, std::size_t alignment);

// One-channel float image with a valid byte stride (docs/interface.md, section 2).
bool valid_gray_image(const GrayImage& image);

// width * height pixels, rejecting products that overflow size_t or a float allocation.
bool gray_pixel_count(std::int32_t width, std::int32_t height, std::size_t& pixels);

inline float* gray_row(GrayImage& image, std::int32_t y) {
    unsigned char* base = reinterpret_cast<unsigned char*>(image.data);
    return reinterpret_cast<float*>(base + static_cast<std::size_t>(y) * image.stride);
}

inline const float* gray_row(const GrayImage& image, std::int32_t y) {
    const unsigned char* base = reinterpret_cast<const unsigned char*>(image.data);
    return reinterpret_cast<const float*>(base + static_cast<std::size_t>(y) * image.stride);
}

}  // namespace panorama

#endif  // GROUP16_IMAGE_LAYOUT_H
