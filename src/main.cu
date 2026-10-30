// Authors: Thanh Chuong (23120195), Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "common/common.h"
#include "common/cuda_utils.cuh"
#include "versions.h"
#include "common/stb_image.h"
#include "common/stb_image_write.h"

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <iomanip>
#include <limits>
#include <locale>
#include <memory>
#include <new>
#include <stdexcept>

#ifdef __CUDACC__
namespace panorama {

// Temporary V1 entry points. Replace these stubs with stage implementations in
// src/v1/; all operations must use the borrowed workspace and the supplied stream.
ErrorCode v1_preprocess(DeviceWorkspace&, const Config&, cudaStream_t) {
    return ErrorCode::Success;
}
ErrorCode v1_detect(DeviceWorkspace&, const Config&, cudaStream_t) {
    return ErrorCode::Success;
}
ErrorCode v1_describe(DeviceWorkspace&, const Config&, cudaStream_t) {
    return ErrorCode::Success;
}
ErrorCode v1_match(DeviceWorkspace&, const Config&, cudaStream_t) {
    return ErrorCode::Success;
}
ErrorCode v1_homography(DeviceWorkspace&, const Config&, cudaStream_t) {
    return ErrorCode::Success;
}
// Keep the CLI scaffold separate from the real, independently tested S6 module.
// P6 replaces this call after S1-S5 can supply a valid Device homography.
ErrorCode v1_scaffold_warp_blend(DeviceWorkspace& workspace, const Config&, cudaStream_t stream) {
    // Infrastructure smoke output only: copy A, without estimating H or stitching B.
    CUDA_CHECK(cudaMemcpy2DAsync(workspace.d_canvas, workspace.canvas.image.stride,
                                workspace.d_imageA, workspace.imageA.stride,
                                static_cast<std::size_t>(workspace.imageA.width) * 3,
                                workspace.imageA.height, cudaMemcpyDeviceToDevice, stream));
    return ErrorCode::Success;
}

}  // namespace panorama
#endif

