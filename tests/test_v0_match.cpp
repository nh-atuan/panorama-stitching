// Authors: Le Thuong De (23120232)
// External source: none

#include "feature_config.h"
#include "v0_match.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

using namespace panorama;
namespace {
int checks = 0;
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}
template <typename T>
FeatureView<T> view(const std::vector<T>& values) {
    return FeatureView<T>(values.data(), static_cast<std::int32_t>(values.size()), values.size());
}
Config settings() {
    Config config;
    require(configure_v0_features(config, 1920, 1080) == ErrorCode::Success, "config");
    return config;
}
Descriptor repeated(std::uint32_t word) {
    Descriptor result;
    for (int i = 0; i < 8; ++i) result.data[i] = word;
    return result;
}
void test_unique_and_non_mutual() {
    const std::uint32_t patterns[] = {0u, 0xffffffffu, 0xaaaaaaaau, 0x55555555u};
    std::vector<Descriptor> a, b;
    for (int i = 0; i < 4; ++i) a.push_back(repeated(patterns[i]));
    b = a;
    std::reverse(b.begin(), b.end());
    a.push_back(a[0]);  // The same B is a valid nearest neighbor for two A points.
    std::vector<Match> output;
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::Success, "matching");
    require(output.size() == 5, "no implicit mutual/uniqueness filter");
    for (int i = 0; i < 5; ++i) {
        require(output[i].indexA == i, "output order");
        require(output[i].indexB == (i < 4 ? 3-i : 3), "permuted correspondence");
        require(output[i].distance == 0, "identical descriptors");
    }
    a[4].data[7] ^= 1u << 31;
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::Success, "one-bit match");
    require(output[4].distance == 1, "bit 255 Hamming");
    const Config config=settings();
    for(int count=1;count<=3;++count) {
        require(v0_match(FeatureView<Descriptor>(a.data(),count,a.size()),view(b),output,config)==
                ErrorCode::InsufficientMatches,"one to three valid matches insufficient");
        require(output.empty(),"partial match output not published");
    }
}
void test_ratio_and_ties() {
    std::vector<Descriptor> a(4), b(2);
    std::vector<Match> output;
    b[0].data[0] = 0x7fu;  // 7 changed bits.
    b[1].data[0] = 0x3ffu; // 10 changed bits.
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::Success, "7/10 passes");
    require(output[0].distance == 7, "known Hamming distance");
    b[0].data[0] = 0xffu;
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::InsufficientMatches,
            "8/10 boundary rejected");
    require(output.empty(), "failure clears previous output");
    b[0].data[0] = 0x1ffu;
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::InsufficientMatches,
            "9/10 rejected");
    b[0] = b[1];
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::InsufficientMatches,
            "equal nonzero neighbors ambiguous");
    b.assign(2, Descriptor());
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::InsufficientMatches,
            "two zero-distance neighbors ambiguous");
    b.assign(2, repeated(0xffffffffu));
    require(v0_match(view(a), view(b), output, settings()) == ErrorCode::InsufficientMatches,
            "distance 256 ties are ambiguous");
}
void test_validation_and_config() {
    std::vector<Descriptor> a(4), b(2);
    std::vector<Match> output(1);
    Config config = settings();
    require(v0_match(FeatureView<Descriptor>(nullptr,4,4), view(b), output, config) ==
            ErrorCode::InvalidArgument, "null input");
    require(output.empty(), "null failure output");
    require(v0_match(FeatureView<Descriptor>(a.data(),4,3), view(b), output, config) ==
            ErrorCode::InvalidArgument, "insufficient declared capacity");
    require(v0_match(FeatureView<Descriptor>(a.data(),-1,4), view(b), output, config) ==
            ErrorCode::InvalidArgument, "negative count");
    require(v0_match(FeatureView<Descriptor>(), view(b), output, config) ==
            ErrorCode::InsufficientKeypoints, "empty A");
    b.resize(1);
    require(v0_match(view(a), view(b), output, config) == ErrorCode::InsufficientKeypoints,
            "single candidate has no second neighbor");
    config.match_cross_check = 1;
    require(v0_match(view(a), view(b), output, config) == ErrorCode::InvalidConfig,
            "cross-check alternative rejected");
    config.match_cross_check = 0;
    const float invalid[] = {0.0f,1.0f,0.75f,std::numeric_limits<float>::quiet_NaN(),
                             std::numeric_limits<float>::infinity()};
    for (float ratio : invalid) {
        config.match_ratio_threshold = ratio;
        require(v0_match(view(a), view(b), output, config) == ErrorCode::InvalidConfig,
                "invalid/frozen ratio");
    }
    config = Config();
    config.max_canvas_pixels = 12345;
    const int widths[] = {1280,1920,3840};
    const int heights[] = {720,1080,2160};
    for (int i = 0; i < 3; ++i) {
        require(configure_v0_features(config,widths[i],heights[i]) == ErrorCode::Success,
                "resolution config");
        require(config.ransac_threshold == 2.0f * (i == 0 ? 1.0f : i == 1 ? 1.5f : 3.0f),
                "threshold 2/3/6 px");
        require(config.max_canvas_pixels == 12345, "preserve other owner config");
    }
    const float previous = config.ransac_threshold;
    require(configure_v0_features(config,0,1080) == ErrorCode::InvalidArgument,
            "invalid image dimensions");
    require(config.ransac_threshold == previous, "transactional config");
}
}  // namespace

int main() {
    try {
        test_unique_and_non_mutual();
        test_ratio_and_ties();
        test_validation_and_config();
        std::cout << "PASS S4: " << checks << " checks; ratio=0.80 cross_check=0 seed=16\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL S4: " << error.what() << '\n';
        return 1;
    }
}
