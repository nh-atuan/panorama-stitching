// Authors: Thanh Chuong (23120195)
// External source: none

#include "common/s6_cuda_setup.cuh"
#include "v1/v1_warp_blend.h"

// Keep Host-only V0 builds independent of CUDA headers and the runtime.
#ifdef __CUDACC__
namespace panorama {
namespace {

// Step 4: adjacent lanes access adjacent RGB pixels on each row; honor input pitch.
__global__ void copy_a_kernel(Image a, Image canvas, int offset_x, int offset_y) {
    const int x = blockIdx.x * blockDim.x + threadIdx.x;
    const int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= a.width || y >= a.height) return;
    const std::uint8_t* source = a.data + static_cast<std::size_t>(y) * a.stride +
                                 static_cast<std::size_t>(x) * 3;
    std::uint8_t* target = canvas.data + static_cast<std::size_t>(y + offset_y) * canvas.stride +
                           static_cast<std::size_t>(x + offset_x) * 3;
    for (int c = 0; c < 3; ++c) target[c] = source[c];
}

// Step 5: one thread owns each canvas pixel; no atomics or color-based masks.
__global__ void gather_b_kernel(Image a, Image b, Image canvas, DeviceCanvasInfo info,
                                Matrix inverse, double epsilon) {
    const int xc = blockIdx.x * blockDim.x + threadIdx.x;
    const int yc = blockIdx.y * blockDim.y + threadIdx.y;
    if (xc >= canvas.width || yc >= canvas.height) return;
    const int xa = xc - info.offset_x, ya = yc - info.offset_y;
    Point p;
    double w;
    if (!project(inverse, xa, ya, epsilon, p, w)) return;
    p.x = snap_integer(p.x); p.y = snap_integer(p.y);
    if (p.x < 0.0 || p.x > b.width - 1 || p.y < 0.0 || p.y > b.height - 1) return;
    const int x0 = static_cast<int>(floor(p.x)), y0 = static_cast<int>(floor(p.y));
    const int x1 = x0 + 1 < b.width ? x0 + 1 : b.width - 1;
    const int y1 = y0 + 1 < b.height ? y0 + 1 : b.height - 1;
    const double ax = __dsub_rn(p.x, double(x0)), ay = __dsub_rn(p.y, double(y0));
    const std::uint8_t* row0 = b.data + static_cast<std::size_t>(y0) * b.stride;
    const std::uint8_t* row1 = b.data + static_cast<std::size_t>(y1) * b.stride;
    const std::size_t col0 = static_cast<std::size_t>(x0) * 3;
    const std::size_t col1 = static_cast<std::size_t>(x1) * 3;
    const bool has_a = xa >= 0 && xa < a.width && ya >= 0 && ya < a.height;
    std::uint8_t* target = canvas.data + static_cast<std::size_t>(yc) * canvas.stride +
                           static_cast<std::size_t>(xc) * 3;
    for (int c = 0; c < 3; ++c) {
        const double top = __dadd_rn(__dmul_rn(__dsub_rn(1.0, ax), row0[col0 + c]),
                                     __dmul_rn(ax, row0[col1 + c]));
        const double bottom = __dadd_rn(__dmul_rn(__dsub_rn(1.0, ax), row1[col0 + c]),
                                        __dmul_rn(ax, row1[col1 + c]));
        const double color = __dadd_rn(__dmul_rn(__dsub_rn(1.0, ay), top), __dmul_rn(ay, bottom));
        const double blended = has_a ? __dmul_rn(0.5, __dadd_rn(double(target[c]), color)) : color;
        target[c] = static_cast<std::uint8_t>(floor(__dadd_rn(fmax(0.0, fmin(255.0, blended)), 0.5)));
    }
}

}  // namespace

ErrorCode v1_warp_blend(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream) {
    SetupMetadata metadata = {};
    Image canvas;
    const ErrorCode prepared = prepare_s6_canvas(workspace, config, stream, metadata, canvas);
    if (prepared != ErrorCode::Success) return prepared;
    const DeviceCanvasInfo& info = metadata.info;
    const std::size_t bytes = canvas.stride * canvas.height;
    cudaError_t status = cudaMemsetAsync(workspace.d_canvas, 0, bytes, stream);
    if (status != cudaSuccess) return discard_canvas(workspace, stream, cuda_status(status));
    const dim3 block(32, 8);
    const dim3 grid_a((workspace.imageA.width + block.x - 1) / block.x,
                       (workspace.imageA.height + block.y - 1) / block.y);
    PANORAMA_LAUNCH_KERNEL(stream, copy_a_kernel<<<grid_a, block, 0, stream>>>(workspace.imageA, canvas, info.offset_x, info.offset_y));
    status = cudaGetLastError();
    if (status != cudaSuccess) return discard_canvas(workspace, stream, cuda_status(status));
    const dim3 grid_canvas((info.width + block.x - 1) / block.x, (info.height + block.y - 1) / block.y);
    PANORAMA_LAUNCH_KERNEL(stream, gather_b_kernel<<<grid_canvas, block, 0, stream>>>(workspace.imageA, workspace.imageB, canvas,
                                                    info, metadata.inverse, config.homography_epsilon));
    status = cudaGetLastError();
    if (status != cudaSuccess) return discard_canvas(workspace, stream, cuda_status(status));

    // Step 6: publish only after successful enqueue; caller owns synchronization/D2H.
    publish_s6_canvas(workspace, canvas, info);
    return ErrorCode::Success;
}

}  // namespace panorama
#endif  // __CUDACC__
