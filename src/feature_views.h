// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_FEATURE_VIEWS_H
#define GROUP16_FEATURE_VIEWS_H

#include "common.h"
#include <limits>

namespace panorama {

// Borrowed host storage. Capacity is the actual allocation in elements.
// A caller must not declare a capacity larger than the allocation.
template <typename T>
struct FeatureView {
    const T* data;
    std::int32_t count;
    std::size_t capacity;

    FeatureView(const T* pointer = nullptr, std::int32_t size = 0,
                std::size_t allocation = 0)
        : data(pointer), count(size), capacity(allocation) {}
};

template <typename T>
bool valid_feature_view(const FeatureView<T>& view) {
    if (view.count < 0 || static_cast<std::size_t>(view.count) > view.capacity ||
        view.capacity > std::numeric_limits<std::size_t>::max() / sizeof(T))
        return false;
    if (view.count == 0) return true;
    return view.data != nullptr &&
           reinterpret_cast<std::uintptr_t>(view.data) % alignof(T) == 0;
}

}  // namespace panorama

#endif
