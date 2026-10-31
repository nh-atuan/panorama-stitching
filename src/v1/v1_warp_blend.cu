// Authors: Thanh Chuong (23120195)
// External source: none

#include "v1/v1_warp_blend.h"

// Keep Host-only V0 builds independent of CUDA headers and the runtime.
#ifdef __CUDACC__
#include <cmath>
#include <cstddef>
#include <cstdint>

// Geometry and sampling follow the group's v0/v0_warp_blend.cpp; V0 stays frozen.

namespace panorama {
namespace {

constexpr double kCoordinateEpsilon = 1e-6;
constexpr double kPivotEpsilon = 1e-12;
constexpr double kReciprocalConditionEpsilon = 1e-12;
constexpr int kMaxCanvasDimension = 10000;
constexpr std::uint64_t kMaxCanvasPixels = 100000000;

struct Point { double x, y; };
struct Matrix { double data[9]; };
struct SetupMetadata {
    DeviceCanvasInfo info;
    Matrix inverse;
};

ErrorCode cuda_status(cudaError_t status) {
    if (status == cudaSuccess) return ErrorCode::Success;
    return status == cudaErrorMemoryAllocation ? ErrorCode::AllocationFailed : ErrorCode::CudaFailure;
}

bool valid_image(const Image& image) {
    if (!image.data || image.width <= 0 || image.height <= 0 || image.channels != 3)
        return false;
    const std::size_t limit = static_cast<std::size_t>(-1);
    const std::size_t width = static_cast<std::size_t>(image.width);
    return width <= limit / 3 && image.stride >= width * 3 &&
           static_cast<std::size_t>(image.height) <= limit / image.stride;
}

// Explicit rounded operations preserve V0's evaluation order even when nvcc's
// automatic FMA contraction is enabled. Explicit fma() below remains intentional.
__device__ double snap_integer(double value) {
    const double nearest = floor(__dadd_rn(value, 0.5));
    return fabs(__dsub_rn(value, nearest)) <= kCoordinateEpsilon ? nearest : value;
}

__device__ double infinity_norm(const Matrix& matrix) {
    double result = 0.0;
    for (int row = 0; row < 3; ++row) {
        const int i = row * 3;
        const double sum = __dadd_rn(__dadd_rn(fabs(matrix.data[i]), fabs(matrix.data[i + 1])),
                                    fabs(matrix.data[i + 2]));
        result = fmax(result, sum);
    }
    return result;
}

__device__ ErrorCode invert_homography(const Homography& input, Matrix& normalized,
                                      Matrix& inverse) {
    double scale = 0.0;
    for (int i = 0; i < 9; ++i) {
        if (!isfinite(input.data[i])) return ErrorCode::NumericalFailure;
        scale = fmax(scale, fabs(static_cast<double>(input.data[i])));
    }
    if (scale == 0.0) return ErrorCode::DegenerateHomography;
    double augmented[3][6] = {};
    double row_scale[3] = {};
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) {
            const double value = __ddiv_rn(static_cast<double>(input.data[row * 3 + col]), scale);
            normalized.data[row * 3 + col] = augmented[row][col] = value;
            row_scale[row] = fmax(row_scale[row], fabs(value));
        }
        if (row_scale[row] == 0.0) return ErrorCode::DegenerateHomography;
        augmented[row][row + 3] = 1.0;
    }
    // The one-thread setup retains V0's scaled partial pivoting and tie order.
    for (int col = 0; col < 3; ++col) {
        int pivot_row = col;
        double best_ratio = -1.0;
        for (int row = col; row < 3; ++row) {
            const double ratio = __ddiv_rn(fabs(augmented[row][col]), row_scale[row]);
            if (ratio > best_ratio) { best_ratio = ratio; pivot_row = row; }
        }
        if (!isfinite(best_ratio) || best_ratio <= kPivotEpsilon)
            return ErrorCode::DegenerateHomography;
        if (pivot_row != col) {
            for (int j = 0; j < 6; ++j) {
                const double temp = augmented[col][j];
                augmented[col][j] = augmented[pivot_row][j];
                augmented[pivot_row][j] = temp;
            }
            const double temp = row_scale[col];
            row_scale[col] = row_scale[pivot_row]; row_scale[pivot_row] = temp;
        }
        const double pivot = augmented[col][col];
        for (int j = 0; j < 6; ++j) {
            augmented[col][j] = __ddiv_rn(augmented[col][j], pivot);
            if (!isfinite(augmented[col][j])) return ErrorCode::DegenerateHomography;
        }
        augmented[col][col] = 1.0;
        for (int row = 0; row < 3; ++row) {
            if (row == col) continue;
            const double factor = augmented[row][col];
            for (int j = 0; j < 6; ++j) {
                augmented[row][j] = __dsub_rn(augmented[row][j],
                                             __dmul_rn(factor, augmented[col][j]));
                if (!isfinite(augmented[row][j])) return ErrorCode::DegenerateHomography;
            }
            augmented[row][col] = 0.0;
        }
    }
    for (int row = 0; row < 3; ++row)
        for (int col = 0; col < 3; ++col)
            inverse.data[row * 3 + col] = augmented[row][col + 3];
    const double product = __dmul_rn(infinity_norm(normalized), infinity_norm(inverse));
    if (!isfinite(product) || product <= 0.0 ||
        __ddiv_rn(1.0, product) <= kReciprocalConditionEpsilon)
        return ErrorCode::DegenerateHomography;
    return ErrorCode::Success;
}

