// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: src/v2/s5/v2_homography_sampling.cuh by Nguyen Ho Anh Tuan (23120185)
// Changes: Deterministic SplitMix64 sampling and adaptive budget calculation for V3.

#ifndef GROUP16_V3_HOMOGRAPHY_SAMPLING_CUH
#define GROUP16_V3_HOMOGRAPHY_SAMPLING_CUH

#include "v3/s5/v3_homography_geometry.cuh"

namespace panorama { namespace homography_v3 {

namespace {
__device__ inline std::uint64_t mix64(std::uint64_t value) {
    value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

struct SampleStream {
    std::uint64_t state;
    __device__ std::uint64_t next() {
        state += UINT64_C(0x9e3779b97f4a7c15);
        return mix64(state);
    }
    __device__ std::uint64_t bounded(std::uint64_t count) {
        const std::uint64_t floor = (std::uint64_t(0) - count) % count;
        std::uint64_t value;
        do { value = next(); } while (value < floor);
        return value % count;
    }
};
}  // namespace

__device__ inline bool uniform_sample4(std::uint32_t seed, std::int32_t hypothesis_id,
                                        std::int32_t count, Array<std::int32_t, 4>& sample) {
    sample.fill(-1);
    if (hypothesis_id < 0 || count < 4) return false;
    SampleStream stream = {mix64(static_cast<std::uint64_t>(seed) ^
                                 static_cast<std::uint64_t>(hypothesis_id))};
    for (int slot = 0; slot < 4; ++slot) {
        bool repeated;
        do {
            sample[slot] = static_cast<std::int32_t>(stream.bounded(static_cast<std::uint64_t>(count)));
            repeated = false;
            for (int previous = 0; previous < slot; ++previous)
                if (sample[previous] == sample[slot]) repeated = true;
        } while (repeated);
    }
    return true;
}

__device__ inline std::int32_t adaptive_iteration_budget(std::int32_t inliers, std::int32_t count,
                                                          std::int32_t cap) {
    if (cap <= 0) return 0;
    if (count <= 0 || inliers <= 0 || inliers > count) return cap;
    if (inliers == count) return 1;
    const double ratio = static_cast<double>(inliers) / static_cast<double>(count);
    const double squared = ratio * ratio;
    const double all_inliers = squared * squared;
    const double denominator = log1p(-all_inliers);
    if (!isfinite(denominator) || denominator >= 0.0) return cap;
    const double needed = ceil(log1p(-feature_policy::kConfidence) / denominator);
    if (!isfinite(needed) || needed >= static_cast<double>(cap)) return cap;
    return static_cast<std::int32_t>(max_value(1.0, needed));
}

} }  // namespace panorama::homography_v3

#endif  // GROUP16_V3_HOMOGRAPHY_SAMPLING_CUH

