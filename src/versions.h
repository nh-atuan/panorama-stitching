// Authors: Thanh Chuong (23120195), Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_VERSIONS_H
#define GROUP16_VERSIONS_H

#include "common/v0_config.h"
#include "v0/v0_pipeline.h"

namespace panorama {

// Versions accepted by --version. V0 is the sequential pipeline in v0_pipeline.cpp;
// CUDA versions are added here as they become ready.
inline bool is_supported_version(int version) {
    return version == 0;
}

}  // namespace panorama

#endif  // GROUP16_VERSIONS_H