__device__ bool project(const Matrix& matrix, double x, double y, double epsilon,
                        Point& point, double& w) {
    const double* m = matrix.data;
    const double u = fma(m[0], x, fma(m[1], y, m[2]));
    const double v = fma(m[3], x, fma(m[4], y, m[5]));
    w = fma(m[6], x, fma(m[7], y, m[8]));
    const double scale = __dadd_rn(__dadd_rn(fabs(__dmul_rn(m[6], x)),
                                            fabs(__dmul_rn(m[7], y))), fabs(m[8]));
    if (!isfinite(u) || !isfinite(v) || !isfinite(w) || !isfinite(scale) ||
        scale == 0.0 || fabs(w) <= __dmul_rn(epsilon, scale)) return false;
    point.x = __ddiv_rn(u, w); point.y = __ddiv_rn(v, w);
    return isfinite(point.x) && isfinite(point.y);
}

__device__ ErrorCode compute_canvas(Image a, Image b, const Matrix& h,
                                    const Config& config, DeviceCanvasInfo& info) {
    const Point corners[4] = {{0.0, 0.0}, {double(b.width - 1), 0.0},
                              {0.0, double(b.height - 1)},
                              {double(b.width - 1), double(b.height - 1)}};
    double min_x = 0.0, min_y = 0.0;
    double max_x = a.width - 1, max_y = a.height - 1;
    bool positive = false;
    for (int i = 0; i < 4; ++i) {
        Point p;
        double w;
        if (!project(h, corners[i].x, corners[i].y, config.homography_epsilon, p, w))
            return ErrorCode::NumericalFailure;
        if (i == 0) positive = w > 0.0;
        else if ((w > 0.0) != positive) return ErrorCode::NumericalFailure;
        // A common negative sign is valid; a sign change crosses the horizon.
        p.x = snap_integer(p.x); p.y = snap_integer(p.y);
        min_x = fmin(min_x, p.x); max_x = fmax(max_x, p.x);
        min_y = fmin(min_y, p.y); max_y = fmax(max_y, p.y);
    }
    const double x0 = floor(min_x), y0 = floor(min_y);
    const double width = __dadd_rn(__dsub_rn(ceil(max_x), x0), 1.0);
    const double height = __dadd_rn(__dsub_rn(ceil(max_y), y0), 1.0);
    if (!isfinite(width) || !isfinite(height) || width < 1.0 || height < 1.0 ||
        width > kMaxCanvasDimension || height > kMaxCanvasDimension ||
        -x0 < 0.0 || -x0 >= width || -y0 < 0.0 || -y0 >= height)
        return ErrorCode::InvalidCanvas;
    info.width = static_cast<int>(width); info.height = static_cast<int>(height);
    info.offset_x = static_cast<int>(-x0); info.offset_y = static_cast<int>(-y0);
    const std::uint64_t pixels = static_cast<std::uint64_t>(info.width) * info.height;
    if (pixels > config.max_canvas_pixels || pixels > kMaxCanvasPixels)
        return ErrorCode::InvalidCanvas;
    info.stride = static_cast<std::size_t>(info.width) * 3;
    if (static_cast<std::size_t>(info.height) > static_cast<std::size_t>(-1) / info.stride)
        return ErrorCode::InvalidCanvas;
    return ErrorCode::Success;
}

