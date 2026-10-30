// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_V1_MATCH_H
#define GROUP16_V1_MATCH_H

#include "common/common.h"
#include <cuda_runtime.h>

namespace panorama {

// Scratch is borrowed, aligned to 16 bytes, and reusable after stream completion.
// Algorithm status/counts are published on Device; return value covers Host/launch errors.
std::size_t v1_match_scratch_bytes(std::size_t descriptor_capacity_a);
ErrorCode v1_match(DeviceWorkspace&, const Config&, cudaStream_t);
ErrorCode v1_match_with_block_size(DeviceWorkspace&, const Config&, cudaStream_t, int threads);

}  // namespace panorama
#endif
