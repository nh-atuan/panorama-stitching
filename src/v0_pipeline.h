// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_V0_PIPELINE_H
#define GROUP16_V0_PIPELINE_H

#include "common.h"
#include "v0_homography.h"
#include <cstddef>
#include <vector>

namespace panorama {

// Buffers shared by all stages of one V0 run. Reused across warm-up and timed runs.
// The destructor releases the S6 panorama, so a workspace must not be copied.
struct V0Workspace {
    std::vector<float> gray_storage_a, gray_storage_b;
    GrayImage gray_a, gray_b;
    std::vector<Keypoint> keypoints_a, keypoints_b;
    std::vector<Descriptor> descriptors_a, descriptors_b;
    std::vector<Match> matches;
    Homography homography;
    Panorama panorama;  // new[] buffer owned by this workspace after S6 succeeds
    // Keypoints found by S2, before S3 drops those whose patch leaves the image.
    std::size_t detected_a = 0, detected_b = 0;

    V0Workspace() = default;
    V0Workspace(const V0Workspace&) = delete;
    V0Workspace& operator=(const V0Workspace&) = delete;
    ~V0Workspace();
};

// Outside timing: allocates both gray images (packed rows) and reserves the feature
// vectors for config.max_keypoints entries.
// Errors: InvalidImage (non-positive or overflowing size), InvalidConfig, AllocationFailed.
ErrorCode v0_prepare(const Image& left, const Image& right, const Config& config,
                     V0Workspace& workspace);

// Runs S1..S6 once on images prepared by v0_prepare. Any previous panorama is released
// before the clock starts. When `timing` is non-null it receives the time of every stage
// (S1..S3 include both images) and the end-to-end time of the six stages.
// On failure returns the stage error, sets *failed_stage and leaves the panorama empty.
// Pass `report` only outside timed runs: S5 then fills its diagnostics and inlier mask.
ErrorCode v0_run(const Image& left, const Image& right, const Config& config,
                 V0Workspace& workspace, TimingStats* timing, Stage* failed_stage,
                 HomographyReport* report = nullptr);

// Outside timing: delete[] the S6 panorama, if any, and reset it.
void v0_release_output(V0Workspace& workspace);

// Short names for logs, e.g. "S5 homography".
const char* stage_name(Stage stage);

}  // namespace panorama

#endif  // GROUP16_V0_PIPELINE_H
