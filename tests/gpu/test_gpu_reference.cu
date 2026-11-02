// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// Smoke suite of the GPU test helpers: V0 data must survive a Device round trip, and a
// difference made on the Device must be reported. Usage: gpu_reference [<left> <right>].

#include "gpu/s45_test_support.cuh"
#include "support/gpu_compare.h"
#include "support/v0_reference.h"

using namespace panorama;
using namespace gpu_test;

namespace {

__global__ void flip_descriptor_bit(Descriptor* descriptors, std::size_t index) {
    descriptors[index].data[0] ^= 1u;
}

template <class T>
std::vector<T> round_trip(const std::vector<T>& values) {
    DeviceBuffer<T> buffer(values.size());
    buffer.upload(values);
    return buffer.read(values.size());
}

void check_round_trip(RgbImage& image, const Config& config) {
    V0Features features;
    require(compute_v0_features(image.view(), config, features) == ErrorCode::Success, "V0 S1 to S3");
    const std::string gray = float_array_mismatch(features.gray_pixels, round_trip(features.gray_pixels));
    const std::string keypoints = keypoint_mismatch(features.keypoints, round_trip(features.keypoints));
    const std::string descriptors = descriptor_mismatch(features.descriptors, round_trip(features.descriptors));
    require(gray.empty(), "gray round trip " + gray);
    require(keypoints.empty(), "keypoint round trip " + keypoints);
    require(descriptors.empty(), "descriptor round trip " + descriptors);
}

void check_kernel_difference_is_reported() {
    RgbImage image = make_test_image(160, 120, 16);
    Config config;
    require(make_v0_config(image.width, image.height, config) == ErrorCode::Success, "config");
    V0Features features;
    require(compute_v0_features(image.view(), config, features) == ErrorCode::Success, "V0 S1 to S3");
    require(!features.descriptors.empty(), "test image has descriptors");

    DeviceBuffer<Descriptor> buffer(features.descriptors.size());
    buffer.upload(features.descriptors);
    Stream stream;
    flip_descriptor_bit<<<1, 1, 0, stream.value>>>(buffer.data, 0);
    cuda(cudaGetLastError());
    stream.wait();
    const std::string message = descriptor_mismatch(features.descriptors, buffer.read(buffer.count));
    require(message.find("[0].data[0]") != std::string::npos, "kernel change is reported: " + message);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 1 && argc != 3) throw std::runtime_error("Usage: gpu_reference [<left> <right>]");
        print_gpu();
        check_kernel_difference_is_reported();
        RgbImage missing;
        require(!load_rgb_image("tests/gpu/no_such_image.jpg", missing), "missing file is reported");
        require(missing.bytes.empty(), "missing file leaves the image empty");
        for (int i = 0; i < 2; ++i) {
            RgbImage image = make_test_image(320, 240, 16u + i);
            if (argc == 3) require(load_rgb_image(argv[i + 1], image), "cannot read input image");
            Config config;
            require(make_v0_config(image.width, image.height, config) == ErrorCode::Success, "config");
            check_round_trip(image, config);
        }
        std::cout << "PASS GPU reference: " << checks() << " checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
