// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// P10-T02 acceptance for the per-image V5 API (src/v5/v5_image_branch.h).
// Reference: the S1-S3 path of V4 (v4_prepare, then v1_preprocess, v1_detect, v1_describe on
// one DeviceWorkspace). Candidate: one V5ImageBranch per image, run A then B through the API,
// then both branches on two streams at once. Gray images, counts, keypoints (order and float
// bits) and descriptors (every bit) must be identical. A second part checks that invalid
// views and Config values are rejected on the host before any work is enqueued.

#include "gpu/pipeline_test_support.cuh"
#include "v1/s1/v1_preprocess.h"
#include "v1/s2/v1_detect.h"
#include "v1/s3/v1_describe.h"
#include "v4/v4_pipeline.h"
#include "v5/v5_image_branch.h"

using namespace pipeline_test;

namespace {

std::string status_name(ErrorCode status) { return std::to_string(static_cast<unsigned>(status)); }

void require_status(ErrorCode actual, ErrorCode expected, const std::string& label) {
    require(actual == expected, label + ": expected status " + status_name(expected) + ", got " +
                                    status_name(actual));
}

// Features of one image after S3, read back to the host.
struct Features {
    std::vector<float> gray;
    std::vector<Keypoint> keypoints;
    std::vector<Descriptor> descriptors;
    std::uint32_t keypoint_count = 0, descriptor_count = 0;
    ErrorCode status = ErrorCode::Success;
};

std::vector<float> read_gray(const float* data, int width, int height) {
    std::vector<float> values(static_cast<std::size_t>(width) * height);
    cuda(cudaMemcpy(values.data(), data, values.size() * sizeof(float), cudaMemcpyDeviceToHost));
    return values;
}

template<class T>
std::vector<T> read_array(const T* data, std::uint32_t count) {
    std::vector<T> values(count);
    if (count) cuda(cudaMemcpy(values.data(), data, count * sizeof(T), cudaMemcpyDeviceToHost));
    return values;
}

// ------------------------------------------------------------------ reference (V4 S1-S3)

void reference_features(const Image& a, const Image& b, const Config& config, Features out[2]) {
    V1DeviceOwner owner;
    require_status(v4_prepare(a, b, config, owner), ErrorCode::Success, "reference prepare");
    DeviceWorkspace& ws = owner.view;
    Stream stream;
    upload_images(a, b, ws, stream.value);
    cuda(cudaMemsetAsync(ws.d_counts, 0, sizeof(DeviceCounts), stream.value));
    require_status(v1_preprocess(ws, config, stream.value), ErrorCode::Success, "reference S1");
    require_status(v1_detect(ws, config, stream.value), ErrorCode::Success, "reference S2");
    require_status(v1_describe(ws, config, stream.value), ErrorCode::Success, "reference S3");
    stream.wait();
    DeviceCounts counts;
    cuda(cudaMemcpy(&counts, ws.d_counts, sizeof(counts), cudaMemcpyDeviceToHost));
    out[0].gray = read_gray(ws.d_grayA, a.width, a.height);
    out[1].gray = read_gray(ws.d_grayB, b.width, b.height);
    out[0].keypoint_count = counts.keypointsA;
    out[0].descriptor_count = counts.descriptorsA;
    out[1].keypoint_count = counts.keypointsB;
    out[1].descriptor_count = counts.descriptorsB;
    out[0].keypoints = read_array(ws.d_keypointsA, counts.keypointsA);
    out[1].keypoints = read_array(ws.d_keypointsB, counts.keypointsB);
    out[0].descriptors = read_array(ws.d_descriptorsA, counts.descriptorsA);
    out[1].descriptors = read_array(ws.d_descriptorsB, counts.descriptorsB);
    out[0].status = out[1].status = counts.status;
}

// ------------------------------------------------------------------ candidate (V5 API)

// Owns the storage that V5ImageBranch borrows, sized as the T03 dispatcher sizes it.
struct BranchStorage {
    gpu_test::DeviceBuffer<std::uint8_t> rgb;
    gpu_test::DeviceBuffer<float> gray;
    gpu_test::DeviceBuffer<Keypoint> keypoints;
    gpu_test::DeviceBuffer<Descriptor> descriptors;
    gpu_test::DeviceBuffer<DeviceCounts> counts;
    gpu_test::DeviceBuffer<std::uint8_t> scratch;
    std::uint8_t* host_rgb = nullptr;
    std::uint32_t* host_candidates = nullptr;
    Image pinned;
    V5ImageBranch view;