// Step 1: only this single thread writes geometry and inverse-H metadata.
__global__ void setup_kernel(Image a, Image b, const Homography* h, Config config,
                              SetupMetadata* metadata, DeviceCanvasInfo* public_info) {
    SetupMetadata result = {};
    Matrix normalized;
    result.info.status = invert_homography(*h, normalized, result.inverse);
    if (result.info.status == ErrorCode::Success)
        result.info.status = compute_canvas(a, b, normalized, config, result.info);
    *metadata = result;
    *public_info = result.info;
}

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

void invalidate_output(DeviceWorkspace& workspace) {
    workspace.canvas = Panorama();
    workspace.d_panorama = nullptr;
}

// On a launch failure, finish already queued writes before dropping their buffer.
ErrorCode discard_canvas(DeviceWorkspace& workspace, cudaStream_t stream, ErrorCode error) {
    const cudaError_t waited = cudaStreamSynchronize(stream);
    const cudaError_t freed = cudaFree(workspace.d_canvas);
    if (freed == cudaSuccess) {
        workspace.d_canvas = nullptr;
        workspace.canvas_capacity_bytes = 0;
    }
    invalidate_output(workspace);
    return waited == cudaSuccess && freed == cudaSuccess ? error : ErrorCode::CudaFailure;
}

}  // namespace

