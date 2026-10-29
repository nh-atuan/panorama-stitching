// Authors: Thanh Chuong (23120195), Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_VERSIONS_H
#define GROUP16_VERSIONS_H

#include "common/v0_config.h"
#include "v0/v0_pipeline.h"

namespace panorama {

// Versions accepted by --version. V0 is the sequential pipeline in v0_pipeline.cpp;
// V1 currently exposes infrastructure stubs only, with an explicit CLI warning.
// Host-only builds retain V0 support without CUDA headers or a GPU driver.
inline bool is_supported_version(int version) {
#ifdef __CUDACC__
    return version == 0 || version == 1;
#else
    return version == 0;
#endif
}

}  // namespace panorama

#endif  // GROUP16_VERSIONS_H
