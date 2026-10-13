// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_ORDERED_REDUCTION_H
#define GROUP16_ORDERED_REDUCTION_H

#include <cstddef>

namespace panorama {
namespace homography_detail {

// Fixed binary tree with leaves in input order and zero padding.
template <typename Getter>
double sum_subtree(const Getter& get, std::size_t count,
                   std::size_t first, std::size_t width) {
    if (first >= count) return 0.0;
    if (width == 1) return get(first);
    const std::size_t half = width / 2;
    const double left = sum_subtree(get, count, first, half);
    const double right = sum_subtree(get, count, first + half, half);
    return left + right;
}

template <typename Getter>
double ordered_sum(std::size_t count, const Getter& get) {
    if (count == 0) return 0.0;
    // Feature counts are int32; DLT uses at most twice that count.
    std::size_t width = 1;
    while (width < count) width *= 2;
    return sum_subtree(get, count, 0, width);
}

}  // namespace homography_detail
}  // namespace panorama

#endif
