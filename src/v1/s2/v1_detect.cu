// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

#include "common/kernel_timing.cuh"
#include "v1/s2/v1_detect.h"
#include "common/feature_border.h"
#include "common/image_layout.h"
#include "v0/v0_detect.h"
#include "v1/common/v1_nvtx.cuh"
#include "v1/s2/v1_fast_score.cuh"
#include "v1/s2/v1_nms.cuh"
#include "v1/s2/v1_topk_sort.cuh"
#include <algorithm>
#include <cmath>
#include <limits>

namespace panorama {
namespace {

constexpr unsigned kBlockX = 32;
constexpr unsigned kBlockY = 8;
constexpr std::size_t kScratchAlignment = 16;

// Offsets of one image's buffers inside d_scratch. total == 0: no candidate region.
struct DetectLayout {
    std::size_t pixels = 0;
    std::uint32_t capacity = 0;
    std::size_t scores_offset = kScratchAlignment;  // Counter in the first 16 bytes.
    std::size_t keys_offset = 0;
    std::size_t total = 0;
};

bool has_region(std::int32_t width, std::int32_t height) {
    return width > 2 * kFeatureBorder && height > 2 * kFeatureBorder;
}

// False when a dimension is not positive or W*H does not fit the 32-bit raster of a key.
bool make_layout(std::int32_t width, std::int32_t height, DetectLayout& layout) {
    layout = DetectLayout();
    if (!gray_pixel_count(width, height, layout.pixels)) return false;
    if (layout.pixels > std::numeric_limits<std::uint32_t>::max()) return false;
    if (!has_region(width, height)) return true;
    const std::size_t half_w = (static_cast<std::size_t>(width) + 1) / 2;
    const std::size_t half_h = (static_cast<std::size_t>(height) + 1) / 2;
    layout.capacity = static_cast<std::uint32_t>(half_w * half_h);
    const std::size_t slots = v1_s2::next_power_of_two(layout.capacity);
    const std::size_t scores_end = layout.scores_offset + layout.pixels * sizeof(float);
    layout.keys_offset = (scores_end + kScratchAlignment - 1) / kScratchAlignment * kScratchAlignment;
    layout.total = layout.keys_offset + slots * sizeof(unsigned long long);
    return true;
}

bool valid_config(const Config& config) {
    const float t = config.fast_threshold;
    return std::isfinite(t) && t > 0.0f && t < 1.0f && config.max_keypoints >= 1 &&
           config.max_keypoints <= kMaxKeypointsLimit;
}

bool valid_gray(const GrayImage& gray) {
    std::size_t pixels = 0;
    return valid_gray_image(gray) && gray_pixel_count(gray.width, gray.height, pixels);
}

__global__ void publish_count_kernel(std::uint32_t* field, std::uint32_t value) { *field = value; }

dim3 region_grid(const GrayImage& gray) {
    const unsigned w = static_cast<unsigned>(gray.width - 2 * kFeatureBorder);
    const unsigned h = static_cast<unsigned>(gray.height - 2 * kFeatureBorder);
    return dim3((w + kBlockX - 1) / kBlockX, (h + kBlockY - 1) / kBlockY);
}

ErrorCode detect_one(const GrayImage& gray, Keypoint* keypoints, std::uint32_t* count_field,
                     const Config& config, std::uint8_t* scratch, cudaStream_t stream) {
    DetectLayout layout;
    make_layout(gray.width, gray.height, layout);
    std::uint32_t kept = 0;
    if (layout.total != 0) {
        std::uint32_t* d_count = reinterpret_cast<std::uint32_t*>(scratch);
        float* scores = reinterpret_cast<float*>(scratch + layout.scores_offset);
        unsigned long long* keys = reinterpret_cast<unsigned long long*>(scratch + layout.keys_offset);
        const unsigned char* pixels = reinterpret_cast<const unsigned char*>(gray.data);
        const dim3 block(kBlockX, kBlockY), grid = region_grid(gray);
        std::uint32_t candidates = 0;
        {
            V1NvtxRange range("S2.score_nms");
            if (cudaMemsetAsync(d_count, 0, sizeof(std::uint32_t), stream) != cudaSuccess ||
                cudaMemsetAsync(scores, 0, layout.pixels * sizeof(float), stream) != cudaSuccess) {
                return ErrorCode::CudaFailure;
            }
            PANORAMA_LAUNCH_KERNEL(stream, v1_s2::fast_score_kernel<<<grid, block, 0, stream>>>(pixels, gray.stride, gray.width, gray.height,
                                                                config.fast_threshold, scores));
            PANORAMA_LAUNCH_KERNEL(stream, v1_s2::nms_kernel<<<grid, block, 0, stream>>>(scores, gray.width, gray.height, d_count, keys,
                                                         layout.capacity));
            if (cudaPeekAtLastError() != cudaSuccess ||
                cudaMemcpyAsync(&candidates, d_count, sizeof(candidates), cudaMemcpyDeviceToHost, stream) !=
                    cudaSuccess ||
                cudaStreamSynchronize(stream) != cudaSuccess) {
                return ErrorCode::CudaFailure;
            }
        }
        candidates = std::min(candidates, layout.capacity);
        kept = std::min(candidates, static_cast<std::uint32_t>(config.max_keypoints));
        V1NvtxRange range("S2.top_n");
        if (v1_s2::sort_keys(keys, candidates, stream) != cudaSuccess) return ErrorCode::CudaFailure;
        if (kept > 0) {
            PANORAMA_LAUNCH_KERNEL(stream, v1_s2::write_keypoints_kernel<<<v1_s2::blocks_for(kept), v1_s2::kSortThreads, 0, stream>>>(
                keys, kept, static_cast<std::uint32_t>(gray.width), keypoints));
        }
    }
    PANORAMA_LAUNCH_KERNEL(stream, publish_count_kernel<<<1, 1, 0, stream>>>(count_field, kept));
    return cudaPeekAtLastError() == cudaSuccess ? ErrorCode::Success : ErrorCode::CudaFailure;
}

}  // namespace

std::size_t v1_detect_scratch_bytes(std::int32_t width, std::int32_t height) {
    DetectLayout layout;
    return make_layout(width, height, layout) ? layout.total : 0;
}

ErrorCode v1_detect(DeviceWorkspace& w, const Config& config, cudaStream_t stream) {
    V1NvtxRange stage("S2.detect");
    if (!valid_gray(w.grayA) || !valid_gray(w.grayB)) return ErrorCode::InvalidImage;
    if (!valid_config(config)) return ErrorCode::InvalidConfig;

    DetectLayout a, b;
    const std::size_t limit = static_cast<std::size_t>(config.max_keypoints);
    if (!w.d_counts || !w.d_keypointsA || !w.d_keypointsB || w.keypoint_capacityA < limit ||
        w.keypoint_capacityB < limit || !make_layout(w.grayA.width, w.grayA.height, a) ||
        !make_layout(w.grayB.width, w.grayB.height, b)) {
        return ErrorCode::InvalidArgument;
    }
    const std::size_t bytes = std::max(a.total, b.total);
    if (bytes && (!w.d_scratch || w.scratch_capacity_bytes < bytes ||
                  reinterpret_cast<std::uintptr_t>(w.d_scratch) % kScratchAlignment != 0)) {
        return ErrorCode::InvalidArgument;
    }

    ErrorCode result = ErrorCode::Success;
    {
        V1NvtxRange range("S2.image_a");
        result = detect_one(w.grayA, w.d_keypointsA, &w.d_counts->keypointsA, config, w.d_scratch, stream);
    }
    if (result != ErrorCode::Success) return result;
    V1NvtxRange range("S2.image_b");
    return detect_one(w.grayB, w.d_keypointsB, &w.d_counts->keypointsB, config, w.d_scratch, stream);
}

}  // namespace panorama
