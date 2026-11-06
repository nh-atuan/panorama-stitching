// Authors: Le Thuong De (23120232), Le Ha Thanh Chuong (23120195), Nguyen Ho Anh Tuan (23120185),
//          Tran Huu Kim Thanh (23120166)
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
#include "v1/v1_pipeline.h"
#endif

namespace {

const char* const kUsage =
    "Usage: ./stitch <left_image> <right_image> <output_image> "
    "--version <0|1> [--runs N] [--debug]";

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
             std::string(panorama::is_supported_version(1) ? "0, 1." : "0."),
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

// Pipeline values printed by --debug, filled by V0 or V1 after all timed runs.
struct DebugSummary {
    std::size_t detected_a = 0, detected_b = 0;  // After S2.
    std::size_t kept_a = 0, kept_b = 0;          // After S3 drops border keypoints.
    std::size_t matches = 0;
    Homography homography;
    std::int32_t canvas_width = 0, canvas_height = 0;
    std::int32_t offset_x = 0, offset_y = 0;
};

DebugSummary v0_debug_summary(const V0Workspace& workspace) {
    DebugSummary summary;
    summary.detected_a = workspace.detected_a;
    summary.detected_b = workspace.detected_b;
    summary.kept_a = workspace.keypoints_a.size();
    summary.kept_b = workspace.keypoints_b.size();
    summary.matches = workspace.matches.size();
    summary.homography = workspace.homography;
    summary.canvas_width = workspace.panorama.image.width;
    summary.canvas_height = workspace.panorama.image.height;
    summary.offset_x = workspace.panorama.offset_x;
    summary.offset_y = workspace.panorama.offset_y;
    return summary;
}

// Diagnostics of the pipeline, written to stderr after all timed runs.
// The "H(B->A)=" line is parsed by scripts that compare H with a ground truth.
void print_diagnostics(const Image& left, const Image& right, const Config& config,
                       const DebugSummary& summary, const HomographyReport& report) {
    std::ostream& log = std::cerr;
    const std::ios_base::fmtflags flags = log.flags();
    const std::streamsize precision = log.precision();
    log << std::defaultfloat << std::setprecision(9);
    log << "[debug] image A=" << left.width << 'x' << left.height
        << " B=" << right.width << 'x' << right.height << '\n';
    log << "[debug] config: ";
    write_config(log, config);
    log << "[debug] S2 keypoints A=" << summary.detected_a << " B=" << summary.detected_b
        << "; kept by S3 A=" << summary.kept_a << " B=" << summary.kept_b << '\n';
    log << "[debug] S4 matches=" << summary.matches << '\n';
    log << "[debug] ";
    write_homography_report(log, report);
    log << "[debug] H(B->A)=";
    for (int i = 0; i < 9; ++i) log << (i ? " " : "") << summary.homography.data[i];
    log << '\n';
    log << "[debug] S6 canvas=" << summary.canvas_width << 'x' << summary.canvas_height
        << " offset=(" << summary.offset_x << ',' << summary.offset_y << ")\n";
    log.flags(flags);
    log.precision(precision);
}

#ifdef __CUDACC__
struct V1Events {
    CudaEvent h2d_start, h2d_stop, d2h_start, d2h_stop;
    CudaEvent stage_start[kStageCount], stage_stop[kStageCount];
};

// Pinned Host copy of the panorama. Its size is known only after S6 computes the canvas
// from H, so the untimed warm-up allocates it and the timed runs must reuse that canvas.
struct HostPanorama {
    std::unique_ptr<PinnedBuffer<std::uint8_t>> pixels;
    Panorama geometry;  // Canvas of the warm-up; geometry.image.data stays null.
};

bool same_canvas(const Panorama& a, const Panorama& b) {
    return a.image.width == b.image.width && a.image.height == b.image.height &&
           a.image.stride == b.image.stride && a.offset_x == b.offset_x &&
           a.offset_y == b.offset_y;
}

// Warm-up only, outside timing: sizes the pinned output for the canvas S6 just published.
void reserve_host_panorama(const Panorama& canvas, HostPanorama& output) {
    const Image& image = canvas.image;
    if (!image.data || image.width <= 0 || image.height <= 0 ||
        image.stride < static_cast<std::size_t>(image.width) * 3 ||
        static_cast<std::size_t>(image.height) >
            std::numeric_limits<std::size_t>::max() / image.stride) {
        fail("S6 published an invalid canvas.", ErrorCode::InvalidCanvas);
    }
    output.pixels.reset();
    output.pixels.reset(new PinnedBuffer<std::uint8_t>(
        image.stride * static_cast<std::size_t>(image.height)));
    output.geometry = canvas;
    output.geometry.image.data = nullptr;
}

// One H2D -> S1..S6 -> D2H run on `stream`. The warm-up (measure = false) sizes the pinned
// output from the canvas; a timed run fails when S6 gives another canvas.
TimingStats run_v1_once(DeviceWorkspace& workspace, const Config& config,
                        const std::uint8_t* host_a, const std::uint8_t* host_b,
                        HostPanorama& output, cudaStream_t stream, V1Events& events,
                        bool measure, DeviceCounts* after_s2) {
    using Clock = std::chrono::high_resolution_clock;
    Clock::time_point start;
    // Chrono measures synchronized Host-observed end-to-end only, never kernels.
    // The caller drains the stream before entry; completion is awaited below.
    if (measure) start = Clock::now();
    // S3-S5 skip their work once d_counts->status holds an error, so every run starts clean.
    CUDA_CHECK(cudaMemsetAsync(workspace.d_counts, 0, sizeof(DeviceCounts), stream));
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
    V1StageTrace trace;
    if (measure) {
        trace.stage_start = events.stage_start;
        trace.stage_stop = events.stage_stop;
    }
    trace.after_s2 = after_s2;
    V1StageFailure failure;
    const ErrorCode status = v1_run_stages(workspace, config, stream, trace, failure);
    if (failure.on_device) fail("Device-side check in S3-S5 failed.", status);
    check_stage(status, failure.stage);
    // S6 has waited for its setup kernel, so the canvas geometry is already on the Host.
    if (!measure) {
        reserve_host_panorama(workspace.canvas, output);
    } else if (!same_canvas(workspace.canvas, output.geometry)) {
        fail("S6 canvas changed between runs.", ErrorCode::InvalidCanvas);
    }
    const Image& canvas = workspace.canvas.image;
    if (measure) events.d2h_start.record(stream);
    CUDA_CHECK(cudaMemcpy2DAsync(output.pixels->get(), canvas.stride, canvas.data, canvas.stride,
                                static_cast<std::size_t>(canvas.width) * 3, canvas.height,
                                cudaMemcpyDeviceToHost, stream));
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
        // Kernel-only time is not measured yet (0 = not measured). Stage spans also hold
        // Host waits (S2 candidate count, S6 setup) and S6's canvas cudaMalloc, so their
        // sum is not a kernel total. The team decides how to measure this field.
        timing.total_kernel_ms = 0.0;
    }
    // Outside the timed window: S3-S5 report algorithm errors on the Device only.
    const DeviceCounts counts = v1_read_counts(workspace, stream);
    if (counts.status != ErrorCode::Success) {
        fail("Device-side check in S3-S5 failed.", counts.status);
    }
    return timing;
}