ErrorCode v1_warp_blend(DeviceWorkspace& workspace, const Config& config, cudaStream_t stream) {
    invalidate_output(workspace);
    if (!valid_image(workspace.imageA) || !valid_image(workspace.imageB) ||
        workspace.imageA.data != workspace.d_imageA || workspace.imageB.data != workspace.d_imageB ||
        (workspace.d_canvas && (workspace.d_canvas == workspace.d_imageA ||
                               workspace.d_canvas == workspace.d_imageB)))
        return ErrorCode::InvalidImage;
    if (!workspace.d_homography || !workspace.d_canvas_info) return ErrorCode::InvalidArgument;
    if (!std::isfinite(config.homography_epsilon) || config.homography_epsilon <= 0.0f ||
        config.homography_epsilon >= 1.0f || !config.max_canvas_pixels)
        return ErrorCode::InvalidConfig;

    SetupMetadata* device_metadata = nullptr;
    cudaError_t status = cudaMalloc(reinterpret_cast<void**>(&device_metadata), sizeof(SetupMetadata));
    if (status != cudaSuccess) return cuda_status(status);
    setup_kernel<<<1, 1, 0, stream>>>(workspace.imageA, workspace.imageB, workspace.d_homography,
                                     config, device_metadata, workspace.d_canvas_info);
    status = cudaGetLastError();
    SetupMetadata metadata = {};
    // Step 2: a small D2H read, ordered on the caller's stream (not the default stream).
    if (status == cudaSuccess)
        status = cudaMemcpyAsync(&metadata, device_metadata, sizeof(metadata), cudaMemcpyDeviceToHost, stream);
    const cudaError_t waited = cudaStreamSynchronize(stream);
    const cudaError_t released = cudaFree(device_metadata);
    if (status != cudaSuccess) return cuda_status(status);
    if (waited != cudaSuccess) return cuda_status(waited);
    if (released != cudaSuccess) return cuda_status(released);
    if (metadata.info.status != ErrorCode::Success) return metadata.info.status;

    // Recheck the small Host metadata before allocating or launching writes.
    const DeviceCanvasInfo& info = metadata.info;
    if (info.width <= 0 || info.height <= 0 || info.width > kMaxCanvasDimension ||
        info.height > kMaxCanvasDimension || info.offset_x < 0 || info.offset_y < 0 ||
        info.offset_x > info.width - workspace.imageA.width ||
        info.offset_y > info.height - workspace.imageA.height ||
        info.stride != static_cast<std::size_t>(info.width) * 3)
        return ErrorCode::InvalidCanvas;
    const std::uint64_t pixels = static_cast<std::uint64_t>(info.width) * info.height;
    if (pixels > config.max_canvas_pixels || pixels > kMaxCanvasPixels ||
        static_cast<std::size_t>(info.height) > static_cast<std::size_t>(-1) / info.stride)
        return ErrorCode::InvalidCanvas;
    const std::size_t bytes = info.stride * static_cast<std::size_t>(info.height);

    // Step 3: the Host entry point manages output allocation on the owner's behalf.
    // Release the previous canvas first, avoiding two large panoramas at peak memory.
    if (workspace.d_canvas) {
        status = cudaFree(workspace.d_canvas);
        if (status != cudaSuccess) return cuda_status(status);
        workspace.d_canvas = nullptr; workspace.canvas_capacity_bytes = 0;
    }
    std::size_t free_bytes = 0, total_bytes = 0;
    status = cudaMemGetInfo(&free_bytes, &total_bytes);
    if (status != cudaSuccess) return cuda_status(status);
    if (bytes > free_bytes) return ErrorCode::AllocationFailed;
    status = cudaMalloc(reinterpret_cast<void**>(&workspace.d_canvas), bytes);
    if (status != cudaSuccess) return cuda_status(status);
    workspace.canvas_capacity_bytes = bytes;
    status = cudaMemsetAsync(workspace.d_canvas, 0, bytes, stream);
    if (status != cudaSuccess) return discard_canvas(workspace, stream, cuda_status(status));
    Image canvas;
    canvas.data = workspace.d_canvas; canvas.stride = info.stride;
    canvas.width = info.width; canvas.height = info.height; canvas.channels = 3;
    const dim3 block(32, 8);
    const dim3 grid_a((workspace.imageA.width + block.x - 1) / block.x,
                       (workspace.imageA.height + block.y - 1) / block.y);
    copy_a_kernel<<<grid_a, block, 0, stream>>>(workspace.imageA, canvas, info.offset_x, info.offset_y);
    status = cudaGetLastError();
    if (status != cudaSuccess) return discard_canvas(workspace, stream, cuda_status(status));
    const dim3 grid_canvas((info.width + block.x - 1) / block.x, (info.height + block.y - 1) / block.y);
    gather_b_kernel<<<grid_canvas, block, 0, stream>>>(workspace.imageA, workspace.imageB, canvas,
                                                    info, metadata.inverse, config.homography_epsilon);
    status = cudaGetLastError();
    if (status != cudaSuccess) return discard_canvas(workspace, stream, cuda_status(status));

    // Step 6: publish only after successful enqueue; caller owns synchronization/D2H.
    workspace.canvas.image = canvas;
    workspace.canvas.offset_x = info.offset_x; workspace.canvas.offset_y = info.offset_y;
    workspace.d_panorama = workspace.d_canvas;
    return ErrorCode::Success;
}

}  // namespace panorama
#endif  // __CUDACC__
