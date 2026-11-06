// Authors: Le Ha Thanh Chuong (23120195), Tran Huu Kim Thanh (23120166)
// External source: none

#ifndef GROUP16_V1_PIPELINE_H
#define GROUP16_V1_PIPELINE_H

#include "common/common.h"
#include "common/cuda_utils.cuh"
#include "v1/s5/v1_homography.h"
#include <cuda_runtime.h>
#include <cstddef>

namespace panorama {

// Owns every Device allocation of one V1 workspace; the views in `view` borrow them.
// S6 replaces d_canvas during a run, so the destructor frees whatever d_canvas holds.
// Destroy it only after the stream that used it has completed.
struct V1DeviceOwner {
    DeviceWorkspace view;
    V1DeviceOwner() = default;
    V1DeviceOwner(const V1DeviceOwner&) = delete;
    V1DeviceOwner& operator=(const V1DeviceOwner&) = delete;
    ~V1DeviceOwner();
};

// Scratch shared by S1..S5, which run one after another on one stream: the largest
// v1_<stage>_scratch_bytes() over images A and B, rounded up to 16 bytes.
// Returns 0 when a stage rejects the size (non-positive dimension or overflow). S2 alone
// may need no scratch (an image side <= 30), which is not an error.
std::size_t v1_scratch_bytes(const Image& a, const Image& b, std::size_t feature_capacity);

// Outside timing: allocates Device images, gray images, features, counts, H, canvas
// metadata and the shared scratch for config.max_keypoints entries; zeroes the metadata.
// d_canvas stays empty: S6 allocates it from H inside every run. Also raises the Device
// stack limit to the 32 KiB that S5 needs, a global setting S5 leaves to the caller.
// Returns InvalidImage or InvalidConfig before allocating; CUDA errors throw CudaError.
ErrorCode v1_prepare(const Image& left, const Image& right, const Config& config,
                     V1DeviceOwner& owner);

// Optional extras for one run of the six stages.
struct V1StageTrace {
    // kStageCount events each, recorded around every stage on the stream; null when untimed.
    CudaEvent* stage_start = nullptr;
    CudaEvent* stage_stop = nullptr;
    // Untimed warm-up with --debug only: receives the counts right after S2, before S3
    // drops keypoints. Costs one stream wait.
    DeviceCounts* after_s2 = nullptr;
};

// Where a run stopped. on_device means S3, S4 or S5 wrote the error to d_counts->status.
struct V1StageFailure {
    Stage stage = Stage::Preprocess;
    bool on_device = false;
};

// Enqueues S1..S6 on `stream`. The caller resets d_counts before the run, uploads both
// images first and awaits the stream before using the canvas.
// A Host-side or launch error returns that code with failure.stage set. An algorithm error
// in S3-S5 leaves H at zero, so S6 then fails: the run reads d_counts->status (S6 has
// already waited for the stream) and, when it holds an error, returns it with on_device.
ErrorCode v1_run_stages(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream,
                        const V1StageTrace& trace, V1StageFailure& failure);

// Copies d_counts to the Host and waits for `stream`. Call outside the timed window.
DeviceCounts v1_read_counts(const DeviceWorkspace& workspace, cudaStream_t stream);

// Debug values of the last completed run, read back outside timing.
struct V1Diagnostics {
    DeviceCounts counts;
    Homography homography;
    V1HomographyDiagnostics s5;
    Panorama canvas;  // Geometry only; canvas.image.data is a Device pointer.
};

// The S5 report lives in scratch, which S6 does not touch, so after a full run it still
// holds that run's values. Waits for `stream`.
V1Diagnostics v1_collect_diagnostics(const DeviceWorkspace& workspace, cudaStream_t stream);

}  // namespace panorama

#endif  // GROUP16_V1_PIPELINE_H
