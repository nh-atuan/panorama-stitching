// Authors: Le Thuong De (23120232)
// External source: none

#include "homography_dlt.h"
#include "homography_svd.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace panorama;
using namespace panorama::homography_detail;
namespace {
int checks = 0;
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}
Point2 ground_truth(const Matrix3& h, const Point2& b) {
    // Independent analytic projection, not the implementation under test.
    const double w = h[6]*b.x + h[7]*b.y + h[8];
    return Point2((h[0]*b.x+h[1]*b.y+h[2])/w,
                  (h[3]*b.x+h[4]*b.y+h[5])/w);
}
std::vector<Correspondence> fixture(const Matrix3& h, int columns=2, int rows=2,
                                    double offset=0.0) {
    std::vector<Correspondence> result;
    for (int y=0; y<rows; ++y)
        for (int x=0; x<columns; ++x) {
            Correspondence pair;
            pair.b=Point2(offset+10.0+80.0*x,offset+10.0+60.0*y);
            pair.a=ground_truth(h,pair.b);
            result.push_back(pair);
        }
    return result;
}
void check_fit(const Matrix3& truth, int columns, int rows, double offset,
               double tolerance) {
    const std::vector<Correspondence> points=fixture(truth,columns,rows,offset);
    Matrix3 estimated = {};
    require(normalized_dlt(points,points.size()==4,1e-6,estimated)==ErrorCode::Success,"DLT fit");
    for (const Correspondence& pair : points) {
        Point2 actual;
        require(project(estimated,pair.b,1e-6,actual),"finite projection");
        require(std::hypot(actual.x-pair.a.x,actual.y-pair.a.y)<tolerance,"analytic fit error");
    }
    Point2 check(47.0+offset,39.0+offset), actual;
    const Point2 expected=ground_truth(truth,check);
    require(project(estimated,check,1e-6,actual),"held-out projection");
    require(std::hypot(actual.x-expected.x,actual.y-expected.y)<tolerance,"held-out fit error");
    double max_coefficient=0.0;
    for(double value:estimated) max_coefficient=std::max(max_coefficient,std::abs(value));
    require(max_coefficient==1.0,"max-abs gauge");
}
void test_models() {
    const Matrix3 models[] = {
        {{1,0,0,0,1,0,0,0,1}},
        {{1,0,20,0,1,5,0,0,1}},
        {{1.1,0.08,12,-0.04,0.93,4,0,0,1}},
        {{1.05,0.03,14,-0.02,0.97,6,0.0002,-0.0001,1}},
        {{1,0.1,20,0.2,1,10,0.01,0.02,0}}
    };
    for(const Matrix3& h:models) {
        check_fit(h,2,2,0.0,1e-8);
        check_fit(h,8,6,0.0,1e-8);
    }
    check_fit(models[2],4,4,1000000.0,1e-6);
    Matrix3 inverse = {}, negative=models[3];
    for(double& value:negative) value *= -17.0;
    Point2 p(71,29), positive_projection, negative_projection;
    require(project(models[3],p,1e-6,positive_projection),"positive H");
    require(project(negative,p,1e-6,negative_projection),"negative H");
    require(std::hypot(positive_projection.x-negative_projection.x,
                       positive_projection.y-negative_projection.y)<1e-10,"H scale invariance");
    require(invert(models[3],inverse),"inverse");
    Point2 back;
    require(project(inverse,positive_projection,1e-6,back),"inverse projection");
    require(std::hypot(back.x-p.x,back.y-p.y)<1e-10,"roundtrip");
}
void test_failures_and_full_basis() {
    Matrix3 h={{1,0,0,0,1,0,0,0,1}}, out={};
    std::vector<Correspondence> points=fixture(h);
    points[1].b=points[0].b;
    require(normalized_dlt(points,true,1e-6,out)==ErrorCode::DegenerateHomography,"duplicate B");
    require(out==Matrix3(),"failure clears H");
    points=fixture(h); points[1].a=points[0].a;
    require(normalized_dlt(points,true,1e-6,out)==ErrorCode::DegenerateHomography,"duplicate A");
    for(int i=0;i<4;++i) {points[i].a=Point2(i,0);points[i].b=Point2(i,0);}
    require(normalized_dlt(points,true,1e-6,out)==ErrorCode::DegenerateHomography,"collinearity");
    points.resize(3);
    require(normalized_dlt(points,false,1e-6,out)==ErrorCode::InsufficientMatches,"three pairs");
    points=fixture(h); points[0].a.x=std::numeric_limits<double>::quiet_NaN();
    require(normalized_dlt(points,true,1e-6,out)==ErrorCode::NumericalFailure,"NaN input");
    points=fixture(h);
    require(normalized_dlt(points,true,0,out)==ErrorCode::InvalidConfig,"unset epsilon");
    std::vector<double> matrix(8*9,0.0);
    for(int i=0;i<8;++i) matrix[9*i+i]=i+1.0;
    Matrix3 vector={}, singular={};
    require(smallest_right_vector(matrix,8,vector,singular)==ErrorCode::Success,"8x9 full SVD");
    require(std::abs(vector[8])==1.0 && singular[8]==0.0,"ninth nullspace vector");
    require(singular[0]==8.0 && singular[7]==1.0,"descending singular values");
    const Matrix3 horizon={{1,0,0,0,1,0,1,0,-10}};
    Point2 projected;
    require(!project(horizon,Point2(10,2),1e-6,projected),"horizon denominator");
    require(!project(horizon,Point2(10+1e-8,2),1e-6,projected),"near horizon denominator");
}
void test_noisy_refit_and_rank() {
    const Matrix3 truth={{1.05,0.03,14,-0.02,0.97,6,0.0002,-0.0001,1}};
    std::vector<Correspondence> points=fixture(truth,8,6);
    for(std::size_t i=0;i<points.size();++i) {
        points[i].a.x += 0.12*std::sin(1.7*static_cast<double>(i));
        points[i].a.y += 0.10*std::cos(0.3*static_cast<double>(i));
    }
    Matrix3 estimated={};
    require(normalized_dlt(points,false,1e-6,estimated)==ErrorCode::Success,"noisy non-minimal fit");
    for(int y=0;y<5;++y) for(int x=0;x<7;++x) {
        const Point2 b(30+80*x,25+60*y), expected=ground_truth(truth,b);
        Point2 actual;
        require(project(estimated,b,1e-6,actual),"noisy held-out projection");
        require(std::hypot(actual.x-expected.x,actual.y-expected.y)<0.1,"bounded held-out error");
    }
    for(std::size_t i=0;i<points.size();++i) {
        points[i].a=Point2(static_cast<double>(i),2.0*i+1.0);
        points[i].b=Point2(2.0*i,4.0*i+2.0);
    }
    require(normalized_dlt(points,false,1e-6,estimated)==ErrorCode::DegenerateHomography,
            "rank failure on all-inlier fit");
}
}  // namespace
int main() {
    try {
        test_models(); test_failures_and_full_basis(); test_noisy_refit_and_rank();
        std::cout << "PASS DLT: " << checks << " checks; direct double SVD, B->A\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "FAIL DLT: " << error.what() << '\n'; return 1;
    }
}
