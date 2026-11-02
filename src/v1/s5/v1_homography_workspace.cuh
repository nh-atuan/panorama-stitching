// Authors: Le Thuong De (23120232)
// External source: none
#ifndef GROUP16_V1_HOMOGRAPHY_WORKSPACE_CUH
#define GROUP16_V1_HOMOGRAPHY_WORKSPACE_CUH
#include "v1/s5/v1_homography.h"
#include "v1/s5/v1_homography_math.cuh"
namespace panorama { namespace homography_gpu {
struct Hypothesis {
    Matrix3 matrix;
    int sample[4];
    ErrorCode status;
    double loss;
    int inliers;
};
struct State {
    V1HomographyDiagnostics report;
    Matrix3 best;
    int count, done;
};
struct Scratch {
    State* state;
    Correspondence* points;
    Correspondence* selected;
    Point2* normalized_a;
    Point2* normalized_b;
    double* design;
    Hypothesis* hypotheses;
    double* losses;
    int* inliers;
    std::uint8_t* mask;
    std::uint8_t* best_mask;
    std::size_t leaves;
};
inline std::size_t leaf_count(std::size_t n) {
    std::size_t p=1;while(p<n)p*=2;return p;
}
// Every slice starts at a 16-byte boundary; all sizes are checked on the Host.
template<class T> inline T* slice(std::uint8_t* base,std::size_t& offset,std::size_t n) {
    offset=(offset+15u)&~std::size_t(15u);
    T* pointer=base?reinterpret_cast<T*>(base+offset):nullptr;
    offset+=n*sizeof(T);return pointer;
}
inline Scratch layout(std::uint8_t* base,std::size_t cap,int batch,std::size_t& bytes) {
    Scratch s;bytes=0;s.leaves=leaf_count(cap);
    s.state=slice<State>(base,bytes,1);
    s.points=slice<Correspondence>(base,bytes,cap);
    s.selected=slice<Correspondence>(base,bytes,cap);
    s.normalized_a=slice<Point2>(base,bytes,cap);
    s.normalized_b=slice<Point2>(base,bytes,cap);
    s.design=slice<double>(base,bytes,(cap<5?9:2*cap)*9);
    s.hypotheses=slice<Hypothesis>(base,bytes,static_cast<std::size_t>(batch));
    s.losses=slice<double>(base,bytes,s.leaves*static_cast<std::size_t>(batch));
    s.inliers=slice<int>(base,bytes,s.leaves*static_cast<std::size_t>(batch));
    s.mask=slice<std::uint8_t>(base,bytes,cap);
    s.best_mask=slice<std::uint8_t>(base,bytes,cap);
    return s;
}
} }
#endif