    BranchStorage(const Image& host, const Config& config, std::size_t scratch_bytes)
        : rgb(static_cast<std::size_t>(host.width) * 3 * host.height),
          gray(static_cast<std::size_t>(host.width) * host.height),
          keypoints(static_cast<std::size_t>(config.max_keypoints)),
          descriptors(static_cast<std::size_t>(config.max_keypoints)),
          counts(1),
          scratch(scratch_bytes) {
        const std::size_t row = static_cast<std::size_t>(host.width) * 3;
        cuda(cudaMallocHost(reinterpret_cast<void**>(&host_rgb), row * host.height));
        cuda(cudaMallocHost(reinterpret_cast<void**>(&host_candidates), sizeof(std::uint32_t)));
        for (int y = 0; y < host.height; ++y) {
            std::memcpy(host_rgb + row * y, host.data + host.stride * y, row);
        }
        pinned = host;
        pinned.data = host_rgb;
        pinned.stride = row;
        view.image = host;
        view.image.data = rgb.data;
        view.image.stride = row;
        view.gray.data = gray.data;
        view.gray.stride = static_cast<std::size_t>(host.width) * sizeof(float);
        view.gray.width = host.width;
        view.gray.height = host.height;
        view.gray.channels = 1;
        view.keypoints = keypoints.data;
        view.descriptors = descriptors.data;
        view.counts = counts.data;
        view.scratch = scratch.data;
        view.scratch_bytes = scratch_bytes;
        view.feature_capacity = static_cast<std::size_t>(config.max_keypoints);
        view.host_candidates = host_candidates;
    }
    BranchStorage(const BranchStorage&) = delete;
    BranchStorage& operator=(const BranchStorage&) = delete;
    ~BranchStorage() {
        cudaFreeHost(host_rgb);
        cudaFreeHost(host_candidates);
    }
};

std::size_t scratch_for(const Image& image, const Config& config) {
    std::size_t bytes = 0;
    require_status(v5_image_scratch_bytes(image, config, bytes), ErrorCode::Success, "scratch size");
    require(bytes > 0 && bytes % 16 == 0, "scratch size is positive and 16-byte aligned");
    return bytes;
}

// Reset, H2D, S1 and the S2 candidate step: the part enqueued before the count wait.
ErrorCode enqueue_prefix(BranchStorage& branch, const Config& config, cudaStream_t stream) {
    ErrorCode status = v5_reset_image(branch.view, stream);
    if (status == ErrorCode::Success) status = v5_upload_image(branch.pinned, branch.view, stream);
    if (status == ErrorCode::Success) status = v5_preprocess_image(branch.view, config, stream);
    if (status == ErrorCode::Success) status = v5_detect_candidates(branch.view, config, stream);
    return status;
}

// S2 top-K and S3, valid only after the candidate count reached the host.
ErrorCode enqueue_suffix(BranchStorage& branch, const Config& config, cudaStream_t stream) {
    ErrorCode status = v5_finish_detect(branch.view, config, stream);
    if (status == ErrorCode::Success) status = v5_describe_image(branch.view, config, stream);
    return status;
}

Features read_branch(const BranchStorage& branch) {
    DeviceCounts counts;
    cuda(cudaMemcpy(&counts, branch.view.counts, sizeof(counts), cudaMemcpyDeviceToHost));
    Features out;
    out.gray = read_gray(branch.view.gray.data, branch.view.gray.width, branch.view.gray.height);
    out.keypoint_count = counts.keypointsA;
    out.descriptor_count = counts.descriptorsA;
    out.keypoints = read_array(branch.view.keypoints, counts.keypointsA);
    out.descriptors = read_array(branch.view.descriptors, counts.descriptorsA);
    out.status = counts.status;
    require(counts.keypointsB == 0 && counts.descriptorsB == 0 && counts.matches == 0,
            "branch leaves the B and match fields at zero");
    return out;
}

// A then B on one stream, the order the T02 task asks for.
void run_sequential(BranchStorage* branches[2], const Config& config, Features out[2]) {
    Stream stream;
    for (int i = 0; i < 2; ++i) {
        require_status(enqueue_prefix(*branches[i], config, stream.value), ErrorCode::Success, "prefix");
        stream.wait();
        require_status(enqueue_suffix(*branches[i], config, stream.value), ErrorCode::Success, "suffix");
        stream.wait();
        out[i] = read_branch(*branches[i]);
    }
}

// Both prefixes on their own streams before either count is read, as the dual schedule does.
void run_concurrent(BranchStorage* branches[2], const Config& config, Features out[2]) {
    Stream streams[2];
    for (int i = 0; i < 2; ++i) {
        require_status(enqueue_prefix(*branches[i], config, streams[i].value), ErrorCode::Success,
                       "concurrent prefix");
    }
    for (int i = 0; i < 2; ++i) streams[i].wait();
    for (int i = 0; i < 2; ++i) {
        require_status(enqueue_suffix(*branches[i], config, streams[i].value), ErrorCode::Success,
                       "concurrent suffix");
    }
    for (int i = 0; i < 2; ++i) streams[i].wait();
    for (int i = 0; i < 2; ++i) out[i] = read_branch(*branches[i]);
}

// ------------------------------------------------------------------ comparison

bool same_bits(const void* a, const void* b, std::size_t bytes) { return std::memcmp(a, b, bytes) == 0; }

void compare_features(const Features& expected, const Features& actual, const std::string& label) {
    require(actual.status == expected.status, label + ": status " + status_name(actual.status) +
                                                  " vs V4 " + status_name(expected.status));
    require(actual.gray.size() == expected.gray.size() &&
                same_bits(actual.gray.data(), expected.gray.data(), expected.gray.size() * sizeof(float)),
            label + ": S1 gray differs from V4");
    require(actual.keypoint_count == expected.keypoint_count,
            label + ": keypoint count " + std::to_string(actual.keypoint_count) + " vs V4 " +
                std::to_string(expected.keypoint_count));
    require(actual.descriptor_count == expected.descriptor_count, label + ": descriptor count differs");
    for (std::uint32_t i = 0; i < expected.keypoint_count; ++i) {
        require(same_bits(&actual.keypoints[i], &expected.keypoints[i], sizeof(Keypoint)),
                label + ": keypoint " + std::to_string(i) + " differs (order or value)");
    }
    for (std::uint32_t i = 0; i < expected.descriptor_count; ++i) {
        require(same_bits(&actual.descriptors[i], &expected.descriptors[i], sizeof(Descriptor)),
                label + ": descriptor " + std::to_string(i) + " differs");
    }
}

struct Totals {
    int cases = 0;
    std::uint64_t keypoints = 0;
    bool saw_empty = false, saw_capped = false;
};

void compare_pair(const Image& a, const Image& b, const Config& config, const std::string& name, Totals& totals) {
    Features expected[2];
    reference_features(a, b, config, expected);

    BranchStorage branch_a(a, config, scratch_for(a, config));
    BranchStorage branch_b(b, config, scratch_for(b, config));
    BranchStorage* branches[2] = {&branch_a, &branch_b};
    const char* sides[2] = {" A", " B"};

    Features actual[2];
    for (int round = 0; round < 3; ++round) {  // Reruns on the same storage check the reset.
        run_sequential(branches, config, actual);
        for (int i = 0; i < 2; ++i) {
            compare_features(expected[i], actual[i], name + sides[i] + " sequential run " + std::to_string(round + 1));
        }
    }
    run_concurrent(branches, config, actual);
    for (int i = 0; i < 2; ++i) compare_features(expected[i], actual[i], name + sides[i] + " two streams");

    for (int i = 0; i < 2; ++i) {
        totals.keypoints += expected[i].keypoint_count;
        totals.saw_empty |= expected[i].keypoint_count == 0;
        totals.saw_capped |= *branches[i]->host_candidates > static_cast<std::uint32_t>(config.max_keypoints);
    }
    ++totals.cases;
    std::cout << name << ": keypoints A=" << expected[0].keypoint_count << " B=" << expected[1].keypoint_count
              << ", identical to V4 in 3 sequential runs and on two streams\n";
}

void test_parity(const Options& options, Totals& totals) {
    const auto scene = make_test_image(760, 560, 2026);
    const auto a = crop(scene, 640, 480, 20, 20);
    const auto b = crop(scene, 640, 480, 56, 34);
    const Config config = fixture_config(a.view());
    compare_pair(a.view(), b.view(), config, "synthetic 640x480", totals);

    const auto small_b = crop(scene, 320, 240, 200, 120);  // A and B of different sizes.
    compare_pair(a.view(), small_b.view(), config, "different sizes 640x480 + 320x240", totals);

    Config capped = config;
    capped.max_keypoints = 50;  // Fewer slots than candidates: top-K must cut identically.
    compare_pair(a.view(), b.view(), capped, "max_keypoints=50", totals);

    auto tiny_a = make_test_image(24, 24, 1);  // No candidate region inside the FAST border.
    auto tiny_b = make_test_image(24, 24, 2);
    compare_pair(tiny_a.view(), tiny_b.view(), fixture_config(tiny_a.view()), "tiny 24x24", totals);

    auto blank = make_test_image(160, 120, 3);  // Flat image: region exists but no corner.
    std::fill(blank.bytes.begin(), blank.bytes.end(), 128);
    compare_pair(blank.view(), blank.view(), fixture_config(blank.view()), "blank 160x120", totals);

    if (options.dataset.empty()) return;
    for (const std::string site : {"site1", "site2", "site3", "challenge"}) {
        for (const std::string size : {"small", "medium", "large"}) {
            const std::string prefix = options.dataset + "/" + site + "/" + size;
            RgbImage left, right;
            require(load_rgb_image((prefix + "_left.jpg").c_str(), left), "decode " + prefix + "_left.jpg");
            require(load_rgb_image((prefix + "_right.jpg").c_str(), right), "decode " + prefix + "_right.jpg");
            compare_pair(left.view(), right.view(), fixture_config(left.view()), site + "/" + size, totals);
        }
    }
}

// ------------------------------------------------------------------ host-side validation

void test_validation() {
    const auto image = make_test_image(160, 120, 7);
    const Config config = fixture_config(image.view());
    const std::size_t bytes = scratch_for(image.view(), config);
    Stream stream;

    {  // Scratch query rejects a bad Config like the stages do.
        Config bad = config;
        bad.fast_threshold = 0.0f;
        std::size_t unused = 0;
        require_status(v5_image_scratch_bytes(image.view(), bad, unused), ErrorCode::InvalidConfig,
                       "scratch query with fast_threshold=0");
        bad = config;
        bad.max_keypoints = kMaxKeypointsLimit + 1;
        require_status(v5_image_scratch_bytes(image.view(), bad, unused), ErrorCode::InvalidConfig,
                       "scratch query above kMaxKeypointsLimit");
    }
    {  // Feature arrays smaller than max_keypoints would let top-K write past their end.
        BranchStorage branch(image.view(), config, bytes);
        branch.view.feature_capacity = static_cast<std::size_t>(config.max_keypoints) - 1;
        require_status(enqueue_prefix(branch, config, stream.value), ErrorCode::Success, "capacity prefix");
        stream.wait();
        require_status(v5_finish_detect(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "finish_detect with feature_capacity < max_keypoints");
        require_status(v5_describe_image(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "describe with feature_capacity < max_keypoints");
    }
    {  // A scratch view shorter than the layout of a stage.
        BranchStorage branch(image.view(), config, bytes);
        branch.view.scratch_bytes = 16;
        require_status(v5_reset_image(branch.view, stream.value), ErrorCode::Success, "short scratch reset");
        require_status(v5_upload_image(branch.pinned, branch.view, stream.value), ErrorCode::Success,
                       "short scratch upload");
        require_status(v5_preprocess_image(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "preprocess with short scratch");
        require_status(v5_detect_candidates(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "detect_candidates with short scratch");
        *branch.host_candidates = 0;
        require_status(v5_finish_detect(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "finish_detect with short scratch");
        require_status(v5_describe_image(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "describe with short scratch");
        stream.wait();
    }
    {  // Scratch that is not 16-byte aligned.
        BranchStorage branch(image.view(), config, bytes);
        branch.view.scratch += 4;
        branch.view.scratch_bytes -= 16;
        require_status(v5_preprocess_image(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "preprocess with misaligned scratch");
        require_status(v5_detect_candidates(branch.view, config, stream.value), ErrorCode::InvalidArgument,
                       "detect_candidates with misaligned scratch");
    }
    {  // Upload strides shorter than one RGB row.
        BranchStorage branch(image.view(), config, bytes);
        Image short_source = branch.pinned;
        short_source.stride = static_cast<std::size_t>(image.width) * 3 - 1;
        require_status(v5_upload_image(short_source, branch.view, stream.value), ErrorCode::InvalidImage,
                       "upload with short source stride");
        branch.view.image.stride = static_cast<std::size_t>(image.width) * 3 - 1;
        require_status(v5_upload_image(branch.pinned, branch.view, stream.value), ErrorCode::InvalidImage,
                       "upload with short device stride");
    }
    {  // Gray view of another size than the RGB view.
        BranchStorage branch(image.view(), config, bytes);
        branch.view.gray.width -= 1;
        require_status(v5_preprocess_image(branch.view, config, stream.value), ErrorCode::InvalidImage,
                       "preprocess with mismatched gray size");
    }
    {  // Config checked by the S2 steps, as v1_detect does.
        BranchStorage branch(image.view(), config, bytes);
        Config bad = config;
        bad.fast_threshold = 1.5f;
        require_status(v5_detect_candidates(branch.view, bad, stream.value), ErrorCode::InvalidConfig,
                       "detect_candidates with fast_threshold=1.5");
        bad = config;
        bad.max_keypoints = 0;
        *branch.host_candidates = 0;
        require_status(v5_finish_detect(branch.view, bad, stream.value), ErrorCode::InvalidConfig,
                       "finish_detect with max_keypoints=0");
    }
    stream.wait();
    std::cout << "host-side validation: invalid capacity, scratch, alignment, stride, gray size and Config rejected\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv, "--require-v5-image-branch");
        gpu_test::print_gpu();
        require_status(v5_initialize_features(fixture_config(make_test_image(64, 64, 1).view()), nullptr),
                       ErrorCode::Success, "v5_initialize_features");
        Totals totals;
        test_parity(options, totals);
        require(totals.saw_empty, "no case produced zero keypoints");
        require(totals.saw_capped, "no case had more candidates than max_keypoints");
        test_validation();
        std::cout << "PASS GPU V5 image branch: " << gpu_test::checks() << " checks, " << totals.cases
                  << " pairs, " << totals.keypoints << " V4 keypoints compared\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL GPU V5 image branch: " << error.what() << '\n';
        return 1;
    }
}
