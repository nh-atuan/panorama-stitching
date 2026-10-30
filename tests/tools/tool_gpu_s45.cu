// Authors: Le Thuong De (23120232)
// External source: none
// Stage verification driver: V0 S1-S3/S6, selected version of S4-S5.
#include "common/common.h"
#include "common/cuda_utils.cuh"
#include "common/stb_image.h"
#include "common/stb_image_write.h"
#include "common/v0_config.h"
#include "v0/v0_pipeline.h"
#include "v0/v0_preprocess.h"
#include "v0/v0_detect.h"
#include "v0/v0_describe.h"
#include "v0/v0_match.h"
#include "v0/v0_warp_blend.h"
#include "v1/s4/v1_match.h"
#include "v1/s5/v1_homography.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <memory>
#include <stdexcept>
#include <string>
using namespace panorama;
namespace {
void check(ErrorCode status) {
    if(status!=ErrorCode::Success)throw std::runtime_error("stage ErrorCode="+std::to_string(static_cast<unsigned>(status)));
}
template<class T> FeatureView<T> view(const std::vector<T>& v){return {v.data(),static_cast<int>(v.size()),v.size()};}
struct Inputs {
    std::unique_ptr<unsigned char,void(*)(void*)> pixels;
    Image image;
    explicit Inputs(const char* path):pixels(nullptr,stbi_image_free) {
        int channels=0;pixels.reset(stbi_load(path,&image.width,&image.height,&channels,3));
        if(!pixels)throw std::runtime_error("cannot read input image");
        image.data=pixels.get();image.channels=3;image.stride=static_cast<std::size_t>(image.width)*3;
    }
};
struct DeviceStages {
    DeviceWorkspace w;
    CudaStream stream;
    DeviceStages()=default;
    DeviceStages(const DeviceStages&)=delete;
    ~DeviceStages(){
        cudaStreamSynchronize(stream.get());
        device_free(w.d_keypointsA);device_free(w.d_keypointsB);
        device_free(w.d_descriptorsA);device_free(w.d_descriptorsB);
        device_free(w.d_matches);device_free(w.d_homography);device_free(w.d_counts);device_free(w.d_scratch);
    }
    template<class T> void copy(T*& p,const std::vector<T>& v) {
        device_allocate(p,std::max<std::size_t>(1,v.size()));
        if(!v.empty())CUDA_CHECK(cudaMemcpy(p,v.data(),v.size()*sizeof(T),cudaMemcpyHostToDevice));
    }
    void prepare(const V0Workspace& host) {
        copy(w.d_keypointsA,host.keypoints_a);copy(w.d_keypointsB,host.keypoints_b);
        copy(w.d_descriptorsA,host.descriptors_a);copy(w.d_descriptorsB,host.descriptors_b);
        w.keypoint_capacityA=host.keypoints_a.size();w.keypoint_capacityB=host.keypoints_b.size();
        w.descriptor_capacityA=host.descriptors_a.size();w.descriptor_capacityB=host.descriptors_b.size();
        w.match_capacity=w.descriptor_capacityA;
        device_allocate(w.d_matches,std::max<std::size_t>(1,w.match_capacity));
        device_allocate(w.d_homography,1);device_allocate(w.d_counts,1);
        w.scratch_capacity_bytes=std::max(v1_match_scratch_bytes(w.descriptor_capacityA),
                                          v1_homography_scratch_bytes(w.match_capacity));
        device_allocate(w.d_scratch,w.scratch_capacity_bytes);
    }
    void run(V0Workspace& host,const Config& config,bool measured) {
        DeviceCounts counts;counts.keypointsA=w.keypoint_capacityA;counts.keypointsB=w.keypoint_capacityB;
        counts.descriptorsA=w.descriptor_capacityA;counts.descriptorsB=w.descriptor_capacityB;
        CUDA_CHECK(cudaMemcpyAsync(w.d_counts,&counts,sizeof(counts),cudaMemcpyHostToDevice,stream.get()));
        CudaEvent start,after_match,after_h;
        if(measured)start.record(stream.get());
        check(v1_match(w,config,stream.get()));
        if(measured)after_match.record(stream.get());
        check(v1_homography(w,config,stream.get()));
        if(measured)after_h.record(stream.get());
        CUDA_CHECK(cudaStreamSynchronize(stream.get()));
        CUDA_CHECK(cudaMemcpy(&counts,w.d_counts,sizeof(counts),cudaMemcpyDeviceToHost));check(counts.status);
        host.matches.resize(counts.matches);
        CUDA_CHECK(cudaMemcpy(host.matches.data(),w.d_matches,counts.matches*sizeof(Match),cudaMemcpyDeviceToHost));
        CUDA_CHECK(cudaMemcpy(&host.homography,w.d_homography,sizeof(Homography),cudaMemcpyDeviceToHost));
        if(measured)std::cout<<std::setprecision(9)<<after_match.elapsed_since(start)<<','<<after_h.elapsed_since(after_match)<<'\n';
    }
    void verify(const V0Workspace& host,const Config& config,int width_b,int height_b) {
        std::vector<Match> expected;
        check(v0_match(view(host.descriptors_a),view(host.descriptors_b),expected,config));
        if(expected.size()!=host.matches.size())throw std::runtime_error("S4 count parity failed");
        for(std::size_t i=0;i<expected.size();++i)
            if(expected[i].indexA!=host.matches[i].indexA || expected[i].indexB!=host.matches[i].indexB ||
               expected[i].distance!=host.matches[i].distance)throw std::runtime_error("S4 match parity failed");
        Homography h;HomographyReport cpu;
        check(v0_homography(view(host.keypoints_a),view(host.keypoints_b),view(expected),h,config,&cpu));
        V1HomographyDiagnostics gpu;
        CUDA_CHECK(cudaMemcpy(&gpu,v1_homography_diagnostics(w),sizeof(gpu),cudaMemcpyDeviceToHost));
        std::vector<std::uint8_t> mask(expected.size());
        CUDA_CHECK(cudaMemcpy(mask.data(),v1_homography_inlier_mask(w),mask.size(),cudaMemcpyDeviceToHost));
        if(gpu.attempts!=cpu.attempts || gpu.best_hypothesis!=cpu.best_hypothesis || gpu.sample_hash!=cpu.sample_hash ||
           gpu.adaptive_budget!=cpu.adaptive_budget || gpu.refit_passes!=cpu.refit_passes || mask!=cpu.inlier_mask)
            throw std::runtime_error("S5 prefix/model/mask parity failed");
        double squared=0.0,maximum=0.0;
        for(int row=0;row<20;++row)for(int column=0;column<20;++column) {
            const double x=static_cast<double>(width_b-1)*column/19.0;
            const double y=static_cast<double>(height_b-1)*row/19.0;
            const float* a=host.homography.data;const float* b=h.data;
            const double wa=(a[6]*x+a[7]*y)+a[8],wb=(b[6]*x+b[7]*y)+b[8];
            if(wa==0.0 || wb==0.0)throw std::runtime_error("invalid parity projection");
            const double dx=((a[0]*x+a[1]*y)+a[2])/wa-((b[0]*x+b[1]*y)+b[2])/wb;
            const double dy=((a[3]*x+a[4]*y)+a[5])/wa-((b[3]*x+b[4]*y)+b[5])/wb;
            const double error=std::hypot(dx,dy);
            if(!std::isfinite(error))throw std::runtime_error("nonfinite parity projection");
            squared+=error*error;maximum=std::max(maximum,error);
        }
        const double rmse=std::sqrt(squared/400.0);
        std::cerr<<std::setprecision(17)<<"S45 parity: matches=exact prefix=exact mask=exact h_rmse_px="<<rmse
                 <<" h_max_px="<<maximum<<'\n';
        // Stage owner approved these verification tolerances on 2026-10-31.
        if(rmse>0.0001 || maximum>0.001)throw std::runtime_error("S5 CPU-GPU projection tolerance exceeded");
    }
};
int positive(const char* value){
    char* end=nullptr;const long n=std::strtol(value,&end,10);
    if(!*value || *end || n<1 || n>100000)throw std::runtime_error("invalid --runs");
    return static_cast<int>(n);
}
}
int main(int argc,char** argv) {
    try {
        if(argc<4)throw std::runtime_error("usage: tool_gpu_s45 left right output --version <0|1> [--runs N] [--debug]");
        int version=0,runs=1;bool debug=false;
        for(int i=4;i<argc;++i) {
            const std::string option=argv[i];
            if(option=="--debug")debug=true;
            else if(option=="--version" && i+1<argc){const std::string v=argv[++i];if(v!="0" && v!="1")throw std::runtime_error("unsupported version");version=v=="1";}
            else if(option=="--runs" && i+1<argc)runs=positive(argv[++i]);
            else throw std::runtime_error("unknown or incomplete option");
        }
        std::cerr<<"Verification scope: S4-S5 only; CPU S1-S3/S6. No pipeline speedup.\n";
        Inputs a(argv[1]),b(argv[2]);Config config;
        check(make_v0_config(a.image.width,a.image.height,config));V0Workspace host;
        check(v0_prepare(a.image,b.image,config,host));
        check(v0_preprocess(a.image,host.gray_a,config));check(v0_preprocess(b.image,host.gray_b,config));
        check(v0_detect(host.gray_a,host.keypoints_a,config));check(v0_detect(host.gray_b,host.keypoints_b,config));
        check(v0_describe(host.gray_a,host.keypoints_a,host.descriptors_a,config));
        check(v0_describe(host.gray_b,host.keypoints_b,host.descriptors_b,config));
        if(version==1) {
            CUDA_CHECK(cudaDeviceSetLimit(cudaLimitStackSize,32768));
            cudaDeviceProp device;CUDA_CHECK(cudaGetDeviceProperties(&device,0));std::cerr<<"GPU: "<<device.name<<'\n';
            DeviceStages gpu;gpu.prepare(host);gpu.run(host,config,false);
            std::cout<<"S4_V1_ms,S5_V1_ms\n";
            for(int i=0;i<runs;++i)gpu.run(host,config,true);
            gpu.verify(host,config,b.image.width,b.image.height);
        } else {
            check(v0_match(view(host.descriptors_a),view(host.descriptors_b),host.matches,config));
            check(v0_homography(view(host.keypoints_a),view(host.keypoints_b),view(host.matches),host.homography,config));
        }
        if(debug) {
            std::cerr<<"[debug] H(B->A)="<<std::setprecision(9);
            for(float value:host.homography.data)std::cerr<<value<<' ';
            std::cerr<<'\n';
        }
        check(v0_warp_blend(a.image,b.image,host.homography,host.panorama,config));
        const Image& p=host.panorama.image;
        if(!stbi_write_png(argv[3],p.width,p.height,3,p.data,static_cast<int>(p.stride)))throw std::runtime_error("output write failed");
        return 0;
    }catch(const std::exception& e){std::cerr<<"Error: "<<e.what()<<'\n';return 1;}
}