HomographyReport v1_homography_report(const V1HomographyDiagnostics& s5, const Config& config) {
    HomographyReport report;
    report.success = true;  // Read only after a run that finished without error.
    report.seed = config.seed;
    report.max_iterations = config.ransac_iters;
    report.threshold = config.ransac_threshold;
    report.attempts = s5.attempts;
    report.valid_hypotheses = s5.valid_hypotheses;
    report.rejected_samples = s5.rejected_samples;
    report.best_hypothesis = s5.best_hypothesis;
    report.adaptive_budget = s5.adaptive_budget;
    report.best_inliers = s5.best_inliers;
    report.first_refit_inliers = s5.first_refit_inliers;
    report.final_inliers = s5.final_inliers;
    report.refit_passes = s5.refit_passes;
    report.sample_hash = s5.sample_hash;
    report.best_loss = s5.best_loss;
    report.first_refit_loss = s5.first_refit_loss;
    report.refit_loss = s5.refit_loss;
    report.final_loss = s5.final_loss;
    return report;
}

DebugSummary v1_debug_summary(const DeviceCounts& after_s2, const V1Diagnostics& diagnostics) {
    DebugSummary summary;
    summary.detected_a = after_s2.keypointsA;
    summary.detected_b = after_s2.keypointsB;
    summary.kept_a = diagnostics.counts.keypointsA;
    summary.kept_b = diagnostics.counts.keypointsB;
    summary.matches = diagnostics.counts.matches;
    summary.homography = diagnostics.homography;
    summary.canvas_width = diagnostics.canvas.image.width;
    summary.canvas_height = diagnostics.canvas.image.height;
    summary.offset_x = diagnostics.canvas.offset_x;
    summary.offset_y = diagnostics.canvas.offset_y;
    return summary;
}

