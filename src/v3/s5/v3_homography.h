// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: src/v2/s5/v2_homography.h by Nguyen Ho Anh Tuan (23120185)
// Changes: V3 homography interface with micro-architectural optimizations and expanded batch scheduling.

#ifndef GROUP16_V3_HOMOGRAPHY_H
#define GROUP16_V3_HOMOGRAPHY_H

#include "common/common.h"
#include <cuda_runtime.h>

namespace panorama {

// Diagnostics in stage scratch; read only after the supplied stream completes.
struct V3HomographyDiagnostics {
    std::int32_t attempts = 0, computed_hypotheses = 0, valid_hypotheses = 0, rejected_samples = 0;
    std::int32_t best_hypothesis = -1, adaptive_budget = 0, best_inliers = 0, final_inliers = 0;
    std::int32_t first_refit_inliers = 0, refit_passes = 0;
    std::uint64_t sample_hash = UINT64_C(14695981039346656037);
    double best_loss = 0.0, first_refit_loss = 0.0, refit_loss = 0.0, final_loss = 0.0;
};

std::size_t v3_homography_scratch_bytes(std::size_t match_capacity, int batch_size = 128);
ErrorCode v3_homography(DeviceWorkspace&, const Config&, cudaStream_t);
ErrorCode v3_homography_with_batch_size(DeviceWorkspace&, const Config&, cudaStream_t, int batch_size);

// Borrowed pointers do not own storage and become invalid when scratch is reused.
const V3HomographyDiagnostics* v3_homography_diagnostics(const DeviceWorkspace&);
const std::uint8_t* v3_homography_inlier_mask(const DeviceWorkspace&, int batch_size = 128);

}  // namespace panorama

#endif  // GROUP16_V3_HOMOGRAPHY_H

