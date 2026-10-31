// Authors: Thanh Chuong (23120195)
// External source: none

#ifndef GROUP16_COMMON_H
#define GROUP16_COMMON_H

#include <iostream>
#include <string>
#include <vector>
#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace panorama {

struct CliOptions {
    std::string left_image;
    std::string right_image;
    std::string output_image;
    int version = 0;
    int runs = 5;
    bool debug = false;
};

// Non-owning views. Stride is always measured in bytes, including float images.
template <typename T>
struct ImageView {
    T* data = nullptr;
    std::size_t stride = 0;
    std::int32_t width = 0;
    std::int32_t height = 0;
    std::int32_t channels = 0;
};

using Image = ImageView<std::uint8_t>;
using GrayImage = ImageView<float>;

struct Keypoint {
    float x = 0.0f;
    float y = 0.0f;
    float score = 0.0f;
    // Radians in image coordinates; used by rotated BRIEF, ignored by BRIEF.
    float angle = 0.0f;
};

struct alignas(16) Descriptor {
    std::uint32_t data[8] = {};
};

struct Match {
    std::int32_t indexA = -1;
    std::int32_t indexB = -1;
    // Integer Hamming distance: number of different bits, in [0, 256].
    std::uint32_t distance = 0;
};

struct Homography {
    // Row-major; column-vector convention; maps image B into image A.
    // Default is invalid, not an implicit identity transform.
    float data[9] = {};
};

struct Panorama {
    Image image;
    // Integer translation from the image A frame into the canvas frame.
    std::int32_t offset_x = 0;
    std::int32_t offset_y = 0;
};

// Zero algorithm parameters are deliberately unset: validate before execution.
// Concrete values are chosen by stage owners, then shared by every version.
struct Config {
    std::int32_t max_keypoints = 0;
    float gaussian_sigma = 0.0f;
    std::int32_t gaussian_radius = 0;
    float fast_threshold = 0.0f;
    float match_ratio_threshold = 0.0f;
    std::uint32_t match_cross_check = 1;
    std::int32_t ransac_iters = 0;
    float ransac_threshold = 0.0f;
    std::uint32_t seed = 16;
    float homography_epsilon = 0.0f;
    std::uint64_t max_canvas_pixels = 0;
};

enum class Stage : std::uint32_t {
    Preprocess = 0,
    Detect = 1,
    Describe = 2,
    Match = 3,
    Homography = 4,
    WarpBlend = 5
};

constexpr std::size_t kStageCount = 6;

struct TimingStats {
    // Entries follow Stage order. S1-S3 each include both images A and B.
    // V0: CPU stage elapsed; V1: CUDA event spans (CSV S1_V1_ms..S6_V1_ms).
    // A stage span can include copies; do not equate its sum with kernel busy time.
    double stage_ms[kStageCount] = {};
    double total_kernel_ms = 0.0;
    double h2d_ms = 0.0;
    double d2h_ms = 0.0;
    double end_to_end_ms = 0.0;
};

enum class ErrorCode : std::uint32_t {
    Success = 0,
    InvalidArgument = 1,
    UnknownOption = 2,
    UnsupportedVersion = 3,
    InputNotFound = 4,
    ImageReadFailed = 5,
    ImageWriteFailed = 6,
    InvalidImage = 7,
    InvalidConfig = 8,
    InsufficientKeypoints = 9,
    InsufficientMatches = 10,
    DegenerateHomography = 11,
    NumericalFailure = 12,
    InvalidCanvas = 13,
    AllocationFailed = 14,
    CudaFailure = 15
};

// Device-written metadata. Counts are separate from allocated capacities.
struct DeviceCounts {
    std::uint32_t keypointsA = 0, keypointsB = 0;
    std::uint32_t descriptorsA = 0, descriptorsB = 0;
    std::uint32_t matches = 0;
    ErrorCode status = ErrorCode::Success;
};

