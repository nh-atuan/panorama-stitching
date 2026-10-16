// Authors: Le Thuong De (23120232)
// External source: none

#include "feature_support.h"
#include "v0_homography.h"
#include "v0_match.h"
#include "v0_warp_blend.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <new>
#include <sstream>
#include <stdexcept>

using namespace panorama;
namespace {
int checks=0;
using Matrix=std::array<double,9>;
void require(bool condition,const char* message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}
template <typename T>
FeatureView<T> view(const std::vector<T>& values) {
    return FeatureView<T>(values.data(),static_cast<std::int32_t>(values.size()),values.size());
}
Config settings() {
    Config config;
    require(configure_v0_features(config,1920,1080)==ErrorCode::Success,"config");
    config.max_canvas_pixels=100000000;
    return config;
}
Keypoint analytic_projection(const Matrix& h,const Keypoint& b) {
    Keypoint a;
    const double w=h[6]*b.x+h[7]*b.y+h[8];
    a.x=static_cast<float>((h[0]*b.x+h[1]*b.y+h[2])/w);
    a.y=static_cast<float>((h[3]*b.x+h[4]*b.y+h[5])/w);
    return a;
}
struct Fixture {
    std::vector<Keypoint> a,b;
    std::vector<Match> matches;
    Fixture(const Matrix& h,int columns=8,int rows=8,double noise=0.0,bool outliers=false) {
        for (int y=0;y<rows;++y) for (int x=0;x<columns;++x) {
            const int i=static_cast<int>(a.size());
            Keypoint source;
            source.x=static_cast<float>(10+71*x);
            source.y=static_cast<float>(20+53*y);
            Keypoint target=analytic_projection(h,source);
            target.x+=static_cast<float>(noise*std::sin(1.7*i));
            target.y+=static_cast<float>(noise*std::cos(0.9*i));
            if (outliers && i%4==0) {target.x+=static_cast<float>(80+0.27*i);target.y-=150;}
            a.push_back(target);b.push_back(source);
            Match match;match.indexA=i;match.indexB=i;matches.push_back(match);
        }
    }
    ErrorCode estimate(Homography& h,HomographyReport* report=nullptr,const Config* cfg=nullptr) {
        const Config config=cfg ? *cfg : settings();
        return v0_homography(view(a),view(b),view(matches),h,config,report);
    }
};
double held_out_error(const Matrix& truth,const Homography& estimate) {
    double worst=0.0;
    Matrix actual;
    for (int i=0;i<9;++i) actual[i]=estimate.data[i];
    for (int y=0;y<6;++y) for (int x=0;x<6;++x) {
        Keypoint b;b.x=static_cast<float>(32+69*x);b.y=static_cast<float>(42+50*y);
        const Keypoint expected=analytic_projection(truth,b),projected=analytic_projection(actual,b);
        worst=std::max(worst,std::hypot(static_cast<double>(expected.x-projected.x),
                                       static_cast<double>(expected.y-projected.y)));
    }
    return worst;
}
bool invalid_h(const Homography& h) {
    for(float value:h.data) if(value!=0.0f) return false;
    return true;
}
void test_models_and_robustness() {
    const Matrix models[]={
        {{1,0,0,0,1,0,0,0,1}},{{1,0,20,0,1,-8,0,0,1}},
        {{1.04,0.02,14,-0.01,0.97,6,0.0002,-0.0001,1}},
        {{1,0.1,20,0.2,1,10,0.01,0.02,0}}
    };
    for (const Matrix& model:models) {
        Fixture fixture(model);
        Homography h;HomographyReport report;
        require(fixture.estimate(h,&report)==ErrorCode::Success,"noiseless stage");
        require(report.success && report.final_inliers==64,"all noiseless inliers");
        require(held_out_error(model,h)<0.001,"independent held-out B->A mapping");
        require(report.attempts<=2000 && report.refit_passes>=1 && report.refit_passes<=2,
                "bounded attempts and refits");
    }
    Fixture minimal(models[2],2,2);
    Homography minimal_h;HomographyReport minimal_report;
    require(minimal.estimate(minimal_h,&minimal_report)==ErrorCode::Success,"four-pair stage");
    require(minimal_report.attempts==1 && minimal_report.adaptive_budget==1,"all-inlier adaptive stop");
    Fixture robust(models[2],8,12,0.15,true);
    Homography first,second;HomographyReport a,b;
    require(robust.estimate(first,&a)==ErrorCode::Success,"noisy/outlier stage");
    require(a.final_inliers==72,"known true correspondence count");
    require(held_out_error(models[2],first)<0.10,"robust held-out map");
    for (std::size_t i=0;i<a.inlier_mask.size();++i)
        require(a.inlier_mask[i]==(i%4!=0 ? 1 : 0),"ground-truth outlier labels");
    require(robust.estimate(second,&b)==ErrorCode::Success,"repeat stage");
    for (int i=0;i<9;++i)
        require(std::memcmp(&first.data[i],&second.data[i],sizeof(float))==0,"bit-identical repeat H");
    require(a.sample_hash==b.sample_hash && a.best_hypothesis==b.best_hypothesis &&
            a.attempts==b.attempts && a.inlier_mask==b.inlier_mask && a.final_loss==b.final_loss,
            "repeat diagnostics");
    std::ostringstream log;
    write_homography_report(log,a);
    require(log.str().find("seed=16")!=std::string::npos,"seed exposed outside stage timing");
    write_homography_report(std::cout,a);
    const int widths[]={1280,3840},heights[]={720,2160};
    const double scales[]={2.0/3.0,2.0};
    for(int resolution=0;resolution<2;++resolution) {
        Fixture resized=robust;
        const float scale=static_cast<float>(scales[resolution]);
        for(std::size_t i=0;i<resized.a.size();++i) {
            resized.a[i].x*=scale;resized.a[i].y*=scale;
            resized.b[i].x*=scale;resized.b[i].y*=scale;
        }
        Config config;
        require(configure_v0_features(config,widths[resolution],heights[resolution])==
                ErrorCode::Success,"scaled config");
        Homography scaled_h;HomographyReport scaled_report;
        require(resized.estimate(scaled_h,&scaled_report,&config)==ErrorCode::Success,
                "scaled scene estimation");
        require(scaled_report.inlier_mask==a.inlier_mask,"resolution-scaled inlier decisions");
    }
    Fixture reclassify(models[2],11,11,2.0,false);
    Homography noisy;HomographyReport report;
    require(reclassify.estimate(noisy,&report)==ErrorCode::Success,"noisy refit stage");
    require(report.refit_passes==2,"changed mask triggers exactly one extra refit");
    require(held_out_error(models[2],noisy)<1.5,"held-out noisy refit map");
}
void test_failures() {
    const Matrix identity={{1,0,0,0,1,0,0,0,1}};
    Fixture fixture(identity,2,2);
    Config config=settings();Homography h;HomographyReport report;
    fixture.matches.resize(3);
    require(fixture.estimate(h,&report,&config)==ErrorCode::InsufficientMatches,"three matches");
    require(invalid_h(h) && report.inlier_mask.empty(),"failed output invalid");
    fixture=Fixture(identity,2,2);
    fixture.matches[0].indexB=99;
    require(fixture.estimate(h,&report,&config)==ErrorCode::InvalidArgument,"out-of-range index");
    fixture.matches[0].indexB=0;fixture.matches[1].indexA=0;
    require(fixture.estimate(h,&report,&config)==ErrorCode::InvalidArgument,"non-increasing indexA");
    fixture.matches[1].indexA=1;fixture.matches[0].distance=257;
    require(fixture.estimate(h,&report,&config)==ErrorCode::InvalidArgument,"invalid Hamming metadata");
    fixture.matches[0].distance=0;
    fixture.a[0].x=std::numeric_limits<float>::quiet_NaN();
    require(fixture.estimate(h,&report,&config)==ErrorCode::NumericalFailure,"NaN coordinate");
    fixture.a[0].x=std::numeric_limits<float>::infinity();
    require(fixture.estimate(h,&report,&config)==ErrorCode::NumericalFailure,"infinite coordinate");
    fixture=Fixture(identity,2,2);
    require(v0_homography(FeatureView<Keypoint>(nullptr,4,4),view(fixture.b),view(fixture.matches),
                          h,config,&report)==ErrorCode::InvalidArgument,"null view");
    require(v0_homography(FeatureView<Keypoint>(fixture.a.data(),4,3),view(fixture.b),
                          view(fixture.matches),h,config,&report)==ErrorCode::InvalidArgument,
            "invalid declared capacity");
    config.ransac_iters=0;
    require(fixture.estimate(h,&report,&config)==ErrorCode::InvalidConfig,"unset cap");
    config=settings();config.ransac_threshold=std::numeric_limits<float>::infinity();
    require(fixture.estimate(h,&report,&config)==ErrorCode::InvalidConfig,"non-finite threshold");
    config=settings();config.homography_epsilon=0;
    require(fixture.estimate(h,&report,&config)==ErrorCode::InvalidConfig,"unset epsilon");
    config=settings();
    for (std::size_t i=0;i<fixture.a.size();++i) {
        fixture.a[i].x=fixture.b[i].x=static_cast<float>(i);
        fixture.a[i].y=fixture.b[i].y=static_cast<float>(2*i);
    }
    require(fixture.estimate(h,&report,&config)==ErrorCode::DegenerateHomography,"all samples collinear");
    require(report.attempts==2000 && report.rejected_samples==2000 && !report.success,
            "degenerate attempts count toward cap");
    fixture=Fixture(identity,2,2);fixture.b[1]=fixture.b[0];
    require(fixture.estimate(h,&report,&config)==ErrorCode::DegenerateHomography,"duplicate B samples");
    require(invalid_h(h),"no identity fallback");
}
void test_s4_s5_s6_integration() {
    const std::uint32_t patterns[]={0u,0xffffffffu,0xaaaaaaaau,0x55555555u};
    const Matrix translation={{1,0,8,0,1,0,0,0,1}};
    Fixture fixture(translation,2,2);
    for(int i=0;i<4;++i) {
        fixture.b[i].x=static_cast<float>(2+28*(i%2));
        fixture.b[i].y=static_cast<float>(3+16*(i/2));
        fixture.a[i]=analytic_projection(translation,fixture.b[i]);
    }
    std::vector<Descriptor> a(4),b(4);
    for(int i=0;i<4;++i)
        for(int word=0;word<8;++word) a[i].data[word]=b[3-i].data[word]=patterns[i];
    std::reverse(fixture.b.begin(),fixture.b.end());
    Config config=settings();
    std::vector<Match> matches;
    require(v0_match(view(a),view(b),matches,config)==ErrorCode::Success,"S4 integration");
    Homography h;
    require(v0_homography(view(fixture.a),view(fixture.b),view(matches),h,config)==
            ErrorCode::Success,"S5 integration");
    std::vector<std::uint8_t> left(64*32*3,40),right(64*32*3,200);
    Image image_a,image_b;
    image_a.data=left.data();image_b.data=right.data();
    image_a.width=image_b.width=64;image_a.height=image_b.height=32;
    image_a.channels=image_b.channels=3;image_a.stride=image_b.stride=64*3;
    struct Output {Panorama p;~Output(){delete[] p.image.data;}} output;
    require(v0_warp_blend(image_a,image_b,h,output.p,config)==ErrorCode::Success,"S6 integration");
    require(output.p.image.width==72 && output.p.image.height==32,"translated panorama bounds");
    require(output.p.image.data[0]==40,"A-only region");
    require(output.p.image.data[8*3]==120,"overlap average");
    require(output.p.image.data[71*3]==200,"B-only region");
}
}  // namespace
int main() {
    try {
        test_models_and_robustness();test_failures();test_s4_s5_s6_integration();
        std::cout<<"PASS S5: "<<checks<<" checks; seed=16 sampler=uniform scorer=MSAC\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"FAIL S5: "<<error.what()<<'\n';return 1;
    }
}
