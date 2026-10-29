// Authors: Thanh Chuong (23120195), Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "common/common.h"
#include <cmath>
#include <vector>
#include <algorithm>
#include <iostream>

namespace panorama {
namespace {

constexpr double kCoordinateEpsilon = 1e-6;
constexpr double kPivotEpsilon = 1e-12;
constexpr double kReciprocalConditionEpsilon = 1e-12;
constexpr int kMaxCanvasDimension = 10000;
constexpr std::uint64_t kMaxCanvasPixels = 100000000;

struct Point { double x, y; };
struct Matrix { double data[9]; };
struct Canvas {
    int width, height, offset_x, offset_y;
    std::size_t stride, bytes;
};

// Own partial output until all operations succeed; publish only on success.
struct BufferGuard {
    std::uint8_t* data = nullptr;
    ~BufferGuard() { delete[] data; }
    BufferGuard() = default;
    BufferGuard(const BufferGuard&) = delete;
    BufferGuard& operator=(const BufferGuard&) = delete;
};

static bool valid_image(const Image& image) {
    if (!image.data || image.width <= 0 || image.height <= 0 || image.channels != 3)
        return false;
    const std::size_t max_size = static_cast<std::size_t>(-1);
    const std::size_t width = static_cast<std::size_t>(image.width);
    if (width > max_size / 3 || image.stride < width * 3)
        return false;
    return static_cast<std::size_t>(image.height) <= max_size / image.stride;
}

static double snap_integer(double coordinate) {
    const double nearest = std::floor(coordinate + 0.5);
    return std::abs(coordinate - nearest) <= kCoordinateEpsilon ? nearest : coordinate;
}

static double infinity_norm(const Matrix& matrix) {
    double result = 0.0;
    for (int row = 0; row < 3; ++row) {
        const int base = row * 3;
        const double sum = (std::abs(matrix.data[base]) + std::abs(matrix.data[base + 1])) +
                           std::abs(matrix.data[base + 2]);
        result = std::max(result, sum);
    }
    return result;
}

static ErrorCode invert_homography(const Homography& input, Matrix& normalized, Matrix& inverse) {
    double scale = 0.0;
    for (int i = 0; i < 9; ++i) {
        if (!std::isfinite(input.data[i])) return ErrorCode::NumericalFailure;
        scale = std::max(scale, std::abs(static_cast<double>(input.data[i])));
    }
    if (scale == 0.0) return ErrorCode::DegenerateHomography;

    double augmented[3][6] = {};
    double row_scale[3] = {};
    for (int row = 0; row < 3; ++row) {
        for (int column = 0; column < 3; ++column) {
            const double value = static_cast<double>(input.data[row * 3 + column]) / scale;
            normalized.data[row * 3 + column] = value;
            augmented[row][column] = value;
            row_scale[row] = std::max(row_scale[row], std::abs(value));
        }
        if (row_scale[row] == 0.0) return ErrorCode::DegenerateHomography;
        augmented[row][row + 3] = 1.0;
    }

    // Sequential Gauss-Jordan elimination with scaled partial pivoting.
    for (int column = 0; column < 3; ++column) {
        int pivot_row = column;
        double best_ratio = -1.0;
        for (int row = column; row < 3; ++row) {
            const double ratio = std::abs(augmented[row][column]) / row_scale[row];
            if (ratio > best_ratio) { best_ratio = ratio; pivot_row = row; }
        }
        if (!std::isfinite(best_ratio) || best_ratio <= kPivotEpsilon)
            return ErrorCode::DegenerateHomography;
        if (pivot_row != column) {
            for (int j = 0; j < 6; ++j) std::swap(augmented[column][j], augmented[pivot_row][j]);
            std::swap(row_scale[column], row_scale[pivot_row]);
        }
        const double pivot = augmented[column][column];
        for (int j = 0; j < 6; ++j) {
            augmented[column][j] /= pivot;
            if (!std::isfinite(augmented[column][j])) return ErrorCode::DegenerateHomography;
        }
        augmented[column][column] = 1.0;
        for (int row = 0; row < 3; ++row) {
            if (row == column) continue;
            const double factor = augmented[row][column];
            for (int j = 0; j < 6; ++j) {
                augmented[row][j] -= factor * augmented[column][j];
                if (!std::isfinite(augmented[row][j])) return ErrorCode::DegenerateHomography;
            }
            augmented[row][column] = 0.0;
        }
    }
    for (int row = 0; row < 3; ++row)
        for (int column = 0; column < 3; ++column)
            inverse.data[row * 3 + column] = augmented[row][column + 3];

    const double product = infinity_norm(normalized) * infinity_norm(inverse);
    if (!std::isfinite(product) || product <= 0.0 ||
        1.0 / product <= kReciprocalConditionEpsilon)
        return ErrorCode::DegenerateHomography;
    return ErrorCode::Success;
}

static bool project(const Matrix& matrix, double x, double y, double epsilon,
                    Point& point, double& denominator) {
    const double* m = matrix.data;
    const double u = std::fma(m[0], x, std::fma(m[1], y, m[2]));
    const double v = std::fma(m[3], x, std::fma(m[4], y, m[5]));
    denominator = std::fma(m[6], x, std::fma(m[7], y, m[8]));
    const double scale = (std::abs(m[6] * x) + std::abs(m[7] * y)) + std::abs(m[8]);
    if (!std::isfinite(u) || !std::isfinite(v) || !std::isfinite(denominator) ||
        !std::isfinite(scale) || scale == 0.0 || std::abs(denominator) <= epsilon * scale)
        return false;
    point = {u / denominator, v / denominator};
    return std::isfinite(point.x) && std::isfinite(point.y);
}

static ErrorCode compute_canvas(const Image& left, const Image& right, const Matrix& matrix,
                                double epsilon, std::uint64_t max_pixels, Canvas& canvas) {
    const Point corners[4] = {
        {0.0, 0.0}, {static_cast<double>(right.width - 1), 0.0},
        {0.0, static_cast<double>(right.height - 1)},
        {static_cast<double>(right.width - 1), static_cast<double>(right.height - 1)}
    };
    // Image A's four corners have these extrema in its own coordinate frame.
    double min_x = 0.0, min_y = 0.0;
    double max_x = left.width - 1, max_y = left.height - 1;
    bool positive = false;
    for (int i = 0; i < 4; ++i) {
        Point projected;
        double w;
        if (!project(matrix, corners[i].x, corners[i].y, epsilon, projected, w))
            return ErrorCode::NumericalFailure;
        if (i == 0) positive = w > 0.0;
        else if ((w > 0.0) != positive) return ErrorCode::NumericalFailure;
        projected.x = snap_integer(projected.x);
        projected.y = snap_integer(projected.y);
        min_x = std::min(min_x, projected.x); max_x = std::max(max_x, projected.x);
        min_y = std::min(min_y, projected.y); max_y = std::max(max_y, projected.y);
    }
    const double x0 = std::floor(min_x), x1 = std::ceil(max_x);
    const double y0 = std::floor(min_y), y1 = std::ceil(max_y);
    const double width = (x1 - x0) + 1.0, height = (y1 - y0) + 1.0;
    if (!std::isfinite(width) || !std::isfinite(height) ||
        width < 1.0 || height < 1.0 ||
        width > kMaxCanvasDimension || height > kMaxCanvasDimension)
        return ErrorCode::InvalidCanvas;
    // The bounds include A and hence zero. Dimension caps also bound offsets.
    if (-x0 < 0.0 || -x0 >= width || -y0 < 0.0 || -y0 >= height)
        return ErrorCode::InvalidCanvas;
    canvas.width = static_cast<int>(width); canvas.height = static_cast<int>(height);
    canvas.offset_x = static_cast<int>(-x0); canvas.offset_y = static_cast<int>(-y0);
    const std::uint64_t pixels = static_cast<std::uint64_t>(canvas.width) * canvas.height;
    if (pixels > max_pixels || pixels > kMaxCanvasPixels) return ErrorCode::InvalidCanvas;
    const std::size_t max_size = static_cast<std::size_t>(-1);
    canvas.stride = static_cast<std::size_t>(canvas.width) * 3;
    if (static_cast<std::size_t>(canvas.height) > max_size / canvas.stride)
        return ErrorCode::InvalidCanvas;
    canvas.bytes = canvas.stride * static_cast<std::size_t>(canvas.height);
    return ErrorCode::Success;
}

static bool valid_source(Point& point, const Image& image) {
    if (!std::isfinite(point.x) || !std::isfinite(point.y)) return false;
    point.x = snap_integer(point.x); point.y = snap_integer(point.y);
    return point.x >= 0.0 && point.x <= image.width - 1 &&
           point.y >= 0.0 && point.y <= image.height - 1;
}

static void bilinear(const Image& image, const Point& point, double rgb[3]) {
    const int x0 = static_cast<int>(std::floor(point.x));
    const int y0 = static_cast<int>(std::floor(point.y));
    const int x1 = std::min(x0 + 1, image.width - 1);
    const int y1 = std::min(y0 + 1, image.height - 1);
    const double ax = point.x - x0, ay = point.y - y0;
    const std::uint8_t* row0 = image.data + static_cast<std::size_t>(y0) * image.stride;
    const std::uint8_t* row1 = image.data + static_cast<std::size_t>(y1) * image.stride;
    const std::size_t column0 = static_cast<std::size_t>(x0) * 3;
    const std::size_t column1 = static_cast<std::size_t>(x1) * 3;
    for (int c = 0; c < 3; ++c) {
        const double top = (1.0 - ax) * row0[column0 + c] + ax * row0[column1 + c];
        const double bottom = (1.0 - ax) * row1[column0 + c] + ax * row1[column1 + c];
        rgb[c] = (1.0 - ay) * top + ay * bottom;
    }
}

}  // namespace

ErrorCode v0_warp_blend(const Image& left, const Image& right,
                       const Homography& homography, Panorama& output,
                       const Config& config, bool debug_mode) {
    // Never overwrite an owning pointer or free memory borrowed from an input.
    if (output.image.data != nullptr) return ErrorCode::InvalidImage;
    output = Panorama();
    if (!valid_image(left) || !valid_image(right)) return ErrorCode::InvalidImage;
    if (!std::isfinite(config.homography_epsilon) || config.homography_epsilon <= 0.0f ||
        config.homography_epsilon >= 1.0f || config.max_canvas_pixels == 0)
        return ErrorCode::InvalidConfig;
    const double epsilon = static_cast<double>(config.homography_epsilon);
    Matrix matrix, inverse;
    ErrorCode result = invert_homography(homography, matrix, inverse);
    if (result != ErrorCode::Success) return result;
    Canvas canvas;
    result = compute_canvas(left, right, matrix, epsilon, config.max_canvas_pixels, canvas);
    if (result != ErrorCode::Success) return result;
    if (debug_mode) {
        std::cout << "[S6 V0] " << canvas.width << 'x' << canvas.height
                  << ", offset=(" << canvas.offset_x << ',' << canvas.offset_y
                  << "), average blending\n";
    }
    BufferGuard buffer;
    try {
        buffer.data = new std::uint8_t[canvas.bytes]();
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    }

    // Copy A row by row, preserving input pitch and skipping its padding.
    const std::size_t left_row_bytes = static_cast<std::size_t>(left.width) * 3;
    for (int y = 0; y < left.height; ++y) {
        const std::uint8_t* source = left.data + static_cast<std::size_t>(y) * left.stride;
        std::uint8_t* destination = buffer.data +
            static_cast<std::size_t>(y + canvas.offset_y) * canvas.stride +
            static_cast<std::size_t>(canvas.offset_x) * 3;
        std::copy(source, source + left_row_bytes, destination);
    }

    // Gather B into consecutive output rows; validity is independent of RGB values.
    for (int yc = 0; yc < canvas.height; ++yc) {
        std::uint8_t* row = buffer.data + static_cast<std::size_t>(yc) * canvas.stride;
        const int ya = yc - canvas.offset_y;
        for (int xc = 0; xc < canvas.width; ++xc) {
            const int xa = xc - canvas.offset_x;
            Point source_b;
            double w;
            if (!project(inverse, xa, ya, epsilon, source_b, w) || !valid_source(source_b, right))
                continue;  // Keep A or background already in the destination.
            double color[3];
            bilinear(right, source_b, color);
            const bool has_a = xa >= 0 && xa < left.width && ya >= 0 && ya < left.height;
            std::uint8_t* destination = row + static_cast<std::size_t>(xc) * 3;
            for (int c = 0; c < 3; ++c) {
                const double blended = has_a ? 0.5 * (destination[c] + color[c]) : color[c];
                if (!std::isfinite(blended)) return ErrorCode::NumericalFailure;
                const double clamped = std::max(0.0, std::min(255.0, blended));
                destination[c] = static_cast<std::uint8_t>(std::floor(clamped + 0.5));
            }
        }
    }
    output.image.data = buffer.data;
    output.image.width = canvas.width; output.image.height = canvas.height;
    output.image.channels = 3; output.image.stride = canvas.stride;
    output.offset_x = canvas.offset_x; output.offset_y = canvas.offset_y;
    buffer.data = nullptr;  // Transfer new[] ownership to the caller.
    return ErrorCode::Success;
}

}  // namespace panorama
