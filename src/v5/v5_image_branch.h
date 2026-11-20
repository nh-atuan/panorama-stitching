// Authors: Le Ha Thanh Chuong (23120195)
// External source: none
#ifndef GROUP16_V5_IMAGE_BRANCH_H
#define GROUP16_V5_IMAGE_BRANCH_H
#include "common/common.h"
#include <cuda_runtime.h>

namespace panorama {
// Declaration-only T01 contract. P10-T02 supplies these function definitions.
struct V5ImageBranch {
    Image image;
    GrayImage gray;
    Keypoint* keypoints = nullptr;
    Descriptor* descriptors = nullptr;
    DeviceCounts* counts = nullptr;
    std::uint8_t* scratch = nullptr;
    std::size_t scratch_bytes = 0;
    std::size_t feature_capacity = 0;
    std::uint32_t* host_candidates = nullptr;
};
ErrorCode v5_image_scratch_bytes(const Image&, const Config&, std::size_t&);
ErrorCode v5_initialize_features(const Config&, cudaStream_t);
ErrorCode v5_reset_image(V5ImageBranch&, cudaStream_t);
ErrorCode v5_upload_image(const Image&, V5ImageBranch&, cudaStream_t);
ErrorCode v5_preprocess_image(V5ImageBranch&, const Config&, cudaStream_t);
ErrorCode v5_detect_candidates(V5ImageBranch&, const Config&, cudaStream_t);
ErrorCode v5_finish_detect(V5ImageBranch&, const Config&, cudaStream_t);
ErrorCode v5_describe_image(V5ImageBranch&, const Config&, cudaStream_t);
}  // namespace panorama
#endif