struct DeviceCanvasInfo {
    std::int32_t width = 0, height = 0;
    std::int32_t offset_x = 0, offset_y = 0;
    std::size_t stride = 0;  // Bytes; RGB interleaved.
    ErrorCode status = ErrorCode::Success;
};

// Borrowed Device pointers, owned exclusively by the Host dispatcher in main.cu.
// Stages never free inputs or put Host pointers in Device views. The S6 Host
// entry point may replace the owner-managed output allocation (d_canvas).
// The workspace itself is Host-side launch metadata; pass individual views to kernels.
struct DeviceWorkspace {
    std::uint8_t* d_imageA = nullptr;
    std::uint8_t* d_imageB = nullptr;
    float* d_grayA = nullptr;
    float* d_grayB = nullptr;
    Keypoint* d_keypointsA = nullptr;
    Keypoint* d_keypointsB = nullptr;
    Descriptor* d_descriptorsA = nullptr;
    Descriptor* d_descriptorsB = nullptr;
    Match* d_matches = nullptr;
    Homography* d_homography = nullptr;
    std::uint8_t* d_canvas = nullptr;
    // Non-owning output alias. Free d_canvas only, never free this a second time.
    std::uint8_t* d_panorama = nullptr;
    DeviceCounts* d_counts = nullptr;
    DeviceCanvasInfo* d_canvas_info = nullptr;
    std::uint8_t* d_scratch = nullptr;

    // Alias views: data points to the matching d_* allocation, not Host pixels.
    Image imageA, imageB;
    GrayImage grayA, grayB;
    Panorama canvas;
    std::size_t keypoint_capacityA = 0, keypoint_capacityB = 0;
    std::size_t descriptor_capacityA = 0, descriptor_capacityB = 0;
    std::size_t match_capacity = 0;
    std::size_t canvas_capacity_bytes = 0, scratch_capacity_bytes = 0;
};

// Host and device exchange plain data, never CliOptions or STL containers.
#define GROUP16_ASSERT_TRANSFER_TYPE(Type) \
    static_assert(std::is_standard_layout<Type>::value, #Type " must have standard layout"); \
    static_assert(std::is_trivially_copyable<Type>::value, #Type " must be trivially copyable")

GROUP16_ASSERT_TRANSFER_TYPE(Image);
GROUP16_ASSERT_TRANSFER_TYPE(GrayImage);
GROUP16_ASSERT_TRANSFER_TYPE(Keypoint);
GROUP16_ASSERT_TRANSFER_TYPE(Descriptor);
GROUP16_ASSERT_TRANSFER_TYPE(Match);
GROUP16_ASSERT_TRANSFER_TYPE(Homography);
GROUP16_ASSERT_TRANSFER_TYPE(Panorama);
GROUP16_ASSERT_TRANSFER_TYPE(Config);
GROUP16_ASSERT_TRANSFER_TYPE(TimingStats);
GROUP16_ASSERT_TRANSFER_TYPE(DeviceCounts);
GROUP16_ASSERT_TRANSFER_TYPE(DeviceCanvasInfo);
GROUP16_ASSERT_TRANSFER_TYPE(DeviceWorkspace);

#undef GROUP16_ASSERT_TRANSFER_TYPE

static_assert(sizeof(float) == 4, "The pipeline requires 32-bit float");
static_assert(sizeof(double) == 8, "TimingStats requires 64-bit double");
static_assert(sizeof(Keypoint) == 16, "Unexpected Keypoint layout");
static_assert(sizeof(Descriptor) == 32, "Descriptor must contain exactly 256 bits");
static_assert(alignof(Descriptor) == 16, "Descriptor must be 16-byte aligned");
static_assert(sizeof(Match) == 12, "Unexpected Match layout");
static_assert(sizeof(Homography) == 36, "Homography must contain nine floats");

}  // namespace panorama

#endif  // GROUP16_COMMON_H
