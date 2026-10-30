// Authors: Le Thuong De (23120232)
// External source: none
#include "gpu/s45_test_support.cuh"
#include "v1/s4/v1_match.h"
#include "v1/s4/v1_match_internal.cuh"
#include "v0/v0_match.h"
#include <climits>
#include <random>

using namespace panorama;
using namespace gpu_test;

namespace {
Config config() { Config c; c.match_ratio_threshold=0.80f;c.match_cross_check=0;return c; }
void compare(const std::vector<Descriptor>& a,const std::vector<Descriptor>& b,int threads,
             std::size_t output_capacity=SIZE_MAX) {
    DeviceBuffer<Descriptor> da(a.size()),db(b.size()); da.upload(a);db.upload(b);
    DeviceBuffer<Match> matches(a.size());
    DeviceBuffer<DeviceCounts> counts(1);
    DeviceBuffer<std::uint8_t> scratch(v1_match_scratch_bytes(a.size()));
    DeviceCounts c; c.descriptorsA=static_cast<std::uint32_t>(a.size());c.descriptorsB=static_cast<std::uint32_t>(b.size());
    counts.upload({c});
    DeviceWorkspace w;w.d_descriptorsA=da.data;w.d_descriptorsB=db.data;w.d_matches=matches.data;
    w.d_counts=counts.data;w.d_scratch=scratch.data;w.scratch_capacity_bytes=scratch.count;
    w.descriptor_capacityA=a.size();w.descriptor_capacityB=b.size();w.match_capacity=std::min(a.size(),output_capacity);
    Stream stream;
    require(v1_match_with_block_size(w,config(),stream.value,threads)==ErrorCode::Success,"enqueue S4");
    stream.wait(); c=counts.read(1)[0];
    std::vector<Match> reference;
    ErrorCode expected=v0_match({a.data(),static_cast<int>(a.size()),a.size()},
        {b.data(),static_cast<int>(b.size()),b.size()},reference,config());
    if(expected==ErrorCode::Success && reference.size()>w.match_capacity) expected=ErrorCode::InvalidArgument;
    require(c.status==expected,"S4 status parity");
    require(c.matches==(expected==ErrorCode::Success?reference.size():0),"transactional match count");
    if(c.status==ErrorCode::Success) {
        const auto actual=matches.read(c.matches);
        for(std::size_t i=0;i<actual.size();++i) {
            require(actual[i].indexA==reference[i].indexA && actual[i].indexB==reference[i].indexB &&
                actual[i].distance==reference[i].distance,"ordered match parity");
        }
    }
    if(!a.empty() && b.size()>=2) {
        std::vector<match_gpu::TopTwo> top(a.size());
        cuda(cudaMemcpy(top.data(),scratch.data,top.size()*sizeof(top[0]),cudaMemcpyDeviceToHost));
        for(std::size_t i=0;i<a.size();++i) {
            std::vector<std::pair<unsigned,int>> distances;
            for(std::size_t j=0;j<b.size();++j) {
                unsigned d=0;
                for(int k=0;k<8;++k) {
                    unsigned bits=a[i].data[k]^b[j].data[k];
                    for(int bit=0;bit<32;++bit) d+=(bits>>bit)&1u;
                }
                distances.push_back({d,static_cast<int>(j)});
            }
            std::sort(distances.begin(),distances.end());
            require(top[i].best.distance==distances[0].first && top[i].best.index==distances[0].second,"exact best");
            require(top[i].second.distance==distances[1].first && top[i].second.index==distances[1].second,"exact second");
        }
    }
    Config bad=config();bad.match_cross_check=1;
    require(v1_match(w,bad,stream.value)==ErrorCode::InvalidConfig,"cross-check rejected");
    bad=config();bad.match_ratio_threshold=0.0f;
    require(v1_match(w,bad,stream.value)==ErrorCode::InvalidConfig,"ratio rejected");
    if(scratch.count) {
        --w.scratch_capacity_bytes;
        require(v1_match(w,config(),stream.value)==ErrorCode::AllocationFailed,"short scratch rejected");
        ++w.scratch_capacity_bytes;
    }
    c.status=ErrorCode::Success;c.descriptorsA=static_cast<unsigned>(a.size()+1);counts.upload({c});
    require(v1_match(w,config(),stream.value)==ErrorCode::Success,"enqueue invalid counts");stream.wait();
    require(counts.read(1)[0].status==ErrorCode::InvalidArgument,"count exceeds allocation");
    w.d_counts=nullptr;
    require(v1_match(w,config(),stream.value)==ErrorCode::InvalidArgument,"missing metadata");
}
}
int main() {
    try {
        print_gpu();
        std::mt19937 rng(16);
        for(int nb:{0,1,2,31,32,127,128,129,257}) {
            std::vector<Descriptor> a(19),b(static_cast<std::size_t>(nb));
            for(auto& d:a) for(auto& word:d.data) word=rng();
            for(auto& d:b) for(auto& word:d.data) word=rng();
            for(int i=0;i<std::min(19,nb);++i) b[i]=a[i];
            for(int threads:{32,64,128,256}) compare(a,b,threads);
            compare({},b,128);
        }
        // Identical alternatives fail ratio; multiple A may choose the same B.
        Descriptor zero,ones;for(auto& word:ones.data) word=UINT32_MAX;
        compare(std::vector<Descriptor>(8,zero),{zero,zero,ones},128);
        compare(std::vector<Descriptor>(8,zero),{zero,ones},128);
        compare(std::vector<Descriptor>(8,zero),{zero,ones},128,3);
        for(unsigned distance:{7u,8u,9u}) {
            Descriptor near,second;near.data[0]=(1u<<distance)-1;second.data[0]=1023u;
            compare(std::vector<Descriptor>(4,zero),{near,second},128);
        }
        require(v1_match_scratch_bytes(SIZE_MAX)==0,"scratch overflow");
        std::cout<<"PASS GPU S4: "<<checks()<<" checks\n";
        return 0;
    } catch(const std::exception& e) {std::cerr<<"FAIL GPU S4: "<<e.what()<<'\n';return 1;}
}
