// Authors: Thanh Chuong (23120195)
// External source: none

#include "common.h"
#include "cuda_utils.cuh"
#include "versions.h"
#include "stb_image.h"
#include "stb_image_write.h"

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

namespace {

const char* const kUsage =
    "Usage: ./stitch <left_image> <right_image> <output_image> "
    "--version 0 [--runs N] [--debug]";

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
    if (options.version != 0) {
        fail("Only version 0 is currently supported.", panorama::ErrorCode::UnsupportedVersion);
    }
    return options;
}

using namespace panorama;
using Clock = std::chrono::high_resolution_clock;

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

// Private stub signatures are placeholders, not the final shared stage API.
void v0_preprocess(const Image&, GrayImage&, const Config&, bool debug_mode) {
    if (debug_mode) std::cerr << "[stub] v0_preprocess\n";
}
void v0_detect(const GrayImage&, std::vector<Keypoint>&, const Config&, bool debug_mode) {
    if (debug_mode) std::cerr << "[stub] v0_detect\n";
}
void v0_describe(const GrayImage&, std::vector<Keypoint>&,
                 std::vector<Descriptor>&, const Config&, bool debug_mode) {
    if (debug_mode) std::cerr << "[stub] v0_describe\n";
}
void v0_match(const std::vector<Descriptor>&, const std::vector<Descriptor>&,
              std::vector<Match>&, const Config&, bool debug_mode) {
    if (debug_mode) std::cerr << "[stub] v0_match\n";
}
void v0_homography(const std::vector<Keypoint>&, const std::vector<Keypoint>&,
                   const std::vector<Match>&, Homography&, const Config&, bool debug_mode) {
    if (debug_mode) std::cerr << "[stub] v0_homography\n";
}
void v0_warp_blend(const Image& left, const Image&, const Homography&,
                   Panorama& output, const Config&, bool debug_mode) {
    // Borrow A solely for output-I/O testing; no homography or blending is applied.
    output.image = left;
    output.offset_x = output.offset_y = 0;
    if (debug_mode) std::cerr << "[stub] v0_warp_blend: preview is image A\n";
}

struct PipelineState {
    GrayImage gray_a, gray_b;
    std::vector<Keypoint> keypoints_a, keypoints_b;
    std::vector<Descriptor> descriptors_a, descriptors_b;
    std::vector<Match> matches;
    Homography homography;
    Panorama output;
};

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}
template <typename Function>
double measure_stage(Function function, bool collect_timing) {
    if (!collect_timing) {
        function();
        return 0.0;
    }
    const Clock::time_point start = Clock::now();
    function();
    return elapsed_ms(start, Clock::now());
}

TimingStats run_pipeline(const Image& left, const Image& right, const Config& config,
                         PipelineState& state, bool debug_mode, bool collect_timing = true) {
    TimingStats timing;
    const Clock::time_point total_start = collect_timing ? Clock::now() : Clock::time_point();
    timing.stage_ms[0] = measure_stage([&]() {
        v0_preprocess(left, state.gray_a, config, debug_mode);
        v0_preprocess(right, state.gray_b, config, debug_mode);
    }, collect_timing);
    timing.stage_ms[1] = measure_stage([&]() {
        v0_detect(state.gray_a, state.keypoints_a, config, debug_mode);
        v0_detect(state.gray_b, state.keypoints_b, config, debug_mode);
    }, collect_timing);
    timing.stage_ms[2] = measure_stage([&]() {
        v0_describe(state.gray_a, state.keypoints_a, state.descriptors_a, config, debug_mode);
        v0_describe(state.gray_b, state.keypoints_b, state.descriptors_b, config, debug_mode);
    }, collect_timing);
    timing.stage_ms[3] = measure_stage([&]() {
        v0_match(state.descriptors_a, state.descriptors_b, state.matches, config, debug_mode);
    }, collect_timing);
    timing.stage_ms[4] = measure_stage([&]() {
        v0_homography(state.keypoints_a, state.keypoints_b, state.matches,
                       state.homography, config, debug_mode);
    }, collect_timing);
    timing.stage_ms[5] = measure_stage([&]() {
        v0_warp_blend(left, right, state.homography, state.output, config, debug_mode);
    }, collect_timing);
    if (collect_timing) timing.end_to_end_ms = elapsed_ms(total_start, Clock::now());
    return timing;
}

