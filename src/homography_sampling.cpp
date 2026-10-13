// Authors: Le Thuong De (23120232)
// Adapted from: Sebastiano Vigna's public-domain SplitMix64 reference,
// https://prng.di.unimi.it/splitmix64.c, accessed 2026-10-13;
// standard RANSAC termination described in OpenCV USAC documentation,
// https://docs.opencv.org/4.13.0/de/d3e/tutorial_usac.html, accessed 2026-10-13.
// Changes: per-hypothesis stream initialization, rejection-bounded sampling,
// unique draw order, guarded confidence budget and no external RNG dependency.

#include "homography_sampling.h"
#include "feature_config.h"
#include <algorithm>
#include <cmath>

namespace panorama {
namespace homography_detail {
namespace {
std::uint64_t mix64(std::uint64_t value) {
    value = (value ^ (value >> 30))*UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27))*UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

struct SampleStream {
    std::uint64_t state;
    std::uint64_t next() {
        state += UINT64_C(0x9e3779b97f4a7c15);
        return mix64(state);
    }
    std::uint64_t bounded(std::uint64_t count) {
        const std::uint64_t floor = (std::uint64_t(0)-count)%count;
        std::uint64_t value;
        do { value=next(); } while(value<floor);
        return value%count;
    }
};
}  // namespace

bool uniform_sample4(std::uint32_t seed, std::int32_t hypothesis_id,
                      std::int32_t count, std::array<std::int32_t,4>& sample) {
    sample.fill(-1);
    if (hypothesis_id<0 || count<4) return false;
    SampleStream stream={mix64(static_cast<std::uint64_t>(seed) ^
                              static_cast<std::uint64_t>(hypothesis_id))};
    for(int slot=0;slot<4;++slot) {
        bool repeated;
        do {
            sample[slot]=static_cast<std::int32_t>(stream.bounded(static_cast<std::uint64_t>(count)));
            repeated=false;
            for(int previous=0;previous<slot;++previous)
                if(sample[previous]==sample[slot]) repeated=true;
        } while(repeated);
    }
    return true;
}

std::int32_t adaptive_iteration_budget(std::int32_t inliers, std::int32_t count,
                                       std::int32_t cap) {
    if(cap<=0) return 0;
    if(count<=0 || inliers<=0 || inliers>count) return cap;
    if(inliers==count) return 1;
    const double ratio=static_cast<double>(inliers)/static_cast<double>(count);
    const double squared=ratio*ratio;
    const double all_inliers=squared*squared;
    const double denominator=std::log1p(-all_inliers);
    if(!std::isfinite(denominator) || denominator>=0.0) return cap;
    const double needed=std::ceil(std::log1p(-feature_policy::kConfidence)/denominator);
    if(!std::isfinite(needed) || needed>=static_cast<double>(cap)) return cap;
    return static_cast<std::int32_t>(std::max(1.0,needed));
}

}  // namespace homography_detail
}  // namespace panorama
