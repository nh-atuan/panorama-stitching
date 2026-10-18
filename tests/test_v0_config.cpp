// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// make_v0_config fills every field with the values of the stage documents, and the
// result is accepted by the parameter checks of every stage.

#include "v0_config.h"
#include "feature_support.h"
#include "gaussian_kernel.h"
#include "feature_test_support.h"
#include <cmath>
#include <sstream>

using namespace panorama;

namespace {

void test_values_for_three_sizes() {
    const std::int32_t sizes[3][2] = {{1280, 720}, {1920, 1080}, {3840, 2160}};
    const float thresholds[3] = {2.0f, 3.0f, 6.0f};  // 3 px at 1920x1080, scaled by diagonal
    for (int i = 0; i < 3; ++i) {
        Config config;
        require(make_v0_config(sizes[i][0], sizes[i][1], config) == ErrorCode::Success, "config");
        require(config.gaussian_sigma == 1.0f && config.gaussian_radius == 3, "S1 values");
        require(config.fast_threshold == 0.05f && config.max_keypoints == 2000, "S2 values");
        require(config.match_ratio_threshold == feature_policy::kRatio &&
                    config.match_cross_check == 0u, "S4 values");
        require(config.ransac_iters == feature_policy::kMaxIterations &&
                    config.seed == feature_policy::kSeed, "S5 iterations and seed");
        require(std::fabs(config.ransac_threshold - thresholds[i]) < 1e-5f, "S5 threshold");
        require(config.homography_epsilon == 1e-6f, "shared H epsilon");
        require(config.max_canvas_pixels == 100000000ULL, "S6 canvas limit");
        float weights[2 * kMaxGaussianRadius + 1];
        require(make_gaussian_weights(config.gaussian_sigma, config.gaussian_radius, weights) ==
                    ErrorCode::Success, "S1 accepts sigma and radius");
    }
}

void test_rejects_bad_size() {
    Config config;
    config.max_keypoints = 7;
    require(make_v0_config(0, 720, config) == ErrorCode::InvalidArgument, "zero width");
    require(make_v0_config(1280, -1, config) == ErrorCode::InvalidArgument, "negative height");
    require(config.max_keypoints == 7, "config unchanged on error");
}

void test_ignores_previous_content() {
    Config config;
    config.gaussian_sigma = 9.0f;
    config.homography_epsilon = 0.5f;
    config.match_cross_check = 1u;
    require(make_v0_config(1280, 720, config) == ErrorCode::Success, "config");
    require(config.gaussian_sigma == 1.0f && config.homography_epsilon == 1e-6f &&
                config.match_cross_check == 0u, "starts from a default Config");
}

void test_write_config() {
    Config config;
    require(make_v0_config(1920, 1080, config) == ErrorCode::Success, "config");
    std::ostringstream stream;
    write_config(stream, config);
    const std::string text = stream.str();
    require(text.find("seed=16") != std::string::npos, "seed is printed");
    require(text.find("max_keypoints=2000") != std::string::npos, "keypoint cap is printed");
    require(!text.empty() && text[text.size() - 1] == '\n', "one line");
}

}  // namespace

int main() {
    try {
        test_values_for_three_sizes();
        test_rejects_bad_size();
        test_ignores_previous_content();
        test_write_config();
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " assertions: " << error.what() << '\n';
        return 1;
    }
    std::cout << "PASS: " << checks << " assertions for the V0 configuration" << '\n';
    return 0;
}