int run_v1(const CliOptions& options, OutputFormat format, const Image& left,
           const Image& right, const Config& config) {
    int device = 0;
    cudaDeviceProp properties;
    CUDA_CHECK(cudaGetDevice(&device));
    CUDA_CHECK(cudaGetDeviceProperties(&properties, device));
    if (options.debug) {
        std::cerr << "[debug] GPU=" << properties.name << " version=1 seed=" << config.seed
                  << " runs=" << options.runs << '\n'
                  << "[debug] One warm-up (not timed).\n";
    }
    // Declaration order ensures stream completion before pinned/device buffers die,
    // including exceptions during a partially queued run.
    V1DeviceOwner owner;
    const ErrorCode prepared = v1_prepare(left, right, config, owner);
    if (prepared != ErrorCode::Success) fail("Cannot prepare the V1 pipeline buffers.", prepared);
    const std::size_t bytes_a = left.stride * static_cast<std::size_t>(left.height);
    const std::size_t bytes_b = right.stride * static_cast<std::size_t>(right.height);
    PinnedBuffer<std::uint8_t> input_a(bytes_a), input_b(bytes_b);
    std::copy(left.data, left.data + bytes_a, input_a.get());
    std::copy(right.data, right.data + bytes_b, input_b.get());
    HostPanorama output;
    CudaStream stream;
    V1Events events;
    DeviceCounts after_s2;
    run_v1_once(owner.view, config, input_a.get(), input_b.get(), output, stream.get(), events,
                false, options.debug ? &after_s2 : nullptr);
    TimingSummary summary;
    std::cout.imbue(std::locale::classic());
    std::cout << std::fixed << std::setprecision(9)
              << "Run_Index,S1_V1_ms,S2_V1_ms,S3_V1_ms,S4_V1_ms,S5_V1_ms,S6_V1_ms,"
                 "Total_ms,H2D_ms,D2H_ms,Total_Kernel_ms\n";
    for (int index = 0; index < options.runs; ++index) {
        const TimingStats timing = run_v1_once(owner.view, config, input_a.get(), input_b.get(),
                                               output, stream.get(), events, true, nullptr);
        summary.add(timing);
        print_timing(std::to_string(index + 1), timing, true);
    }
    Image result = owner.view.canvas.image;
    result.data = output.pixels->get();
    save_image(options.output_image, format, result);  // Disk I/O is outside timing.
    print_timing("Average", summary.average, true);
    print_timing("Minimum", summary.minimum, true);
    if (options.debug) {
        std::cout.flush();  // Keep the CSV block and the stderr diagnostics apart.
        const V1Diagnostics diagnostics = v1_collect_diagnostics(owner.view, stream.get());
        print_diagnostics(left, right, config, v1_debug_summary(after_s2, diagnostics),
                          v1_homography_report(diagnostics.s5, config));
    }
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
        print_diagnostics(left.view, right.view, config, v0_debug_summary(workspace), report);
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
