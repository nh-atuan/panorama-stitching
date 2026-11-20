// Authors: Le Ha Thanh Chuong (23120195)
// External source: none
#ifndef GROUP16_V5_PIPELINE_H
#define GROUP16_V5_PIPELINE_H
#include "v5/v5_image_branch.h"
#include "v4/v4_pipeline.h"
#include "common/kernel_timing.cuh"
#include <memory>
#include <ostream>
#include <chrono>

namespace panorama {
enum class V5Schedule { Sequential, DualStream };
struct V5BranchEvents {
    CudaEvent start[4], stop[4], count_ready, done;
    ErrorCode status = ErrorCode::Success;
    Stage failure = Stage::Preprocess;
    double host_wait_ms = 0;
};
struct V5TimingDetail {
    double image_ms[2][4] = {};
    double pre_s4_ms = 0, host_pre_s4_ms = 0, count_wait_ms[2] = {};
};
struct V5DeviceOwner {
    DeviceWorkspace view;  // Borrows input/features, owns downstream buffers.
    V5ImageBranch branch[2];
    std::unique_ptr<PinnedBuffer<std::uint32_t>> candidates[2];
    CudaStream image_stream[2], control;
    V5BranchEvents events[2];
    CudaEvent origin, ready;
    CudaEvent downstream_start[3], downstream_stop[3], d2h_start, d2h_stop;
    double host_pre_s4_ms = 0;
    bool output_ready = false;
    std::chrono::steady_clock::time_point download_completed;
    V5DeviceOwner() = default;
    ~V5DeviceOwner();
    V5DeviceOwner(const V5DeviceOwner&) = delete;
    V5DeviceOwner& operator=(const V5DeviceOwner&) = delete;
    void drain() noexcept;
};
ErrorCode v5_prepare(const Image&, const Image&, const Config&, V5DeviceOwner&);
// Host inputs must be pinned. S6 output stays on device until v5_download completes.
ErrorCode v5_run_stages(const Image&, const Image&, const Config&, V5DeviceOwner&,
                       V5Schedule, KernelTiming&, bool, V1StageFailure&);
ErrorCode v5_download(V5DeviceOwner&, std::uint8_t*, std::size_t, bool,
                      TimingStats&, V5TimingDetail&);
void v5_write_detail(std::ostream&, int, V5Schedule, const V5TimingDetail&);
V4Diagnostics v5_collect_diagnostics(const V5DeviceOwner&);
}  // namespace panorama
#endif
