// Authors: Group 16
// External source: none

#include "common.h"
#include "cuda_utils.cuh"
#include "versions.h"

#include <cstdlib>
#include <fstream>
#include <limits>

namespace {

const char* const kUsage =
    "Usage: ./stitch <left_image> <right_image> <output_image> "
    "--version <0|1|2|...> [--runs N] [--debug]";

[[noreturn]] void fail(const std::string& message) {
    std::cerr << "Error: " << message << '\n' << kUsage << '\n';
    std::exit(EXIT_FAILURE);
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
            fail("Unknown option or unexpected argument: '" + flag + "'.");
        }
    }
    if (!version_seen) {
        fail("Missing required option --version.");
    }
    return options;
}

void check_input_file(const std::string& path) {
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input.is_open()) {
        fail("Input image does not exist or cannot be opened: '" + path + "'.");
    }
    // Opening a directory may succeed; probe readability without decoding an image.
    // EOF alone is allowed here: image decoding is outside this skeleton's scope.
    input.peek();
    if (input.bad()) {
        fail("Input image is not a readable file: '" + path + "'.");
    }
}

void preprocess(const char* image_name) {
    std::cout << "[stub] preprocess " << image_name << '\n';
}

void detect(const char* image_name) {
    std::cout << "[stub] detect " << image_name << '\n';
}

void describe(const char* image_name) {
    std::cout << "[stub] describe " << image_name << '\n';
}

void match() {
    std::cout << "[stub] match\n";
}

void homography() {
    std::cout << "[stub] homography\n";
}

void warp() {
    std::cout << "[stub] warp and blend\n";
}

void run_pipeline_stubs() {
    preprocess("A");
    preprocess("B");
    detect("A");
    detect("B");
    describe("A");
    describe("B");
    match();
    homography();
    warp();
}

}  // namespace

int main(int argc, char** argv) {
    const panorama::CliOptions options = parse_cli(argc, argv);
    check_input_file(options.left_image);
    check_input_file(options.right_image);

    std::cout << "Panorama stitching skeleton: version=" << options.version
              << ", runs=" << options.runs
              << ", debug=" << (options.debug ? "true" : "false") << '\n';
    if (options.debug) {
        std::cout << "[debug] left=" << options.left_image << '\n'
                  << "[debug] right=" << options.right_image << '\n'
                  << "[debug] output=" << options.output_image << '\n';
    }

    for (int run = 0; run < options.runs; ++run) {
        std::cout << "Run " << (run + 1) << '/' << options.runs << '\n';
        run_pipeline_stubs();
    }
    std::cout << "Skeleton complete: all stages are stubs; "
                 "no panorama file was written.\n";
    return EXIT_SUCCESS;
}
