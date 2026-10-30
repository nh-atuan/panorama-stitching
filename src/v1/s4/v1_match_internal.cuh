// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_V1_MATCH_INTERNAL_CUH
#define GROUP16_V1_MATCH_INTERNAL_CUH

#include "common/common.h"
#include <cuda_runtime.h>

namespace panorama {
namespace match_gpu {
struct Neighbor { std::uint32_t distance; std::int32_t index; };
struct TopTwo { Neighbor best, second; };

__device__ inline void insert(Neighbor value, TopTwo& pair) {
    if (value.index < 0 || value.index == pair.best.index || value.index == pair.second.index) return;
    const bool first = value.distance < pair.best.distance ||
        (value.distance == pair.best.distance && value.index < pair.best.index);
    if (first) { pair.second = pair.best; pair.best = value; }
    else if (value.distance < pair.second.distance ||
             (value.distance == pair.second.distance && value.index < pair.second.index)) pair.second = value;
}
}  // namespace match_gpu
}  // namespace panorama
#endif
