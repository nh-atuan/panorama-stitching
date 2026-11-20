// Authors: Le Ha Thanh Chuong (23120195)
// External source: none
#include "v5/v5_pipeline.h"

#ifdef PANORAMA_V5_IMAGE_API_AVAILABLE
#include "v1/s4/v1_match.h"
#include "v3/s5/v3_homography.h"
#include "v4/s6/v4_warp_blend.h"
#include <algorithm>
#include <chrono>
#include <limits>
#include <thread>

namespace panorama {
void V5DeviceOwner::drain() noexcept {
    for (int i = 0; i < 2; ++i)
        cuda_cleanup_warning(cudaStreamSynchronize(image_stream[i].get()), "V5 branch drain");
    cuda_cleanup_warning(cudaStreamSynchronize(control.get()), "V5 control drain");
}

V5DeviceOwner::~V5DeviceOwner() {
    drain();
    for (int i = 0; i < 2; ++i) {
        V5ImageBranch& b = branch[i];
        device_free(b.image.data);
        device_free(b.gray.data);
        device_free(b.keypoints);
        device_free(b.descriptors);
        device_free(b.counts);
        device_free(b.scratch);
    }
    device_free(view.d_scratch);
    device_free(view.d_counts);
    device_free(view.d_matches);
    device_free(view.d_homography);
    device_free(view.d_canvas_info);
    device_free(view.d_canvas);
}

ErrorCode v5_prepare(const Image& a, const Image& b, const Config& config, V5DeviceOwner& owner) {
    if (owner.branch[0].image.data || owner.branch[1].image.data || owner.view.d_counts)
        return ErrorCode::InvalidArgument;
    if (config.max_keypoints <= 0) return ErrorCode::InvalidConfig;
    const Image inputs[] = {a, b};
    std::size_t sizes[2] = {};
    for (int i = 0; i < 2; ++i) {
        const Image& input = inputs[i];
        if (!input.data || input.width <= 0 || input.height <= 0 || input.channels != 3 ||
            input.stride < static_cast<std::size_t>(input.width) * 3 ||
            static_cast<std::size_t>(input.height) > std::numeric_limits<std::size_t>::max() / input.stride)
            return ErrorCode::InvalidImage;
        const ErrorCode checked = v5_image_scratch_bytes(input, config, sizes[i]);
        if (checked != ErrorCode::Success) return checked;
    }
    try {
        std::size_t stack = 0;
        CUDA_CHECK(cudaDeviceGetLimit(&stack, cudaLimitStackSize));
        if (stack < 32768) CUDA_CHECK(cudaDeviceSetLimit(cudaLimitStackSize, 32768));
        for (int i = 0; i < 2; ++i) {
            V5ImageBranch& branch = owner.branch[i];
            const Image& input = inputs[i];
            branch.image = input;
            branch.image.data = nullptr;
            device_allocate(branch.image.data, input.stride * input.height);
            branch.gray.width = input.width;
            branch.gray.height = input.height;
            branch.gray.channels = 1;
            branch.gray.stride = static_cast<std::size_t>(input.width) * sizeof(float);
            device_allocate(branch.gray.data, static_cast<std::size_t>(input.width) * input.height);
            branch.feature_capacity = static_cast<std::size_t>(config.max_keypoints);
            device_allocate(branch.keypoints, branch.feature_capacity);
            device_allocate(branch.descriptors, branch.feature_capacity);
            device_allocate(branch.counts, 1);
            branch.scratch_bytes = sizes[i];
            device_allocate(branch.scratch, sizes[i]);
            owner.candidates[i].reset(new PinnedBuffer<std::uint32_t>(1));
            branch.host_candidates = owner.candidates[i]->get();
        }
        DeviceWorkspace& w = owner.view;
        w.imageA = owner.branch[0].image; w.imageB = owner.branch[1].image;
        w.grayA = owner.branch[0].gray; w.grayB = owner.branch[1].gray;
        w.d_imageA = w.imageA.data; w.d_imageB = w.imageB.data;
        w.d_grayA = w.grayA.data; w.d_grayB = w.grayB.data;
        w.d_keypointsA = owner.branch[0].keypoints; w.d_keypointsB = owner.branch[1].keypoints;
        w.d_descriptorsA = owner.branch[0].descriptors; w.d_descriptorsB = owner.branch[1].descriptors;
        w.keypoint_capacityA = w.keypoint_capacityB = w.descriptor_capacityA =
            w.descriptor_capacityB = w.match_capacity = config.max_keypoints;
        device_allocate(w.d_counts, 1);
        device_allocate(w.d_matches, w.match_capacity);
        device_allocate(w.d_homography, 1);
        device_allocate(w.d_canvas_info, 1);
        w.scratch_capacity_bytes = std::max(v1_match_scratch_bytes(w.match_capacity),
                                           v3_homography_scratch_bytes(w.match_capacity));
        if (!w.scratch_capacity_bytes) return ErrorCode::InvalidConfig;
        device_allocate(w.d_scratch, w.scratch_capacity_bytes);
        return v5_initialize_features(config, owner.control.get());
    } catch (const CudaError& error) {
        owner.drain();
        return error.status == cudaErrorMemoryAllocation ? ErrorCode::AllocationFailed : ErrorCode::CudaFailure;
    }
}
namespace {
using Clock = std::chrono::steady_clock;

ErrorCode remember(ErrorCode code, Stage stage, V5BranchEvents& event) {
    if (code != ErrorCode::Success && event.status == ErrorCode::Success) {
        event.status = code;
        event.failure = stage;
    }
    return code;
}

void enqueue_prefix(const Image& host, const Config& config, V5DeviceOwner& owner, int index) {
    V5ImageBranch& branch = owner.branch[index];
    V5BranchEvents& event = owner.events[index];
    cudaStream_t stream = owner.image_stream[index].get();
    event.status = ErrorCode::Success;
    event.failure = Stage::Preprocess;
    event.host_wait_ms = 0;
    owner.origin.wait_on(stream);
    *branch.host_candidates = 0;
    if (remember(v5_reset_image(branch, stream), Stage::Preprocess, event) == ErrorCode::Success) {
        event.start[0].record(stream);
        remember(v5_upload_image(host, branch, stream), Stage::Preprocess, event);
        event.stop[0].record(stream);
    }
    if (event.status == ErrorCode::Success) {
        event.start[1].record(stream);
        remember(v5_preprocess_image(branch, config, stream), Stage::Preprocess, event);
        event.stop[1].record(stream);
    }
    if (event.status == ErrorCode::Success) {
        event.start[2].record(stream);
        remember(v5_detect_candidates(branch, config, stream), Stage::Detect, event);
    }
    event.count_ready.record(stream);
}

void enqueue_suffix(const Config& config, V5DeviceOwner& owner, int index) {
    V5BranchEvents& event = owner.events[index];
    V5ImageBranch& branch = owner.branch[index];
    cudaStream_t stream = owner.image_stream[index].get();
    if (event.status == ErrorCode::Success) {
        remember(v5_finish_detect(branch, config, stream), Stage::Detect, event);
        event.stop[2].record(stream);
    }
    if (event.status == ErrorCode::Success) {
        event.start[3].record(stream);
        remember(v5_describe_image(branch, config, stream), Stage::Describe, event);
        event.stop[3].record(stream);
    }
    event.done.record(stream);
}

void schedule_dual(const Image& a, const Image& b, const Config& config, V5DeviceOwner& owner) {
    enqueue_prefix(a, config, owner, 0);
    enqueue_prefix(b, config, owner, 1);
    bool complete[2] = {};
    const Clock::time_point waiting = Clock::now();
    while (!complete[0] || !complete[1]) {
        for (int i = 0; i < 2; ++i) {
            if (!complete[i] && owner.events[i].count_ready.ready()) {
                owner.events[i].host_wait_ms =
                    std::chrono::duration<double, std::milli>(Clock::now() - waiting).count();
                enqueue_suffix(config, owner, i);
                complete[i] = true;
            }
        }
        if (!complete[0] || !complete[1]) std::this_thread::yield();
    }
}

void schedule_sequential(const Image& a, const Image& b, const Config& config, V5DeviceOwner& owner) {
    const Image inputs[] = {a, b};
    for (int i = 0; i < 2; ++i) {
        if (i) owner.events[0].done.wait_on(owner.image_stream[1].get());
        enqueue_prefix(inputs[i], config, owner, i);
        const Clock::time_point begin = Clock::now();
        owner.events[i].count_ready.synchronize();
        owner.events[i].host_wait_ms =
            std::chrono::duration<double, std::milli>(Clock::now() - begin).count();
        enqueue_suffix(config, owner, i);
    }
}

__global__ void merge_counts(DeviceCounts* out, const DeviceCounts* a, const DeviceCounts* b,
                              ErrorCode host_a, Stage stage_a, ErrorCode host_b, Stage stage_b) {
    if (threadIdx.x || blockIdx.x) return;
    out->keypointsA = a->keypointsA; out->keypointsB = b->keypointsA;
    out->descriptorsA = a->descriptorsA; out->descriptorsB = b->descriptorsA;
    out->matches = 0;
    const ErrorCode status_a = host_a == ErrorCode::Success ? a->status : host_a;
    const ErrorCode status_b = host_b == ErrorCode::Success ? b->status : host_b;
    const Stage rank_a = host_a == ErrorCode::Success ? Stage::Describe : stage_a;
    const Stage rank_b = host_b == ErrorCode::Success ? Stage::Describe : stage_b;
    out->status = status_a;
    if (status_a == ErrorCode::Success ||
        (status_b != ErrorCode::Success && static_cast<unsigned>(rank_b) < static_cast<unsigned>(rank_a)))
        out->status = status_b;
}
}  // namespace

ErrorCode v5_run_stages(const Image& a, const Image& b, const Config& config,
                       V5DeviceOwner& owner, V5Schedule schedule, KernelTiming& kernels,
                       bool measured, V1StageFailure& failure) {
    (void)measured;
    failure = V1StageFailure();
    owner.output_ready = false;
    if (!owner.view.d_counts || !owner.view.d_scratch) return ErrorCode::InvalidArgument;
    const Clock::time_point host_start = Clock::now();
    try {
        kernels.reset();
        KernelTimingScope timing_scope(kernels);
        const cudaStream_t control = owner.control.get();
        CUDA_CHECK(cudaMemsetAsync(owner.view.d_counts, 0, sizeof(DeviceCounts), control));
        CUDA_CHECK(cudaMemsetAsync(owner.view.d_homography, 0, sizeof(Homography), control));
        owner.origin.record(control);
        if (schedule == V5Schedule::Sequential) schedule_sequential(a, b, config, owner);
        else schedule_dual(a, b, config, owner);
        for (int i = 0; i < 2; ++i) {
            if (owner.events[i].status == ErrorCode::CudaFailure) {
                owner.drain();
                return ErrorCode::CudaFailure;
            }
            owner.events[i].done.wait_on(control);
        }
        PANORAMA_LAUNCH_KERNEL(control, merge_counts<<<1, 1, 0, control>>>(
            owner.view.d_counts, owner.branch[0].counts, owner.branch[1].counts,
            owner.events[0].status, owner.events[0].failure,
            owner.events[1].status, owner.events[1].failure));
        CUDA_CHECK(cudaGetLastError());
        owner.ready.record(control);
        owner.host_pre_s4_ms = std::chrono::duration<double, std::milli>(Clock::now() - host_start).count();
        const GpuStage downstream[] = {v1_match, v3_homography, v4_warp_blend};
        for (int i = 0; i < 3; ++i) {
            failure.stage = static_cast<Stage>(i + 3);
            owner.downstream_start[i].record(control);
            const ErrorCode code = downstream[i](owner.view, config, control);
            if (code != ErrorCode::Success) {
                const DeviceCounts counts = v1_read_counts(owner.view, control);
                if (counts.status != ErrorCode::Success) {
                    failure.on_device = true;
                    return counts.status;
                }
                return code;
            }
            CUDA_CHECK(cudaGetLastError());
            owner.downstream_stop[i].record(control);
        }
        owner.output_ready = true;
        return ErrorCode::Success;
    } catch (const CudaError&) {
        owner.drain();
        return ErrorCode::CudaFailure;
    }
}
}  // namespace panorama
#endif