struct TimingSummary {
    TimingStats average, minimum;
    int count = 0;
    TimingSummary() {
        for (std::size_t stage = 0; stage < kStageCount; ++stage) {
            minimum.stage_ms[stage] = std::numeric_limits<double>::max();
        }
        minimum.end_to_end_ms = std::numeric_limits<double>::max();
    }
    void add(const TimingStats& timing) {
        ++count;
        for (std::size_t stage = 0; stage < kStageCount; ++stage) {
            average.stage_ms[stage] += (timing.stage_ms[stage] - average.stage_ms[stage]) / count;
            minimum.stage_ms[stage] = std::min(minimum.stage_ms[stage], timing.stage_ms[stage]);
        }
        average.end_to_end_ms += (timing.end_to_end_ms - average.end_to_end_ms) / count;
        minimum.end_to_end_ms = std::min(minimum.end_to_end_ms, timing.end_to_end_ms);
    }
};

void print_timing(const std::string& label, const TimingStats& timing) {
    std::cout << label;
    for (std::size_t stage = 0; stage < kStageCount; ++stage) std::cout << ',' << timing.stage_ms[stage];
    std::cout << ',' << timing.end_to_end_ms << '\n';
}

int run(int argc, char** argv) {
    const panorama::CliOptions options = parse_cli(argc, argv);
    const OutputFormat format = output_format(options.output_image);
    if (options.debug) std::cerr << "[debug] Reading images...\n";
    OwnedImage left = load_image(options.left_image);
    OwnedImage right = load_image(options.right_image);
    Config config;  // Unset algorithm parameters are not used by the stubs.
    PipelineState state;
    TimingSummary summary;
    if (options.debug) {
        std::cerr << "[debug] Stub benchmark only; seed=" << config.seed
                  << ", runs=" << options.runs << '\n'
                  << "[debug] One warm-up (discarded timings).\n";
    }
    // Stage debug messages appear only in the unreported warm-up.
    run_pipeline(left.view, right.view, config, state, options.debug, false);
    std::cout.imbue(std::locale::classic());
    std::cout << std::fixed << std::setprecision(9);
    std::cout << "Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total_ms\n";
    for (int index = 0; index < options.runs; ++index) {
        // Disable logs in every timed stage, including runs with --debug.
        const TimingStats timing = run_pipeline(left.view, right.view, config, state, false);
        summary.add(timing);
        print_timing(std::to_string(index + 1), timing);
        if (options.debug) std::cerr << "[debug] Measured run " << (index + 1) << " complete.\n";
    }
    if (options.debug) std::cerr << "[debug] Writing preview image (not a panorama)...\n";
    save_image(options.output_image, format, state.output.image);
    print_timing("Average", summary.average);
    print_timing("Minimum", summary.minimum);
    std::cout.flush();
    if (!std::cout) throw std::runtime_error("Cannot write benchmark CSV to stdout.");
    return EXIT_SUCCESS;
}

const char* error_name(ErrorCode code) {
    switch (code) {
        case ErrorCode::InvalidArgument: return "InvalidArgument";
        case ErrorCode::UnknownOption: return "UnknownOption";
        case ErrorCode::UnsupportedVersion: return "UnsupportedVersion";
        case ErrorCode::InputNotFound: return "InputNotFound";
        case ErrorCode::ImageReadFailed: return "ImageReadFailed";
        case ErrorCode::ImageWriteFailed: return "ImageWriteFailed";
        case ErrorCode::InvalidImage: return "InvalidImage";
        default: return "NumericalFailure";
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        return run(argc, argv);
    } catch (const ProgramError& error) {
        std::cerr << "Error: [" << error_name(error.code) << "] " << error.what() << '\n';
        if (error.code == ErrorCode::InvalidArgument || error.code == ErrorCode::UnknownOption ||
            error.code == ErrorCode::UnsupportedVersion) std::cerr << kUsage << '\n';
    } catch (const std::bad_alloc&) {
        std::cerr << "Error: [AllocationFailed] Cannot allocate pipeline buffers.\n";
    } catch (const std::exception& error) {
        std::cerr << "Error: [NumericalFailure] " << error.what() << '\n';
    }
    std::exit(EXIT_FAILURE);
}
