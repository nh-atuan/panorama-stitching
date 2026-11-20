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
}  // namespace panorama
#endif
