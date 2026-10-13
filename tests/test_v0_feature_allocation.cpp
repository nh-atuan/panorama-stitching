// Authors: Le Thuong De (23120232)
// External source: none

#include "feature_config.h"
#include "v0_match.h"
#include "v0_homography.h"
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>

// Dedicated fault-injection binary: Windows ASan owns these same operators.
// Keep this test separate so sanitizer builds and allocation-failure tests both run.
static int allocations_before_failure=-1;
void* operator new(std::size_t bytes) {
    if (allocations_before_failure==0) {
        allocations_before_failure=-1;
        throw std::bad_alloc();
    }
    if (allocations_before_failure>0) --allocations_before_failure;
    void* pointer=std::malloc(bytes ? bytes : 1);
    if (!pointer) throw std::bad_alloc();
    return pointer;
}
void operator delete(void* pointer) noexcept {std::free(pointer);}

using namespace panorama;
namespace {
int checks=0;
void require(bool condition,const char* message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}
template <typename T>
FeatureView<T> view(const std::vector<T>& values) {
    return FeatureView<T>(values.data(),static_cast<std::int32_t>(values.size()),values.size());
}
void test_failures() {
    Config config;
    require(configure_v0_features(config,1920,1080)==ErrorCode::Success,"config");
    std::vector<Descriptor> descriptors_a(4),descriptors_b(2);
    for (int word=0;word<8;++word) descriptors_b[1].data[word]=0xffffffffu;
    std::vector<Match> output_matches(1);
    allocations_before_failure=0;
    const ErrorCode match_status=v0_match(view(descriptors_a),view(descriptors_b),output_matches,config);
    allocations_before_failure=-1;
    require(match_status==ErrorCode::AllocationFailed,"matching allocation error");
    require(output_matches.empty(),"matching output cleared");
    std::vector<Keypoint> a(4),b(4);
    std::vector<Match> matches(4);
    for (int i=0;i<4;++i) {
        b[i].x=static_cast<float>(30*(i%2));b[i].y=static_cast<float>(20*(i/2));
        a[i]=b[i];a[i].x+=8.0f;
        matches[i].indexA=i;matches[i].indexB=i;
    }
    int failures=0;
    bool reached_success=false;
    for (int failure_point=0;failure_point<32;++failure_point) {
        Homography h;h.data[0]=1.0f;
        HomographyReport report;
        allocations_before_failure=failure_point;
        const ErrorCode status=v0_homography(view(a),view(b),view(matches),h,config,&report);
        allocations_before_failure=-1;
        if (status==ErrorCode::Success) {reached_success=true;break;}
        require(status==ErrorCode::AllocationFailed,"homography allocation error at each phase");
        require(!report.success && report.inlier_mask.empty(),"no partial successful mask");
        for (float value:h.data) require(value==0.0f,"failed H remains invalid");
        ++failures;
    }
    require(reached_success && failures>=5,"exercise allocations through sampling/fit/refit phases");
}
}  // namespace
int main() {
    try {
        test_failures();
        std::cout<<"PASS allocation: "<<checks<<" checks; S4/S5 transactional cleanup\n";
        return 0;
    } catch(const std::exception& error) {
        allocations_before_failure=-1;
        std::cerr<<"FAIL allocation: "<<error.what()<<'\n';return 1;
    }
}
