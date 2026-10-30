// Authors: Le Thuong De (23120232)
// External source: none
#include "gpu/s45_test_support.cuh"
#include "v1/s5/v1_homography.h"
#include "v0/v0_homography.h"
#include <cmath>
#include <iomanip>
#include <limits>
using namespace panorama;
using namespace gpu_test;
namespace {
struct Fixture {
    std::vector<Keypoint> a,b;
    std::vector<Match> matches;
    Config c;
    explicit Fixture(int n=56,bool outliers=true) {
        c.ransac_iters=2000;c.ransac_threshold=3.0f;c.homography_epsilon=1e-6f;c.seed=16;
        for(int i=0;i<n;++i) {
            Keypoint point;point.x=static_cast<float>((i%8)*53+11);point.y=static_cast<float>((i/8)*47+9);
            b.push_back(point);
            const double x=point.x,y=point.y,w=1.0+0.0001*x+0.0002*y;
            point.x=static_cast<float>((1.02*x+0.03*y+37)/w);
            point.y=static_cast<float>((-0.01*x+0.98*y+13)/w);
            // Fixed, labelled contamination; no dependency on the estimator mask.
            if(outliers && i%7==0){point.x+=150;point.y-=80;}
            a.push_back(point);
            Match m;m.indexA=i;m.indexB=i;m.distance=0;matches.push_back(m);
        }
    }
};
void compare(const Fixture& f,int batch) {
    DeviceBuffer<Keypoint> a(f.a.size()),b(f.b.size());a.upload(f.a);b.upload(f.b);
    DeviceBuffer<Match> matches(f.matches.size());matches.upload(f.matches);
    DeviceBuffer<DeviceCounts> counts(1);DeviceBuffer<Homography> output(1);
    DeviceBuffer<std::uint8_t> scratch(v1_homography_scratch_bytes(f.matches.size(),batch));
    DeviceCounts c;c.keypointsA=f.a.size();c.keypointsB=f.b.size();c.matches=f.matches.size();counts.upload({c});
    DeviceWorkspace w;w.d_keypointsA=a.data;w.d_keypointsB=b.data;w.d_matches=matches.data;
    w.d_counts=counts.data;w.d_homography=output.data;w.d_scratch=scratch.data;
    w.keypoint_capacityA=f.a.size();w.keypoint_capacityB=f.b.size();w.match_capacity=f.matches.size();
    w.scratch_capacity_bytes=scratch.count;
    Stream stream;
    require(v1_homography_with_batch_size(w,f.c,stream.value,batch)==ErrorCode::Success,"enqueue S5");
    stream.wait();
    Homography reference;HomographyReport expected;
    const ErrorCode status=v0_homography({f.a.data(),static_cast<int>(f.a.size()),f.a.size()},
        {f.b.data(),static_cast<int>(f.b.size()),f.b.size()},
        {f.matches.data(),static_cast<int>(f.matches.size()),f.matches.size()},reference,f.c,&expected);
    const auto actual_status=counts.read(1)[0].status;
    require(actual_status==status,"S5 error parity");
    V1HomographyDiagnostics actual;
    cuda(cudaMemcpy(&actual,v1_homography_diagnostics(w),sizeof(actual),cudaMemcpyDeviceToHost));
    require(actual.attempts==expected.attempts,"same logical prefix");
    require(actual.sample_hash==expected.sample_hash,"same ordered samples");
    require(actual.best_hypothesis==expected.best_hypothesis,"same best hypothesis");
    require(actual.valid_hypotheses==expected.valid_hypotheses,"same valid hypotheses");
    require(actual.rejected_samples==expected.rejected_samples,"same rejected samples");
    require(actual.adaptive_budget==expected.adaptive_budget,"same adaptive budget");
    require(actual.computed_hypotheses>=actual.attempts && actual.computed_hypotheses<=f.c.ransac_iters,"computed/logical attempts");
    const Homography h=output.read(1)[0];
    if(status==ErrorCode::Success) {
        require(actual.refit_passes==expected.refit_passes,"same refit policy");
        require(actual.final_inliers==expected.final_inliers,"same final count");
        std::vector<std::uint8_t> mask(f.matches.size());
        cuda(cudaMemcpy(mask.data(),v1_homography_inlier_mask(w,batch),mask.size(),cudaMemcpyDeviceToHost));
        require(mask==expected.inlier_mask,"same final mask");
        double maximum=0;
        for(int y=0;y<5;++y)for(int x=0;x<5;++x) {
            const double bx=x*100.0,by=y*90.0;
            const double wa=h.data[6]*bx+h.data[7]*by+h.data[8];
            const double wr=reference.data[6]*bx+reference.data[7]*by+reference.data[8];
            const double dx=(h.data[0]*bx+h.data[1]*by+h.data[2])/wa-
                            (reference.data[0]*bx+reference.data[1]*by+reference.data[2])/wr;
            const double dy=(h.data[3]*bx+h.data[4]*by+h.data[5])/wa-
                            (reference.data[3]*bx+reference.data[4]*by+reference.data[5])/wr;
            maximum=std::max(maximum,std::hypot(dx,dy));
            // Existing ground-truth bound is stricter than a coefficient comparison.
            const double gt_w=1.0+0.0001*bx+0.0002*by;
            require(std::hypot((h.data[0]*bx+h.data[1]*by+h.data[2])/wa-(1.02*bx+0.03*by+37)/gt_w,
                              (h.data[3]*bx+h.data[4]*by+h.data[5])/wa-(-0.01*bx+0.98*by+13)/gt_w)<=1.0,
                    "ground truth projection bound");
        }
        std::cout<<"S5 batch="<<batch<<" prefix="<<actual.attempts<<" computed="<<actual.computed_hypotheses
                 <<" max_cpu_gpu_px="<<std::setprecision(12)<<maximum<<'\n';
        // Float32 publication should be exact for these well-separated fixtures.
        for(int i=0;i<9;++i)require(h.data[i]==reference.data[i],"float H fixture parity");
    } else for(float value:h.data)require(value==0.0f,"no successful H on error");
    Config bad=f.c;bad.ransac_iters=0;
    require(v1_homography(w,bad,stream.value)==ErrorCode::InvalidConfig,"invalid cap");
    w.scratch_capacity_bytes=0;
    require(v1_homography_with_batch_size(w,f.c,stream.value,batch)==ErrorCode::AllocationFailed,"short S5 scratch");
}
}
int main() {
    try {
        print_gpu();cuda(cudaDeviceSetLimit(cudaLimitStackSize,32768));
        for(int batch:{1,7,32}){compare(Fixture(),batch);compare(Fixture(56,false),batch);}
        compare(Fixture(3,false),7);
        Fixture minimal(4,false);
        minimal.b[2].x=11;minimal.b[2].y=56;minimal.b[3].x=64;minimal.b[3].y=56;
        for(int i=0;i<4;++i) {
            const double x=minimal.b[i].x,y=minimal.b[i].y,w=1+0.0001*x+0.0002*y;
            minimal.a[i].x=(1.02*x+0.03*y+37)/w;minimal.a[i].y=(-0.01*x+0.98*y+13)/w;
        }
        compare(minimal,7);
        Fixture bad;bad.matches[1].indexA=bad.matches[0].indexA;compare(bad,7);
        bad=Fixture();bad.matches[0].indexB=-1;compare(bad,7);
        bad=Fixture();bad.a[0].x=std::numeric_limits<float>::quiet_NaN();compare(bad,7);
        Fixture line(8,false);for(int i=0;i<8;++i){line.a[i].y=0;line.b[i].y=0;}compare(line,32);
        require(v1_homography_scratch_bytes(SIZE_MAX)==0,"S5 scratch overflow");
        std::cout<<"PASS GPU S5: "<<checks()<<" checks\n";return 0;
    } catch(const std::exception& e){std::cerr<<"FAIL GPU S5: "<<e.what()<<'\n';return 1;}
}
