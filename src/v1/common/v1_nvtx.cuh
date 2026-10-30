// Authors: Le Thuong De (23120232)
// Adapted from: NVIDIA NVTX API descriptions, https://nvidia.github.io/NVTX/,
// accessed 2026-10-31. No external implementation copied.
// Changes: a scoped push/pop wrapper for the team's stage launch ranges.
#ifndef GROUP16_V1_NVTX_CUH
#define GROUP16_V1_NVTX_CUH
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <nvtx3/nvToolsExt.h>
namespace panorama {
class V1NvtxRange {
public:
    explicit V1NvtxRange(const char* name){nvtxRangePushA(name);}
    ~V1NvtxRange(){nvtxRangePop();}
    V1NvtxRange(const V1NvtxRange&)=delete;
    V1NvtxRange& operator=(const V1NvtxRange&)=delete;
};
}
#endif
