// Authors: Le Thuong De (23120232)
// External source: none

#include "homography_scoring.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace panorama;
using namespace panorama::homography_detail;
namespace {
int checks=0;
void require(bool condition,const char* message) {
    if(!condition) throw std::runtime_error(message);
    ++checks;
}
void test_score() {
    const Matrix3 identity={{1,0,0,0,1,0,0,0,1}};
    std::vector<Correspondence> pairs(3);
    pairs[0].a=Point2(2,0); pairs[0].b=Point2(0,0);
    pairs[1].a=Point2(4,0); pairs[1].b=Point2(1,0);
    pairs[2].a=Point2(6,0); pairs[2].b=Point2(2,0);
    std::vector<std::uint8_t> mask;
    ModelScore score=evaluate_msac(identity,pairs,3,1e-6,mask);
    require(score.loss==22 && score.inliers==1,"MSAC 4+9+9 loss");
    require(mask==std::vector<std::uint8_t>({1,0,0}),"strict boundary classification");
    const Matrix3 horizon={{1,0,0,0,1,0,1,0,0}};
    pairs.resize(2);
    pairs[0].a=Point2(0,0);pairs[0].b=Point2(0,0);
    pairs[1].a=Point2(1,0);pairs[1].b=Point2(1,0);
    score=evaluate_msac(horizon,pairs,3,1e-6,mask);
    require(score.loss==9 && score.inliers==1 && mask[0]==0,"invalid projection contributes cap");
    score=evaluate_msac(identity,pairs,0,1e-6,mask);
    require(!std::isfinite(score.loss) && mask.empty(),"invalid score parameters");
    require(better_model(ModelScore(1,4),7,ModelScore(2,100),6),"loss wins over count");
    require(!better_model(ModelScore(2,100),6,ModelScore(1,4),7),"count cannot override loss");
    require(better_model(ModelScore(1,5),7,ModelScore(1,4),6),"count tie break");
    require(better_model(ModelScore(1,4),6,ModelScore(1,4),7),"ID tie break");
    require(!better_model(ModelScore(0,3),0,ModelScore(1,4),1),"under four inliers rejected");
    pairs.resize(4);
    for(std::size_t i=0;i<pairs.size();++i) {
        pairs[i].a=Point2(static_cast<double>(i%2),static_cast<double>(i/2));
        pairs[i].b=pairs[i].a;
    }
    const Matrix3 shifted={{1,0,0.25,0,1,0,0,0,1}};
    const ModelScore exact=evaluate_msac(identity,pairs,3,1e-6,mask);
    const ModelScore displaced=evaluate_msac(shifted,pairs,3,1e-6,mask);
    require(exact.inliers==4 && exact.loss==0.0,"exact model with four inliers");
    require(displaced.inliers==4 && displaced.loss==0.25,"same count with geometric residual");
    require(better_model(exact,7,displaced,6),"same-count residual ranking overrides lower ID");
}
}  // namespace
int main() {
    try {
        test_score();
        std::cout<<"PASS MSAC: "<<checks<<" checks; strict forward reprojection loss\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"FAIL MSAC: "<<error.what()<<'\n';return 1;
    }
}
