// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0/v0_describe.h"
#include "common/brief_pattern.h"
#include "common/gaussian_blur.h"
#include "common/gaussian_kernel.h"
#include "common/image_layout.h"
#include <cmath>
#include <cstddef>
#include <iostream>
#include <limits>
#include <memory>
#include <new>

namespace panorama {
namespace {

bool valid_keypoints(const std::vector<Keypoint>& keypoints) {
    if (keypoints.size() > static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max())) {
        return false;
    }
    for (std::size_t i = 0; i < keypoints.size(); ++i) {
        if (!std::isfinite(keypoints[i].x) || !std::isfinite(keypoints[i].y)) return false;
    }
    return true;
}

// Packed copy of `image` (width floats per row) smoothed for the binary tests.
void smooth_copy(const GrayImage& image, const float* weights, float* smoothed, float* temp) {
    const std::size_t width = static_cast<std::size_t>(image.width);
    for (std::int32_t y = 0; y < image.height; ++y) {
        const float* in = gray_row(image, y);
        float* out = smoothed + static_cast<std::size_t>(y) * width;
        for (std::size_t x = 0; x < width; ++x) out[x] = in[x];
    }
    GrayImage view;
    view.data = smoothed;
    view.stride = width * sizeof(float);
    view.width = image.width;
    view.height = image.height;
    view.channels = 1;
    gaussian_blur_in_place(view, temp, weights, kBriefSmoothRadius);
}

// Rounded patch centre, or false when the 31 x 31 patch would leave the image.
bool patch_centre(const Keypoint& keypoint, std::int32_t width, std::int32_t height,
                  std::int32_t& cx, std::int32_t& cy) {
    const double rx = std::floor(static_cast<double>(keypoint.x) + 0.5);
    const double ry = std::floor(static_cast<double>(keypoint.y) + 0.5);
    if (rx < kBriefPatchRadius || rx > width - 1 - kBriefPatchRadius) return false;
    if (ry < kBriefPatchRadius || ry > height - 1 - kBriefPatchRadius) return false;
    cx = static_cast<std::int32_t>(rx);
    cy = static_cast<std::int32_t>(ry);
    return true;
}

Descriptor describe_patch(const float* smoothed, std::int32_t width, std::int32_t cx,
                          std::int32_t cy) {
    const std::size_t w = static_cast<std::size_t>(width);
    const float* centre = smoothed + static_cast<std::size_t>(cy) * w + static_cast<std::size_t>(cx);
    const std::ptrdiff_t stride = static_cast<std::ptrdiff_t>(width);
    Descriptor d;
    for (std::int32_t k = 0; k < kBriefTests; ++k) {
        const BriefTest& t = kBriefPattern[k];
        const float first = centre[t.ay * stride + t.ax];
        const float second = centre[t.by * stride + t.bx];
        if (first < second) d.data[k / 32] |= 1u << (k % 32);
    }
    return d;
}

}  // namespace

ErrorCode v0_describe(const GrayImage& image, std::vector<Keypoint>& keypoints,
                      std::vector<Descriptor>& descriptors, const Config& config,
                      bool debug_mode) {
    (void)config;
    descriptors.clear();
    if (!valid_gray_image(image)) return ErrorCode::InvalidImage;
    if (!valid_keypoints(keypoints)) return ErrorCode::InvalidArgument;
    std::size_t pixels = 0;
    if (!gray_pixel_count(image.width, image.height, pixels)) return ErrorCode::InvalidImage;

    float weights[2 * kBriefSmoothRadius + 1];
    const ErrorCode kernel_status =
        make_gaussian_weights(kBriefSmoothSigma, kBriefSmoothRadius, weights);
    if (kernel_status != ErrorCode::Success) return kernel_status;

    std::vector<Keypoint> kept;
    std::vector<Descriptor> computed;
    try {
        std::unique_ptr<float[]> smoothed(new float[pixels]);
        std::unique_ptr<float[]> temp(new float[pixels]);
        smooth_copy(image, weights, smoothed.get(), temp.get());
        kept.reserve(keypoints.size());
        computed.reserve(keypoints.size());
        for (std::size_t i = 0; i < keypoints.size(); ++i) {
            std::int32_t cx = 0;
            std::int32_t cy = 0;
            if (!patch_centre(keypoints[i], image.width, image.height, cx, cy)) continue;
            kept.push_back(keypoints[i]);
            computed.push_back(describe_patch(smoothed.get(), image.width, cx, cy));
        }
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    }

    const std::size_t input_count = keypoints.size();
    keypoints.swap(kept);
    descriptors.swap(computed);
    if (debug_mode) {
        std::cerr << "[S3] " << image.width << "x" << image.height << " keypoints_in="
                  << input_count << " descriptors=" << descriptors.size() << '\n';
    }
    return ErrorCode::Success;
}

}  // namespace panorama
