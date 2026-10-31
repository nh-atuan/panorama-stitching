// Authors: Thanh Chuong (23120195)
// External source: none

#include "v1/v1_warp_blend.h"
#include "v0/v0_warp_blend.h"
#include "common/cuda_utils.cuh"
#include "common/stb_image.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>

// Linux link option -Xlinker=--wrap=cudaMalloc enables deterministic OOM tests.
// No large allocations or changes to the production allocator are needed.
static int allocations_before_failure = -1;
extern "C" cudaError_t __real_cudaMalloc(void**, std::size_t);
extern "C" cudaError_t __wrap_cudaMalloc(void** pointer, std::size_t bytes) {
    if (allocations_before_failure == 0) {
        *pointer = nullptr;
        return cudaErrorMemoryAllocation;
    }
    if (allocations_before_failure > 0) --allocations_before_failure;
    return __real_cudaMalloc(pointer, bytes);
}

namespace {
using namespace panorama;
int checks = 0, comparisons = 0, largest_difference = 0;
// Acceptance fixed before execution: exact geometry/status; <= 1 RGB code/channel.
struct Tols {
    static constexpr int max_channel_error = 1;
};

// Follow the group's throwing require/check-count convention. Do not include
// feature_test_support.h: it replaces global new for unrelated CPU OOM tests.
void assert_condition(bool condition, const char* message, const char* expression,
                      const char* file, int line) {
    if (!condition) {
        std::ostringstream error;
        error << file << ':' << line << ": " << message << " [" << expression << ']';
        throw std::runtime_error(error.str());
    }
    ++checks;
}

#define GROUP16_REQUIRE(condition, message) \
    do { assert_condition((condition), (message), #condition, __FILE__, __LINE__); } while (false)

Config settings() {
    Config config;
    config.homography_epsilon = 1e-6f;
    config.max_canvas_pixels = 100000000;
    return config;
}

Homography matrix(float a, float b, float c, float d, float e, float f,
                   float g, float h, float i) {
    Homography result;
    const float values[] = {a,b,c,d,e,f,g,h,i};
    std::copy(values, values + 9, result.data);
    return result;
}
Homography identity() { return matrix(1,0,0,0,1,0,0,0,1); }

struct Fixture {
    std::vector<std::uint8_t> bytes;
    Image image;
    Fixture(int w, int h, int padding = 0, int constant = -1)
        : bytes(static_cast<std::size_t>(w * 3 + padding) * h, 231) {
        image.data = bytes.data(); image.width = w; image.height = h;
        image.stride = w * 3 + padding; image.channels = 3;
        for (int y = 0; y < h; ++y) for (int x = 0; x < w; ++x)
            for (int c = 0; c < 3; ++c)
                bytes[y * image.stride + x * 3 + c] = constant >= 0 ? constant :
                    static_cast<std::uint8_t>((x * 37 + y * 53 + c * 89) & 255);
    }
};

struct GpuFixture {
    DeviceWorkspace workspace;
    // Stream dies first, waiting for outstanding work before buffers are released.
    struct Buffers {
        DeviceWorkspace& w;
        ~Buffers() {
            device_free(w.d_canvas); device_free(w.d_canvas_info);
            device_free(w.d_homography); device_free(w.d_imageB); device_free(w.d_imageA);
        }
    } buffers;
    CudaStream stream;
    GpuFixture(const Image& a, const Image& b, const Homography& h) : buffers{workspace} {
        device_allocate(workspace.d_imageA, a.stride * a.height);
        device_allocate(workspace.d_imageB, b.stride * b.height);
        device_allocate(workspace.d_homography, 1);
        device_allocate(workspace.d_canvas_info, 1);
        workspace.imageA = a; workspace.imageA.data = workspace.d_imageA;
        workspace.imageB = b; workspace.imageB.data = workspace.d_imageB;
        CUDA_CHECK(cudaMemcpyAsync(workspace.d_imageA, a.data, a.stride * a.height,
                                    cudaMemcpyHostToDevice, stream.get()));
        CUDA_CHECK(cudaMemcpyAsync(workspace.d_imageB, b.data, b.stride * b.height,
                                    cudaMemcpyHostToDevice, stream.get()));
        CUDA_CHECK(cudaMemcpyAsync(workspace.d_homography, &h, sizeof(h),
                                    cudaMemcpyHostToDevice, stream.get()));
        CUDA_CHECK(cudaStreamSynchronize(stream.get()));
    }
};

struct CpuOutput {
    Panorama value;
    ~CpuOutput() { delete[] value.image.data; }
};

std::vector<std::uint8_t> download(GpuFixture& gpu) {
    CUDA_CHECK(cudaStreamSynchronize(gpu.stream.get()));
    const Image& image = gpu.workspace.canvas.image;
    std::vector<std::uint8_t> output(image.stride * image.height);
    CUDA_CHECK(cudaMemcpy(output.data(), gpu.workspace.d_canvas, output.size(), cudaMemcpyDeviceToHost));
    return output;
}

struct HostCanvas {
    DeviceCanvasInfo info;
    std::vector<std::uint8_t> pixels;
};

HostCanvas render(const Image& a, const Image& b, const Homography& h, const Config& config) {
    GpuFixture gpu(a, b, h);
    GROUP16_REQUIRE(v1_warp_blend(gpu.workspace, config, gpu.stream.get()) == ErrorCode::Success,
                    "Analytic fixture failed to render");
    HostCanvas result;
    result.pixels = download(gpu);
    CUDA_CHECK(cudaMemcpy(&result.info, gpu.workspace.d_canvas_info, sizeof(result.info),
                           cudaMemcpyDeviceToHost));
    return result;
}

void expect_geometry(const HostCanvas& output, int width, int height, int ox, int oy) {
    GROUP16_REQUIRE(output.info.width == width && output.info.height == height,
                    "Canvas differs from independent geometric oracle");
    GROUP16_REQUIRE(output.info.offset_x == ox && output.info.offset_y == oy,
                    "Offset differs from independent geometric oracle");
    GROUP16_REQUIRE(output.info.stride == static_cast<std::size_t>(width) * 3,
                    "Incorrect packed RGB stride");
}

void expect_pixel(const HostCanvas& output, int x, int y, int value) {
    GROUP16_REQUIRE(x >= 0 && x < output.info.width && y >= 0 && y < output.info.height,
                    "Invalid analytic oracle coordinate");
    for (int c = 0; c < 3; ++c)
        GROUP16_REQUIRE(output.pixels[static_cast<std::size_t>(y) * output.info.stride + x * 3 + c] == value,
                        "Pixel differs from hand-derived value");
}

void expect_error(const Image& a, const Image& b, const Homography& h,
                  const Config& config, ErrorCode expected) {
    GpuFixture gpu(a, b, h);
    GROUP16_REQUIRE(v1_warp_blend(gpu.workspace, config, gpu.stream.get()) == expected,
                    "Unexpected error status for independent failure oracle");
    GROUP16_REQUIRE(!gpu.workspace.d_panorama && !gpu.workspace.canvas.image.data &&
                    !gpu.workspace.d_canvas, "Failure published or allocated output");
}

void analytic_tests() {
    const Config config = settings();
    Fixture a(4,3,5,100), b(4,3,7,20);
    const HostCanvas same = render(a.image, b.image, identity(), config);
    expect_geometry(same, 4, 3, 0, 0);
    expect_pixel(same, 0, 0, 60); expect_pixel(same, 3, 2, 60); // Last row and column.

    const HostCanvas negative = render(a.image, b.image, matrix(1,0,-2,0,1,-1,0,0,1), config);
    expect_geometry(negative, 6, 4, 2, 1);
    expect_pixel(negative, 5, 3, 100); // Only A.
    expect_pixel(negative, 0, 0, 20);  // Only B.
    expect_pixel(negative, 2, 1, 60);  // 50/50 overlap.
    expect_pixel(negative, 5, 0, 0);   // Neither source.
    const HostCanvas positive = render(a.image, b.image, matrix(1,0,2,0,1,1,0,0,1), config);
    expect_geometry(positive, 6, 4, 0, 0);
    expect_pixel(positive, 5, 3, 20);

    Fixture flat(3,1,0,20), ramp(2,1,4,0);
    for (int c = 0; c < 3; ++c) ramp.bytes[3 + c] = 100;
    const HostCanvas fractional = render(flat.image, ramp.image, matrix(1,0,0.5f,0,1,0,0,0,1), config);
    expect_geometry(fractional, 3, 1, 0, 0);
    expect_pixel(fractional, 0, 0, 20); expect_pixel(fractional, 1, 0, 35);
    expect_pixel(fractional, 2, 0, 20);

    Fixture plane(3,3,0,10), gradient(3,3,5,0);
    for (int y = 0; y < 3; ++y) for (int x = 0; x < 3; ++x) for (int c = 0; c < 3; ++c)
        gradient.bytes[y * gradient.image.stride + x * 3 + c] = x * 60;
    const HostCanvas projective = render(plane.image, gradient.image,
                                         matrix(1,0,0,0,1,0,0.25f,0,1), config);
    expect_geometry(projective, 3, 3, 0, 0);
    expect_pixel(projective, 1, 1, 45); // B=(4/3,4/3): (10+80)/2.
    expect_pixel(projective, 2, 1, 10); // B maps outside its source domain.

    Fixture tiny(2,1,0,5), black(1,1,3,0), white(1,1,5,255);
    for (float shift : {-5e-7f, -2e-6f, 5e-7f, 2e-6f}) {
        const HostCanvas snapped = render(tiny.image, tiny.image, matrix(1,0,shift,0,1,0,0,0,1), config);
        expect_geometry(snapped, std::abs(shift) <= 1e-6f ? 2 : 3, 1, shift < -1e-6f ? 1 : 0, 0);
    }
    const HostCanvas blend_black = render(black.image, white.image, identity(), config);
    expect_geometry(blend_black, 1, 1, 0, 0); expect_pixel(blend_black, 0, 0, 128);

    const HostCanvas max_dimension = render(black.image, white.image,
                                           matrix(1,0,9999,0,1,0,0,0,1), config);
    expect_geometry(max_dimension, 10000, 1, 0, 0);
    expect_pixel(max_dimension, 9999, 0, 255); expect_pixel(max_dimension, 1, 0, 0);
    expect_error(black.image, white.image, matrix(1,0,10000,0,1,0,0,0,1), config, ErrorCode::InvalidCanvas);
    Config budget = config; budget.max_canvas_pixels = 11;
    expect_error(a.image, b.image, identity(), budget, ErrorCode::InvalidCanvas);
    budget.max_canvas_pixels = 12;
    expect_geometry(render(a.image, b.image, identity(), budget), 4, 3, 0, 0);
    expect_error(a.image, b.image, Homography(), config, ErrorCode::DegenerateHomography);
    expect_error(a.image, b.image, matrix(1,0,0,0,1,0,1,0,-1), config, ErrorCode::NumericalFailure);
    Homography invalid = identity(); invalid.data[2] = std::numeric_limits<float>::quiet_NaN();
    expect_error(a.image, b.image, invalid, config, ErrorCode::NumericalFailure);
    invalid.data[2] = std::numeric_limits<float>::infinity();
    expect_error(a.image, b.image, invalid, config, ErrorCode::NumericalFailure);
}

bool compare(const Image& a, const Image& b, const Homography& h, const Config& config) {
    CpuOutput cpu;
    const ErrorCode expected = v0_warp_blend(a, b, h, cpu.value, config);
    GpuFixture gpu(a, b, h);
    const ErrorCode actual = v1_warp_blend(gpu.workspace, config, gpu.stream.get());
    GROUP16_REQUIRE(actual == expected, "CPU/GPU status mismatch");
    ++comparisons;
    if (actual != ErrorCode::Success) {
        GROUP16_REQUIRE(!gpu.workspace.d_panorama && !gpu.workspace.canvas.image.data,
                "Failure published a panorama");
        return false;
    }
    const Panorama& output = gpu.workspace.canvas;
    GROUP16_REQUIRE(output.image.width == cpu.value.image.width && output.image.height == cpu.value.image.height,
            "CPU/GPU canvas dimensions differ");
    GROUP16_REQUIRE(output.offset_x == cpu.value.offset_x && output.offset_y == cpu.value.offset_y,
            "CPU/GPU offsets differ");
    GROUP16_REQUIRE(output.image.stride == cpu.value.image.stride, "CPU/GPU stride differs");
    GROUP16_REQUIRE(gpu.workspace.d_panorama == gpu.workspace.d_canvas &&
            output.image.data == gpu.workspace.d_canvas, "Output aliases differ");
    std::vector<std::uint8_t> pixels = download(gpu);
    int max_difference = 0;
    for (std::size_t i = 0; i < pixels.size(); ++i)
        max_difference = std::max(max_difference, std::abs(int(pixels[i]) - int(cpu.value.image.data[i])));
    largest_difference = std::max(largest_difference, max_difference);
    GROUP16_REQUIRE(max_difference <= Tols::max_channel_error, "CPU/GPU pixel error exceeds fixed threshold");
    // Repeated calls replace the old owning canvas and must remain deterministic.
    GROUP16_REQUIRE(v1_warp_blend(gpu.workspace, config, gpu.stream.get()) == ErrorCode::Success, "Second run failed");
    GROUP16_REQUIRE(download(gpu) == pixels, "Repeated GPU output differs");
    std::vector<std::uint8_t> preserved_a(a.stride * a.height), preserved_b(b.stride * b.height);
    CUDA_CHECK(cudaMemcpy(preserved_a.data(), gpu.workspace.d_imageA, preserved_a.size(), cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(preserved_b.data(), gpu.workspace.d_imageB, preserved_b.size(), cudaMemcpyDeviceToHost));
    GROUP16_REQUIRE(std::equal(preserved_a.begin(), preserved_a.end(), a.data), "Modified image A or padding");
    GROUP16_REQUIRE(std::equal(preserved_b.begin(), preserved_b.end(), b.data), "Modified image B or padding");
    return true;
}

void synthetic_tests() {
    Fixture a(4,3,5,100), b(4,3,7,20);
    const Config config = settings();
    for (const Homography& h : {identity(), matrix(1,0,-2,0,1,-1,0,0,1),
            matrix(1,0,2,0,1,1,0,0,1), matrix(1,0,0.5f,0,1,-0.25f,0,0,1),
            matrix(0,-1,2,1,0,0,0,0,1), matrix(-1,0,0,0,-1,0,0,0,-1),
            matrix(1e-20f,0,0,0,1e-20f,0,0,0,1e-20f),
            matrix(1,0,0,0,1,0,0.25f,0,1)}) compare(a.image, b.image, h, config);
    Fixture black(1,1,3,0), white(1,1,5,255), line(3,1,4), column(1,5,7);
    compare(black.image, white.image, identity(), config);
    GpuFixture analytic(black.image, white.image, identity());
    GROUP16_REQUIRE(v1_warp_blend(analytic.workspace, config, analytic.stream.get()) == ErrorCode::Success,
            "Analytic black/white blend failed");
    GROUP16_REQUIRE(download(analytic) == std::vector<std::uint8_t>(3,128), "Black pixel excluded from blend");
    compare(line.image, column.image, identity(), config);
    compare(black.image, white.image, matrix(1,0,2,0,1,0,0,0,1), config);
    for (float shift : {-5e-7f, -2e-6f, 5e-7f, 2e-6f})
        compare(line.image, line.image, matrix(1,0,shift,0,1,0,0,0,1), config);
    for (const Homography& h : {Homography(), matrix(1,0,0,1,0,0,0,0,1),
            matrix(1,0,0,0,1,0,0,0,1e-14f), matrix(1,0,0,0,1,0,1,0,-1),
            matrix(1,0,1,0,1,0,1,0,0), matrix(1,0,10001,0,1,0,0,0,1)})
        compare(a.image, b.image, h, config);
    Homography bad_h = identity(); bad_h.data[2] = std::numeric_limits<float>::quiet_NaN();
    compare(a.image, b.image, bad_h, config);
    bad_h = identity(); bad_h.data[2] = std::numeric_limits<float>::infinity();
    compare(a.image, b.image, bad_h, config);
    Config invalid = config; invalid.max_canvas_pixels = 2;
    compare(a.image, b.image, identity(), invalid);
    invalid = config; invalid.homography_epsilon = 0;
    compare(a.image, b.image, identity(), invalid);
    invalid.homography_epsilon = std::numeric_limits<float>::quiet_NaN();
    compare(a.image, b.image, identity(), invalid);

    // Deterministic patterns and mild projective/affine maps around many raster borders.
    for (int i = 0; i < 40; ++i) {
        Fixture x(17 + i % 5, 13 + i % 3, i % 11), y(19 + i % 7, 11 + i % 4, i % 13);
        const Homography h = matrix(1.0f + (i % 3) * 0.01f, (i % 5 - 2) * 0.013f,
            (i % 7 - 3) * 0.375f, (i % 3 - 1) * 0.017f, 0.98f + (i % 4) * 0.01f,
            (i % 9 - 4) * 0.27f, (i % 3 - 1) * 0.0005f, (i % 5 - 2) * 0.0003f, 1);
        compare(x.image, y.image, h, config);
    }
    for (int fault : {0,1}) {
        GpuFixture oom(a.image, b.image, identity());
        allocations_before_failure = fault;
        const ErrorCode result = v1_warp_blend(oom.workspace, config, oom.stream.get());
        allocations_before_failure = -1;
        GROUP16_REQUIRE(result == ErrorCode::AllocationFailed, "OOM did not return AllocationFailed");
        GROUP16_REQUIRE(!oom.workspace.d_canvas && !oom.workspace.d_panorama &&
                !oom.workspace.canvas.image.data, "OOM published or leaked output");
        GROUP16_REQUIRE(v1_warp_blend(oom.workspace, config, oom.stream.get()) == ErrorCode::Success,
                "Recovery after OOM failed");
        download(oom);
    }
    GpuFixture invalid_view(a.image, b.image, identity());
    invalid_view.workspace.imageB.stride = 1;
    GROUP16_REQUIRE(v1_warp_blend(invalid_view.workspace, config, invalid_view.stream.get()) == ErrorCode::InvalidImage,
            "Invalid stride accepted");
    invalid_view.workspace.imageB.stride = b.image.stride;
    invalid_view.workspace.imageB.channels = 1;
    GROUP16_REQUIRE(v1_warp_blend(invalid_view.workspace, config, invalid_view.stream.get()) == ErrorCode::InvalidImage,
            "Non-RGB input accepted");
    invalid_view.workspace.imageB.channels = 3;
    invalid_view.workspace.imageB.stride = static_cast<std::size_t>(-1);
    GROUP16_REQUIRE(v1_warp_blend(invalid_view.workspace, config, invalid_view.stream.get()) == ErrorCode::InvalidImage,
            "Overflowing stride accepted");
    invalid_view.workspace.imageB.stride = b.image.stride;
    Homography* saved_h = invalid_view.workspace.d_homography;
    invalid_view.workspace.d_homography = nullptr;
    GROUP16_REQUIRE(v1_warp_blend(invalid_view.workspace, config, invalid_view.stream.get()) == ErrorCode::InvalidArgument,
            "Missing H accepted");
    invalid_view.workspace.d_homography = saved_h;
    Config bad = config; bad.homography_epsilon = 1;
    GROUP16_REQUIRE(v1_warp_blend(invalid_view.workspace, bad, invalid_view.stream.get()) == ErrorCode::InvalidConfig,
            "Invalid epsilon accepted");
    GROUP16_REQUIRE(v1_warp_blend(invalid_view.workspace, config, invalid_view.stream.get()) == ErrorCode::Success,
            "Cannot recover valid workspace");
    download(invalid_view);
    // A geometry error invalidates output aliases but retains the allocation for
    // its Host owner, without dropping the only owning pointer.
    std::uint8_t* old_canvas = invalid_view.workspace.d_canvas;
    const Homography singular;
    CUDA_CHECK(cudaMemcpyAsync(saved_h, &singular, sizeof(singular), cudaMemcpyHostToDevice,
                                invalid_view.stream.get()));
    GROUP16_REQUIRE(v1_warp_blend(invalid_view.workspace, config, invalid_view.stream.get()) ==
                ErrorCode::DegenerateHomography, "Singular H after a valid run accepted");
    GROUP16_REQUIRE(!invalid_view.workspace.d_panorama && !invalid_view.workspace.canvas.image.data &&
                invalid_view.workspace.d_canvas == old_canvas, "Lost retained canvas ownership");
    const Homography restored = identity();
    CUDA_CHECK(cudaMemcpyAsync(saved_h, &restored, sizeof(restored), cudaMemcpyHostToDevice,
                                invalid_view.stream.get()));
    // OOM when replacing an existing canvas must leave no published output.
    allocations_before_failure = 1;
    const ErrorCode replacement_oom = v1_warp_blend(invalid_view.workspace, config, invalid_view.stream.get());
    allocations_before_failure = -1;
    GROUP16_REQUIRE(replacement_oom == ErrorCode::AllocationFailed && !invalid_view.workspace.d_canvas &&
                !invalid_view.workspace.d_panorama, "OOM while replacing output leaked ownership");
}

void real_pair(int argc, char** argv) {
    if (argc == 1) return;
    if (argc != 12) throw std::runtime_error("Usage: test_gpu_s6 [A B h00 h01 ... h22]");
    int aw, ah, ac, bw, bh, bc;
    using StbImage = std::unique_ptr<stbi_uc, decltype(&stbi_image_free)>;
    StbImage a(stbi_load(argv[1], &aw, &ah, &ac, 3), stbi_image_free);
    StbImage b(stbi_load(argv[2], &bw, &bh, &bc, 3), stbi_image_free);
    if (!a || !b) throw std::runtime_error("Cannot load actual pair");
    Fixture left(aw, ah), right(bw, bh);
    std::copy(a.get(), a.get() + left.bytes.size(), left.bytes.data());
    std::copy(b.get(), b.get() + right.bytes.size(), right.bytes.data());
    Homography h;
    for (int i = 0; i < 9; ++i) h.data[i] = std::stof(argv[i + 3]);
    GROUP16_REQUIRE(compare(left.image, right.image, h, settings()),
                    "Real pair requires a valid H and an actual output comparison");
    std::cout << "Real pair: A=" << aw << 'x' << ah << " B=" << bw << 'x' << bh << '\n';
}
}  // namespace

int main(int argc, char** argv) {
    try {
        int device;
        cudaDeviceProp info;
        CUDA_CHECK(cudaGetDevice(&device)); CUDA_CHECK(cudaGetDeviceProperties(&info, device));
        std::cout << "GPU: " << info.name << '\n';
        analytic_tests(); synthetic_tests(); real_pair(argc, argv);
        std::cout << "PASS: " << checks << " checks, " << comparisons
                  << " V0/V1 comparisons; max RGB error=" << largest_difference
                  << ", threshold=" << Tols::max_channel_error << '\n';
        return 0;
    } catch (const std::exception& error) {
        allocations_before_failure = -1;
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
