// Authors: Le Ha Thanh Chuong (23120195)
// External source: none
// Adapted from: src/v1/v1_warp_blend.cu by Thanh Chuong (23120195)

#include "common/s6_cuda_setup.cuh"
#include "v4/s6/v4_warp_blend.h"

#ifdef __CUDACC__
namespace panorama {
namespace {

__device__ bool map_to_b(const Image& b, const Matrix& inverse, int xa, int ya,
                         double epsilon, Point& point) {
    double denominator;
    if (!project(inverse, xa, ya, epsilon, point, denominator)) return false;
    point.x = snap_integer(point.x);
    point.y = snap_integer(point.y);
    return point.x >= 0.0 && point.x <= b.width - 1 &&
           point.y >= 0.0 && point.y <= b.height - 1;
}

__global__ void render_canvas_kernel(Image a, Image b, Image canvas, int ox, int oy,
                                      Matrix inverse, double epsilon) {
    const int xc = blockIdx.x * blockDim.x + threadIdx.x;
    const int yc = blockIdx.y * blockDim.y + threadIdx.y;
    if (xc >= canvas.width || yc >= canvas.height) return;

    const int xa = xc - ox, ya = yc - oy;
    const bool has_a = xa >= 0 && xa < a.width && ya >= 0 && ya < a.height;
    const std::uint8_t* pixel_a = has_a
        ? a.data + static_cast<std::size_t>(ya) * a.stride + static_cast<std::size_t>(xa) * 3
        : nullptr;
    std::uint8_t* target = canvas.data + static_cast<std::size_t>(yc) * canvas.stride +
                           static_cast<std::size_t>(xc) * 3;
    Point p;
    if (!map_to_b(b, inverse, xa, ya, epsilon, p)) {
        // An uncovered B sample leaves either the exact A bytes or black background.
        for (int c = 0; c < 3; ++c) target[c] = has_a ? pixel_a[c] : 0;
        return;
    }

    const int x0 = static_cast<int>(floor(p.x)), y0 = static_cast<int>(floor(p.y));
    const int x1 = x0 + 1 < b.width ? x0 + 1 : b.width - 1;
    const int y1 = y0 + 1 < b.height ? y0 + 1 : b.height - 1;
    const double ax = __dsub_rn(p.x, double(x0)), ay = __dsub_rn(p.y, double(y0));
    const std::uint8_t* row0 = b.data + static_cast<std::size_t>(y0) * b.stride;
    const std::uint8_t* row1 = b.data + static_cast<std::size_t>(y1) * b.stride;
    const std::size_t col0 = static_cast<std::size_t>(x0) * 3;
    const std::size_t col1 = static_cast<std::size_t>(x1) * 3;
    // Preserve the V1 evaluation order and round once, after optional blending.
    for (int c = 0; c < 3; ++c) {
        const double top = __dadd_rn(__dmul_rn(__dsub_rn(1.0, ax), row0[col0 + c]),
                                     __dmul_rn(ax, row0[col1 + c]));
        const double bottom = __dadd_rn(__dmul_rn(__dsub_rn(1.0, ax), row1[col0 + c]),
                                        __dmul_rn(ax, row1[col1 + c]));
        const double color = __dadd_rn(__dmul_rn(__dsub_rn(1.0, ay), top), __dmul_rn(ay, bottom));
        const double blended = has_a ? __dmul_rn(0.5, __dadd_rn(double(pixel_a[c]), color)) : color;
        target[c] = static_cast<std::uint8_t>(floor(__dadd_rn(fmax(0.0, fmin(255.0, blended)), 0.5)));
    }
}

}  // namespace

ErrorCode v4_warp_blend(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream) {
    SetupMetadata metadata = {};
    Image canvas;
    const ErrorCode prepared = prepare_s6_canvas(workspace, config, stream, metadata, canvas);
    if (prepared != ErrorCode::Success) return prepared;
    const DeviceCanvasInfo& info = metadata.info;
    const dim3 block(32, 8);
    const dim3 grid((info.width + block.x - 1) / block.x, (info.height + block.y - 1) / block.y);
    PANORAMA_LAUNCH_KERNEL(stream, render_canvas_kernel<<<grid, block, 0, stream>>>(
        workspace.imageA, workspace.imageB, canvas, info.offset_x, info.offset_y,
        metadata.inverse, config.homography_epsilon));
    const cudaError_t status = cudaGetLastError();
    if (status != cudaSuccess) return discard_canvas(workspace, stream, cuda_status(status));
    publish_s6_canvas(workspace, canvas, info);
    return ErrorCode::Success;
}

}  // namespace panorama
#endif  // __CUDACC__
