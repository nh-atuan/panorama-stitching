// Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_FEATURE_SUPPORT_H
#define GROUP16_FEATURE_SUPPORT_H

#include "common/common.h"
#include <limits>

namespace panorama {
namespace feature_policy {

constexpr float kRatio = 0.80f;
constexpr std::int32_t kMaxIterations = 2000;
constexpr std::uint32_t kSeed = 16u;
constexpr double kConfidence = 0.99;
constexpr double kReferenceThreshold = 3.0;
constexpr double kDuplicateEpsilon = 1e-6;
constexpr double kAreaEpsilon = 1e-4;
constexpr double kRankEpsilon = 1e-10;

}  // namespace feature_policy

// Set only S4/S5 fields; preserve parameters owned by the other stages.
// A zero shared H epsilon receives the documented working value 1e-6f.
// Failure leaves config unchanged.
ErrorCode configure_v0_features(Config& config, std::int32_t width_a,
                                std::int32_t height_a);

}  // namespace panorama

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
