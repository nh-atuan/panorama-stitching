// Authors: Le Ha Thanh Chuong (23120195)
// External source: NVIDIA CUDA Runtime API (events and memory queries).
#ifndef GROUP16_P10_PRES4_PROBE_CUH
#define GROUP16_P10_PRES4_PROBE_CUH

#include "common/cuda_utils.cuh"
#include "common/common.h"
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
#include "v1/s3/v1_describe.h"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iomanip>

namespace panorama {
namespace pres4 {
using Clock = std::chrono::steady_clock;
enum Slot { UploadA, UploadB, S1A, S1B, S2A, S2B, S3A, S3B, CountA, CountB, Slots };

inline void environment(const Image& a, const Image& b, const Config& config) {
    int device = 0, runtime = 0, driver = 0;
    cudaDeviceProp props;
    std::size_t free = 0, total = 0;
    CUDA_CHECK(cudaGetDevice(&device));
    CUDA_CHECK(cudaGetDeviceProperties(&props, device));
    CUDA_CHECK(cudaRuntimeGetVersion(&runtime));
    CUDA_CHECK(cudaDriverGetVersion(&driver));
    CUDA_CHECK(cudaMemGetInfo(&free, &total));
    const char* path = std::getenv("P10_PROBE_ENV");
    if (!path || !*path) throw std::runtime_error("P10_PROBE_ENV is required");
    std::size_t scratch[2] = {};
    const Image images[] = {a, b};
    for (int i = 0; i < 2; ++i) {
        const Image& image = images[i];
        scratch[i] = std::max(v1_preprocess_scratch_bytes(image.width, image.height),
            std::max(v1_detect_scratch_bytes(image.width, image.height),
                v1_describe_scratch_bytes(image.width, image.height, config.max_keypoints)));
    }
    std::ofstream out(path);
    out << "{\"gpu\":\"" << props.name << "\",\"compute_major\":" << props.major
        << ",\"compute_minor\":" << props.minor << ",\"runtime_version\":" << runtime
        << ",\"driver_api_version\":" << driver << ",\"async_engine_count\":" << props.asyncEngineCount
        << ",\"concurrent_kernels\":" << props.concurrentKernels
        << ",\"before_workspace_free_bytes\":" << free << ",\"total_bytes\":" << total
        << ",\"branch_scratch_A_bytes\":" << scratch[0]
        << ",\"branch_scratch_B_bytes\":" << scratch[1] << "}\n";
    if (!out) throw std::runtime_error("Cannot write probe environment");
}

struct Context {
    bool measured;
    CudaEvent start[Slots], stop[Slots], origin, ready;
    bool seen[Slots] = {};
    Clock::time_point host_origin;
    double host_ready_ms = 0, wait_ms[2] = {};
    int branch = 0;
    std::size_t workspace_free = 0, end_free = 0, total = 0;
    static Context*& active() { static Context* value = nullptr; return value; }
    explicit Context(bool timed) : measured(timed) {
        CUDA_CHECK(cudaMemGetInfo(&workspace_free, &total));
        active() = this;
    }
    ~Context() { active() = nullptr; }
    void begin(cudaStream_t stream) {
        host_origin = Clock::now();
        origin.record(stream);
    }
    void boundary(cudaStream_t stream) {
        ready.record(stream);
        host_ready_ms = std::chrono::duration<double, std::milli>(Clock::now() - host_origin).count();
    }
    void write(const TimingStats& timing, const DeviceWorkspace& w) {
        if (!measured) return;
        ready.synchronize();  // Usually already completed by the final D2H wait.
        CUDA_CHECK(cudaMemGetInfo(&end_free, &total));
        const char* path = std::getenv("P10_PROBE_CSV");
        if (!path || !*path) throw std::runtime_error("P10_PROBE_CSV is required");
        std::ifstream existing(path);
        const bool header = existing.peek() == std::ifstream::traits_type::eof();
        existing.close();
        std::ofstream out(path, std::ios::app);
        out.imbue(std::locale::classic());
        if (header) out << "PreS4_ms,Host_PreS4_Submit_ms,H2D_A_ms,H2D_B_ms,S1_A_ms,S1_B_ms,"
            "S2_A_ms,S2_B_ms,S3_A_ms,S3_B_ms,CountD2H_A_ms,CountD2H_B_ms,"
            "CountWait_A_ms,CountWait_B_ms,WorkspaceFree_bytes,AfterD2HFree_bytes,"
            "TotalVRAM_bytes,Scratch_bytes,Total_ms\n";
        out << std::setprecision(12) << ready.elapsed_since(origin) << ',' << host_ready_ms;
        for (int i = 0; i < Slots; ++i) {
            if (!seen[i]) throw std::runtime_error("Missing required pre-S4 timing endpoint");
            out << ',' << stop[i].elapsed_since(start[i]);
        }
        out << ',' << wait_ms[0] << ',' << wait_ms[1] << ',' << workspace_free << ','
            << end_free << ',' << total << ',' << w.scratch_capacity_bytes << ','
            << timing.end_to_end_ms << '\n';
        if (!out) throw std::runtime_error("Cannot write pre-S4 evidence");
    }
};

class Span {
    Context* ctx_;
    int slot_;
    cudaStream_t stream_;
public:
    Span(int slot, cudaStream_t stream) : ctx_(Context::active()), slot_(slot), stream_(stream) {
        if (ctx_) {
            ctx_->seen[slot_] = true;
            ctx_->start[slot_].record(stream_);
        }
    }
    ~Span() noexcept(false) {
        if (ctx_ && !std::uncaught_exception()) ctx_->stop[slot_].record(stream_);
    }
};

inline cudaError_t wait(cudaStream_t stream) {
    const auto begin = Clock::now();
    const cudaError_t status = cudaStreamSynchronize(stream);
    Context* ctx = Context::active();
    if (ctx) ctx->wait_ms[ctx->branch] +=
        std::chrono::duration<double, std::milli>(Clock::now() - begin).count();
    return status;
}
inline void set_branch(bool image_a) {
    if (Context::active()) Context::active()->branch = image_a ? 0 : 1;
}
inline int count_slot() {
    return Context::active() && Context::active()->branch ? CountB : CountA;
}
inline void before_s4(cudaStream_t stream) {
    if (Context::active()) Context::active()->boundary(stream);
}
}  // namespace pres4
}  // namespace panorama
#endif