namespace {

const char* const kUsage =
    "Usage: ./stitch <left_image> <right_image> <output_image> "
    "--version <0|1> [--runs N] [--debug] (V1: CUDA infrastructure stubs only)";

class ProgramError : public std::runtime_error {
public:
    ProgramError(const std::string& message, panorama::ErrorCode code)
        : std::runtime_error(message), code(code) {}
    panorama::ErrorCode code;
};

[[noreturn]] void fail(const std::string& message,
                       panorama::ErrorCode code = panorama::ErrorCode::InvalidArgument) {
    // Unwind owned buffers before main reports the fatal error and exits.
    throw ProgramError(message, code);
}

// Parse decimal digits only; reject signs, whitespace, trailing text and overflow.
int parse_integer(const std::string& value, const std::string& flag,
                  bool allow_zero) {
    const std::string requirement = allow_zero
        ? "a nonnegative decimal integer"
        : "a positive decimal integer";
    if (value.empty()) {
        fail(flag + " requires " + requirement + ".");
    }

    int result = 0;
    for (char digit : value) {
        if (digit < '0' || digit > '9') {
            fail(flag + " requires " + requirement + ": '" + value + "'.");
        }
        const int number = digit - '0';
        if (result > (std::numeric_limits<int>::max() - number) / 10) {
            fail(flag + " is out of range: '" + value + "'.");
        }
        result = result * 10 + number;
    }
    if (!allow_zero && result == 0) {
        fail(flag + " must be greater than zero.");
    }
    return result;
}

std::string read_option_value(int argc, char** argv, int& index,
                              const std::string& flag) {
    if (index + 1 >= argc || std::string(argv[index + 1]).compare(0, 2, "--") == 0) {
        fail("Missing value for " + flag + ".");
    }
    return argv[++index];
}

panorama::CliOptions parse_cli(int argc, char** argv) {
    if (argc < 4) {
        fail("Expected left_image, right_image and output_image.");
    }

    panorama::CliOptions options;
    std::string* const paths[] = {
        &options.left_image, &options.right_image, &options.output_image
    };
    for (int index = 1; index <= 3; ++index) {
        const std::string path = argv[index];
        if (path.empty() || path[0] == '-') {
            fail("Expected three image paths before the options; "
                 "prefix a path beginning with '-' with './'.");
        }
        *paths[index - 1] = path;
    }

    bool version_seen = false;
    bool runs_seen = false;
    bool debug_seen = false;
    for (int index = 4; index < argc; ++index) {
        const std::string flag = argv[index];
        if (flag == "--version") {
            if (version_seen) {
                fail("Duplicate option --version.");
            }
            version_seen = true;
            options.version = parse_integer(
                read_option_value(argc, argv, index, flag), flag, true);
        } else if (flag == "--runs") {
            if (runs_seen) {
                fail("Duplicate option --runs.");
            }
            runs_seen = true;
            options.runs = parse_integer(
                read_option_value(argc, argv, index, flag), flag, false);
        } else if (flag == "--debug") {
            if (debug_seen) {
                fail("Duplicate option --debug.");
            }
            debug_seen = true;
            options.debug = true;
        } else {
            fail("Unknown option or unexpected argument: '" + flag + "'.",
                 panorama::ErrorCode::UnknownOption);
        }
    }
    if (!version_seen) {
        fail("Missing required option --version.");
    }
    if (!panorama::is_supported_version(options.version)) {
        fail("Version " + std::to_string(options.version) + " is not available; "
             "supported versions in this build: " +
             std::string(panorama::is_supported_version(1) ? "0, 1 (stubs)." : "0."),
             panorama::ErrorCode::UnsupportedVersion);
    }
    return options;
}

using namespace panorama;

enum class OutputFormat { Png, Jpeg };

OutputFormat output_format(const std::string& path) {
    const std::size_t dot = path.find_last_of('.');
    std::string extension = dot == std::string::npos ? "" : path.substr(dot);
    for (char& c : extension) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    if (extension == ".png") return OutputFormat::Png;
    if (extension == ".jpg" || extension == ".jpeg") return OutputFormat::Jpeg;
    fail("Output extension must be .png, .jpg or .jpeg.");
}

struct OwnedImage {
    std::unique_ptr<stbi_uc, decltype(&stbi_image_free)> pixels;
    Image view;
    OwnedImage() : pixels(nullptr, stbi_image_free) {}
};

OwnedImage load_image(const std::string& path) {
    errno = 0;
    std::FILE* file = std::fopen(path.c_str(), "rb");
    if (!file) {
        const int open_error = errno;
        fail("Cannot open input image: '" + path + "'.",
             open_error == ENOENT ? ErrorCode::InputNotFound : ErrorCode::ImageReadFailed);
    }
    std::fclose(file);
    OwnedImage image;
    int width = 0, height = 0, source_channels = 0;
    image.pixels.reset(stbi_load(path.c_str(), &width, &height, &source_channels, 3));
    if (!image.pixels) {
        const char* reason = stbi_failure_reason();
        fail("Cannot decode input image: '" + path + "': " +
             (reason ? reason : "unknown stb error") + ".", ErrorCode::ImageReadFailed);
    }
    if (width <= 0 || height <= 0 ||
        static_cast<std::size_t>(width) > std::numeric_limits<std::size_t>::max() / 3) {
        fail("Invalid input image dimensions.", ErrorCode::InvalidImage);
    }
    const std::size_t stride = static_cast<std::size_t>(width) * 3;
    if (static_cast<std::size_t>(height) > std::numeric_limits<std::size_t>::max() / stride) {
        fail("Input image byte size overflows.", ErrorCode::InvalidImage);
    }
    image.view.data = image.pixels.get();
    image.view.width = width;
    image.view.height = height;
    image.view.channels = 3;
    image.view.stride = stride;
    return image;
}

void save_image(const std::string& path, OutputFormat format, const Image& image) {
    if (!image.data || image.width <= 0 || image.height <= 0 || image.channels != 3 ||
        static_cast<std::size_t>(image.width) > static_cast<std::size_t>(std::numeric_limits<int>::max()) / 3) {
        fail("Invalid RGB output dimensions.", ErrorCode::InvalidImage);
    }
    const std::size_t row_bytes = static_cast<std::size_t>(image.width) * 3;
    if (image.stride < row_bytes || image.stride > static_cast<std::size_t>(std::numeric_limits<int>::max()) ||
        static_cast<std::size_t>(image.height) > std::numeric_limits<std::size_t>::max() / image.stride) {
        fail("Invalid output stride or byte size.", ErrorCode::InvalidImage);
    }
    int written = 0;
    if (format == OutputFormat::Png) {
        written = stbi_write_png(path.c_str(), image.width, image.height, 3,
                                 image.data, static_cast<int>(image.stride));
    } else {
        // JPEG has no stride argument; pack padded rows outside timing.
        std::vector<std::uint8_t> packed;
        const std::uint8_t* pixels = image.data;
        if (image.stride != row_bytes) {
            packed.resize(row_bytes * static_cast<std::size_t>(image.height));
            for (int y = 0; y < image.height; ++y) {
                const std::uint8_t* row = image.data + static_cast<std::size_t>(y) * image.stride;
                std::copy(row, row + row_bytes, packed.data() + static_cast<std::size_t>(y) * row_bytes);
            }
            pixels = packed.data();
        }
        written = stbi_write_jpg(path.c_str(), image.width, image.height, 3, pixels, 95);
    }
    if (!written) fail("Cannot write output image: '" + path + "'.", ErrorCode::ImageWriteFailed);
}

struct TimingSummary {
    TimingStats average, minimum;
    int count = 0;
    TimingSummary() {
        for (std::size_t stage = 0; stage < kStageCount; ++stage) {
            minimum.stage_ms[stage] = std::numeric_limits<double>::max();
        }
        minimum.end_to_end_ms = std::numeric_limits<double>::max();
        minimum.h2d_ms = minimum.d2h_ms = minimum.total_kernel_ms =
            std::numeric_limits<double>::max();
    }
    void add(const TimingStats& timing) {
        ++count;
        for (std::size_t stage = 0; stage < kStageCount; ++stage) {
            average.stage_ms[stage] += (timing.stage_ms[stage] - average.stage_ms[stage]) / count;
            minimum.stage_ms[stage] = std::min(minimum.stage_ms[stage], timing.stage_ms[stage]);
        }
        average.end_to_end_ms += (timing.end_to_end_ms - average.end_to_end_ms) / count;
        minimum.end_to_end_ms = std::min(minimum.end_to_end_ms, timing.end_to_end_ms);
        const double values[] = {timing.h2d_ms, timing.d2h_ms, timing.total_kernel_ms};
        double* averages[] = {&average.h2d_ms, &average.d2h_ms, &average.total_kernel_ms};
        double* minima[] = {&minimum.h2d_ms, &minimum.d2h_ms, &minimum.total_kernel_ms};
        for (int i = 0; i < 3; ++i) {
            *averages[i] += (values[i] - *averages[i]) / count;
            *minima[i] = std::min(*minima[i], values[i]);
        }
    }
};

void print_timing(const std::string& label, const TimingStats& timing, bool gpu = false) {
    std::cout << label;
    for (std::size_t stage = 0; stage < kStageCount; ++stage) std::cout << ',' << timing.stage_ms[stage];
    std::cout << ',' << timing.end_to_end_ms;
    if (gpu) {
        std::cout << ',' << timing.h2d_ms << ',' << timing.d2h_ms
                  << ',' << timing.total_kernel_ms;
    }
    std::cout << '\n';
}

void check_stage(ErrorCode status, Stage stage) {
    if (status != ErrorCode::Success) fail(std::string(stage_name(stage)) + " failed.", status);
}

// Diagnostics of the pipeline, written to stderr after all timed runs.
// The "H(B->A)=" line is parsed by scripts that compare H with a ground truth.
void print_diagnostics(const Image& left, const Image& right, const Config& config,
                       const V0Workspace& workspace, const HomographyReport& report) {
    std::ostream& log = std::cerr;
    const std::ios_base::fmtflags flags = log.flags();
    const std::streamsize precision = log.precision();
    log << std::defaultfloat << std::setprecision(9);
    log << "[debug] image A=" << left.width << 'x' << left.height
        << " B=" << right.width << 'x' << right.height << '\n';
    log << "[debug] config: ";
    write_config(log, config);
    log << "[debug] S2 keypoints A=" << workspace.detected_a << " B=" << workspace.detected_b
        << "; kept by S3 A=" << workspace.keypoints_a.size()
        << " B=" << workspace.keypoints_b.size() << '\n';
    log << "[debug] S4 matches=" << workspace.matches.size() << '\n';
    log << "[debug] ";
    write_homography_report(log, report);
    log << "[debug] H(B->A)=";
    for (int i = 0; i < 9; ++i) log << (i ? " " : "") << workspace.homography.data[i];
    log << '\n';
    log << "[debug] S6 canvas=" << workspace.panorama.image.width << 'x'
        << workspace.panorama.image.height << " offset=(" << workspace.panorama.offset_x
        << ',' << workspace.panorama.offset_y << ")\n";
    log.flags(flags);
    log.precision(precision);
}

#ifdef __CUDACC__
// Owns each allocation once. Alias image views in DeviceWorkspace are never freed.
struct OwnedDeviceWorkspace {
    DeviceWorkspace view;
    OwnedDeviceWorkspace() = default;
    OwnedDeviceWorkspace(const OwnedDeviceWorkspace&) = delete;
    OwnedDeviceWorkspace& operator=(const OwnedDeviceWorkspace&) = delete;
    ~OwnedDeviceWorkspace() {
        device_free(view.d_scratch);
        device_free(view.d_canvas_info);
        device_free(view.d_counts);
        device_free(view.d_canvas);
        device_free(view.d_homography);
        device_free(view.d_matches);
        device_free(view.d_descriptorsB);
        device_free(view.d_descriptorsA);
        device_free(view.d_keypointsB);
        device_free(view.d_keypointsA);
        device_free(view.d_grayB);
        device_free(view.d_grayA);
        device_free(view.d_imageB);
        device_free(view.d_imageA);
    }
};

void prepare_device_workspace(const Image& left, const Image& right, const Config& config,
                              DeviceWorkspace& workspace) {
    const std::size_t bytes_a = left.stride * static_cast<std::size_t>(left.height);
    const std::size_t bytes_b = right.stride * static_cast<std::size_t>(right.height);
    const std::size_t features = static_cast<std::size_t>(config.max_keypoints);
    device_allocate(workspace.d_imageA, bytes_a);
    device_allocate(workspace.d_imageB, bytes_b);
    workspace.imageA = left;
    workspace.imageB = right;
    workspace.imageA.data = workspace.d_imageA;
    workspace.imageB.data = workspace.d_imageB;
    device_allocate(workspace.d_grayA, static_cast<std::size_t>(left.width) * left.height);
    device_allocate(workspace.d_grayB, static_cast<std::size_t>(right.width) * right.height);
    workspace.grayA.data = workspace.d_grayA;
    workspace.grayA.width = left.width;
    workspace.grayA.height = left.height;
    workspace.grayA.channels = 1;
    workspace.grayA.stride = static_cast<std::size_t>(left.width) * sizeof(float);
    workspace.grayB.data = workspace.d_grayB;
    workspace.grayB.width = right.width;
    workspace.grayB.height = right.height;
    workspace.grayB.channels = 1;
    workspace.grayB.stride = static_cast<std::size_t>(right.width) * sizeof(float);
    device_allocate(workspace.d_keypointsA, features);
    device_allocate(workspace.d_keypointsB, features);
    device_allocate(workspace.d_descriptorsA, features);
    device_allocate(workspace.d_descriptorsB, features);
    device_allocate(workspace.d_matches, features);
    device_allocate(workspace.d_homography, 1);
    device_allocate(workspace.d_counts, 1);
    device_allocate(workspace.d_canvas_info, 1);
    CUDA_CHECK(cudaMemset(workspace.d_counts, 0, sizeof(DeviceCounts)));
    CUDA_CHECK(cudaMemset(workspace.d_canvas_info, 0, sizeof(DeviceCanvasInfo)));
    workspace.keypoint_capacityA = workspace.keypoint_capacityB = features;
    workspace.descriptor_capacityA = workspace.descriptor_capacityB = features;
    workspace.match_capacity = features;
    // The stub has A's canvas. Real S6 must publish its computed geometry first;
    // the Host owner then checks the budget and reserves the required capacity.
    device_allocate(workspace.d_canvas, bytes_a);
    workspace.canvas_capacity_bytes = bytes_a;
    workspace.canvas.image = workspace.imageA;
    workspace.canvas.image.data = workspace.d_canvas;
}

struct V1Events {
    CudaEvent h2d_start, h2d_stop, d2h_start, d2h_stop;
    CudaEvent stage_start[kStageCount], stage_stop[kStageCount];
};

TimingStats run_v1_once(DeviceWorkspace& workspace, const Config& config,
                        const std::uint8_t* host_a, const std::uint8_t* host_b,
                        std::uint8_t* host_output, cudaStream_t stream,
                        V1Events& events, bool measure) {
    using Clock = std::chrono::high_resolution_clock;
    Clock::time_point start;
    // Chrono measures synchronized Host-observed end-to-end only, never kernels.
    // The caller drains the stream before entry; completion is awaited below.
    if (measure) start = Clock::now();
    if (measure) events.h2d_start.record(stream);
    CUDA_CHECK(cudaMemcpy2DAsync(workspace.d_imageA, workspace.imageA.stride,
                                host_a, workspace.imageA.stride,
                                static_cast<std::size_t>(workspace.imageA.width) * 3,
                                workspace.imageA.height, cudaMemcpyHostToDevice, stream));
    CUDA_CHECK(cudaMemcpy2DAsync(workspace.d_imageB, workspace.imageB.stride,
                                host_b, workspace.imageB.stride,
                                static_cast<std::size_t>(workspace.imageB.width) * 3,
                                workspace.imageB.height, cudaMemcpyHostToDevice, stream));
    if (measure) events.h2d_stop.record(stream);
    typedef ErrorCode (*StageFunction)(DeviceWorkspace&, const Config&, cudaStream_t);
    const StageFunction stages[] = {v1_preprocess, v1_detect, v1_describe,
                                   v1_match, v1_homography, v1_scaffold_warp_blend};
    for (std::size_t i = 0; i < kStageCount; ++i) {
        if (measure) events.stage_start[i].record(stream);
        check_stage(stages[i](workspace, config, stream), static_cast<Stage>(i));
        CUDA_CHECK(cudaGetLastError());  // Catch immediate launch errors as kernels arrive.
        if (measure) events.stage_stop[i].record(stream);
    }
    if (measure) events.d2h_start.record(stream);
    CUDA_CHECK(cudaMemcpy2DAsync(host_output, workspace.canvas.image.stride,
                                workspace.d_canvas, workspace.canvas.image.stride,
                                static_cast<std::size_t>(workspace.canvas.image.width) * 3,
                                workspace.canvas.image.height, cudaMemcpyDeviceToHost, stream));
    if (measure) {
        events.d2h_stop.record(stream);
        events.d2h_stop.synchronize();  // One wait after all stages and final D2H.
    } else {
        CUDA_CHECK(cudaStreamSynchronize(stream));
    }
    TimingStats timing;
    if (measure) {
        timing.end_to_end_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
        timing.h2d_ms = events.h2d_stop.elapsed_since(events.h2d_start);
        timing.d2h_ms = events.d2h_stop.elapsed_since(events.d2h_start);
        for (std::size_t i = 0; i < kStageCount; ++i) {
            timing.stage_ms[i] = events.stage_stop[i].elapsed_since(events.stage_start[i]);
        }
        // No compute kernels exist in these stubs. S6's D2D copy is not a kernel.
        // Real stages must supply kernel-only event measurements before this can
        // report nonzero total_kernel_ms; do not substitute the sum of stage spans.
        timing.total_kernel_ms = 0.0;
    }
    return timing;
}

int run_v1(const CliOptions& options, OutputFormat format, const Image& left,
           const Image& right, const Config& config) {
    std::cerr << "Warning: V1 is an infrastructure scaffold with six stubs. "
                 "Output copies image A; timings are not stitching benchmarks.\n";
    int device = 0;
    cudaDeviceProp properties;
    CUDA_CHECK(cudaGetDevice(&device));
    CUDA_CHECK(cudaGetDeviceProperties(&properties, device));
    if (options.debug) {
        std::cerr << "[debug] GPU=" << properties.name << " version=1 (stubs) runs="
                  << options.runs << " seed=" << config.seed << '\n'
                  << "[debug] Config: ";
        write_config(std::cerr, config);
        std::cerr << "\n[debug] One warm-up (not timed): S1 S2 S3 S4 S5 S6 stubs.\n";
    }
    // Declaration order ensures stream completion before pinned/device buffers die,
    // including exceptions during a partially queued run.
    OwnedDeviceWorkspace owner;
    prepare_device_workspace(left, right, config, owner.view);
    const std::size_t bytes_a = left.stride * static_cast<std::size_t>(left.height);
    const std::size_t bytes_b = right.stride * static_cast<std::size_t>(right.height);
    PinnedBuffer<std::uint8_t> input_a(bytes_a), input_b(bytes_b), output(bytes_a);
    std::copy(left.data, left.data + bytes_a, input_a.get());
    std::copy(right.data, right.data + bytes_b, input_b.get());
    CudaStream stream;
    V1Events events;
    run_v1_once(owner.view, config, input_a.get(), input_b.get(), output.get(),
                stream.get(), events, false);
    TimingSummary summary;
    std::cout.imbue(std::locale::classic());
    std::cout << std::fixed << std::setprecision(9)
              << "Run_Index,S1_V1_ms,S2_V1_ms,S3_V1_ms,S4_V1_ms,S5_V1_ms,S6_V1_ms,"
                 "Total_ms,H2D_ms,D2H_ms,Total_Kernel_ms\n";
    for (int index = 0; index < options.runs; ++index) {
        const TimingStats timing = run_v1_once(owner.view, config, input_a.get(), input_b.get(),
                                               output.get(), stream.get(), events, true);
        summary.add(timing);
        print_timing(std::to_string(index + 1), timing, true);
    }
    Image result = owner.view.canvas.image;
    result.data = output.get();
    save_image(options.output_image, format, result);  // Disk I/O is outside timing.
    print_timing("Average", summary.average, true);
    print_timing("Minimum", summary.minimum, true);
    std::cout.flush();
    if (!std::cout) throw std::runtime_error("Cannot write benchmark CSV to stdout.");
    return EXIT_SUCCESS;
}
#endif  // __CUDACC__

int run(int argc, char** argv) {
    const panorama::CliOptions options = parse_cli(argc, argv);
    const OutputFormat format = output_format(options.output_image);
    if (options.debug) std::cerr << "[debug] Reading images...\n";
    OwnedImage left = load_image(options.left_image);
    OwnedImage right = load_image(options.right_image);
    Config config;
    if (make_v0_config(left.view.width, left.view.height, config) != ErrorCode::Success) {
        fail("Cannot build the V0 configuration.", ErrorCode::InvalidConfig);
    }
#ifdef __CUDACC__
    if (options.version == 1) return run_v1(options, format, left.view, right.view, config);
#endif
    V0Workspace workspace;
    Stage stage = Stage::Preprocess;
    const ErrorCode prepared = v0_prepare(left.view, right.view, config, workspace);
    if (prepared != ErrorCode::Success) fail("Cannot prepare the V0 pipeline buffers.", prepared);
    if (options.debug) {
        std::cerr << "[debug] version=" << options.version << " seed=" << config.seed
                  << " runs=" << options.runs << '\n'
                  << "[debug] One warm-up (not timed).\n";
    }
    // Only the untimed warm-up collects the S5 report; V0 is deterministic, so the
    // timed runs produce the same matches, H and panorama.
    HomographyReport report;
    ErrorCode status = v0_run(left.view, right.view, config, workspace, nullptr, &stage, &report);
    check_stage(status, stage);
    TimingSummary summary;
    std::cout.imbue(std::locale::classic());
    std::cout << std::fixed << std::setprecision(9);
    std::cout << "Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total_ms\n";
    for (int index = 0; index < options.runs; ++index) {
        v0_release_output(workspace);  // Outside the timed region.
        TimingStats timing;
        status = v0_run(left.view, right.view, config, workspace, &timing, &stage);
        check_stage(status, stage);
        summary.add(timing);
        print_timing(std::to_string(index + 1), timing);
        if (options.debug) std::cerr << "[debug] Measured run " << (index + 1) << " complete.\n";
    }
    save_image(options.output_image, format, workspace.panorama.image);
    print_timing("Average", summary.average);
    print_timing("Minimum", summary.minimum);
    if (options.debug) {
        std::cout.flush();  // Keep the CSV block and the stderr diagnostics apart.
        print_diagnostics(left.view, right.view, config, workspace, report);
    }
    std::cout.flush();
    if (!std::cout) throw std::runtime_error("Cannot write benchmark CSV to stdout.");
    return EXIT_SUCCESS;
}

const char* error_name(ErrorCode code) {
    switch (code) {
        case ErrorCode::Success: return "Success";
        case ErrorCode::InvalidArgument: return "InvalidArgument";
        case ErrorCode::UnknownOption: return "UnknownOption";
        case ErrorCode::UnsupportedVersion: return "UnsupportedVersion";
        case ErrorCode::InputNotFound: return "InputNotFound";
        case ErrorCode::ImageReadFailed: return "ImageReadFailed";
        case ErrorCode::ImageWriteFailed: return "ImageWriteFailed";
        case ErrorCode::InvalidImage: return "InvalidImage";
        case ErrorCode::InvalidConfig: return "InvalidConfig";
        case ErrorCode::InsufficientKeypoints: return "InsufficientKeypoints";
        case ErrorCode::InsufficientMatches: return "InsufficientMatches";
        case ErrorCode::DegenerateHomography: return "DegenerateHomography";
        case ErrorCode::NumericalFailure: return "NumericalFailure";
        case ErrorCode::InvalidCanvas: return "InvalidCanvas";
        case ErrorCode::AllocationFailed: return "AllocationFailed";
        case ErrorCode::CudaFailure: return "CudaFailure";
    }
    return "UnknownError";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        return run(argc, argv);
    } catch (const ProgramError& error) {
        std::cerr << "Error: [" << error_name(error.code) << "] " << error.what() << '\n';
        if (error.code == ErrorCode::InvalidArgument || error.code == ErrorCode::UnknownOption ||
            error.code == ErrorCode::UnsupportedVersion) std::cerr << kUsage << '\n';
#ifdef __CUDACC__
    } catch (const panorama::CudaError&) {
        // CUDA_CHECK has reported the call; all stack-owned resources are now released.
#endif
    } catch (const std::bad_alloc&) {
        std::cerr << "Error: [AllocationFailed] Cannot allocate pipeline buffers.\n";
    } catch (const std::exception& error) {
        std::cerr << "Error: [NumericalFailure] " << error.what() << '\n';
    }
    std::exit(EXIT_FAILURE);
}
