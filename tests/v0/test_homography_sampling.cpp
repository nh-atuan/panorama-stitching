// Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0/v0_homography_internal.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace panorama;
using namespace panorama::homography_detail;
namespace {
int checks=0;
void require(bool condition,const char* message) {
    if(!condition) throw std::runtime_error(message);
    ++checks;
}
void test_sampler() {
    // Golden tuples calculated separately with the documented uint64 reference rule.
    const std::int32_t golden[5][4]={{3,8,5,0},{1,7,0,6},{2,8,7,4},{5,7,0,1},{6,8,3,1}};
    const int schedule[]={4,0,3,1,2};
    for(int id:schedule) {
        std::array<std::int32_t,4> actual;
        require(uniform_sample4(16,id,9,actual),"golden sample");
        for(int i=0;i<4;++i) require(actual[i]==golden[id][i],"independent golden tuple/order");
    }
    const std::int32_t counts[]={4,5,9,31,100,2147483647};
    for(std::int32_t count:counts) {
        for(int id=0;id<60;++id) {
            std::array<std::int32_t,4> first,second;
            require(uniform_sample4(16,id,count,first),"sample succeeds");
            require(uniform_sample4(16,id,count,second) && first==second,"reproducible sample");
            for(int i=0;i<4;++i) {
                require(first[i]>=0 && first[i]<count,"sample bound");
                for(int j=0;j<i;++j) require(first[i]!=first[j],"sample without replacement");
            }
            if(count==4) {
                std::sort(first.begin(),first.end());
                require(first==std::array<std::int32_t,4>{{0,1,2,3}},"m=4 contains every index");
            }
        }
    }
    std::array<std::int32_t,4> sample;
    require(!uniform_sample4(16,0,3,sample),"insufficient sample universe");
    require(!uniform_sample4(16,-1,9,sample),"invalid hypothesis ID");
    require(adaptive_iteration_budget(0,100,2000)==2000,"zero inlier budget");
    require(adaptive_iteration_budget(100,100,2000)==1,"all inlier budget");
    require(adaptive_iteration_budget(50,100,2000)==72,"standard 0.5 ratio budget");
    require(adaptive_iteration_budget(10,100,2000)==2000,"budget capped");
    require(adaptive_iteration_budget(1,2147483647,2000)==2000,"guard huge floating budget");
}
}  // namespace
int main() {
    try {
        test_sampler();
        std::cout<<"PASS sampling: "<<checks<<" checks; seed=16 confidence=0.99\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"FAIL sampling: "<<error.what()<<'\n';return 1;
    }
}
