// Authors: Le Thuong De (23120232)
// External source: none
// Device batching and prefix replay implement the team's S5 stage design.
#include "v1/s5/v1_homography_workspace.cuh"
#include <cmath>
#include <limits>

namespace panorama {
namespace {
using namespace homography_gpu;

__device__ double residual(const Matrix3& h,const Correspondence& p,double tau2,double epsilon,int& inlier) {
    Point2 q;inlier=0;
    if(!project(h,p.b,epsilon,q))return tau2;
    const double dx=q.x-p.a.x,dy=q.y-p.a.y;
    const double e=dx*dx+dy*dy;
    if(!isfinite(e))return tau2;
    inlier=e<tau2;return min_value(e,tau2);
}

__global__ void prepare_homography(DeviceWorkspace w,Scratch s,Config config) {
    *s.state=State();
    *w.d_homography=Homography();
    if(w.d_counts->status!=ErrorCode::Success){s.state->done=1;return;}
    const DeviceCounts c=*w.d_counts;
    ErrorCode status=ErrorCode::Success;
    if(c.keypointsA>w.keypoint_capacityA || c.keypointsB>w.keypoint_capacityB ||
       c.matches>w.match_capacity) status=ErrorCode::InvalidArgument;
    else {
        for(unsigned i=0;i<c.keypointsA;++i)
            if(!isfinite(w.d_keypointsA[i].x)||!isfinite(w.d_keypointsA[i].y))status=ErrorCode::NumericalFailure;
        for(unsigned i=0;i<c.keypointsB;++i)
            if(!isfinite(w.d_keypointsB[i].x)||!isfinite(w.d_keypointsB[i].y))status=ErrorCode::NumericalFailure;
        if(status==ErrorCode::Success) {
            int previous=-1;
            for(unsigned i=0;i<c.matches;++i) {
                const Match m=w.d_matches[i];
                if(m.indexA<=previous || m.indexA>=static_cast<int>(c.keypointsA) ||
                   m.indexB<0 || m.indexB>=static_cast<int>(c.keypointsB) || m.distance>256u) {
                    status=ErrorCode::InvalidArgument;break;
                }
                previous=m.indexA;
            }
            if(status==ErrorCode::Success && c.matches<4)status=ErrorCode::InsufficientMatches;
        }
    }
    s.state->count=static_cast<int>(c.matches);
    if(status!=ErrorCode::Success){w.d_counts->status=status;s.state->done=1;}
    else s.state->report.adaptive_budget=config.ransac_iters;
}

__global__ void gather_points(DeviceWorkspace w,Scratch s) {
    const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
    if(w.d_counts->status!=ErrorCode::Success || i>=static_cast<unsigned>(s.state->count))return;
    const Match m=w.d_matches[i];
    const Keypoint a=w.d_keypointsA[m.indexA],b=w.d_keypointsB[m.indexB];
    s.points[i].a=Point2(a.x,a.y);s.points[i].b=Point2(b.x,b.y);
}

__global__ void compute_hypotheses(DeviceWorkspace w,Scratch s,Config config,int first) {
    if(w.d_counts->status!=ErrorCode::Success || s.state->done)return;
    Hypothesis& result=s.hypotheses[blockIdx.x];
    if(threadIdx.x==0) {
        Array<std::int32_t,4> indices;
        uniform_sample4(config.seed,first+static_cast<int>(blockIdx.x),s.state->count,indices);
        Correspondence sample[4];Point2 a[4],b[4];double design[81];
        for(int i=0;i<4;++i){result.sample[i]=indices[i];sample[i]=s.points[indices[i]];}
        result.status=normalized_dlt(Buffer<Correspondence>(sample,4),true,config.homography_epsilon,
                                     result.matrix,design,a,b);
    }
    __syncthreads();
    double* losses=s.losses+blockIdx.x*s.leaves;
    int* inliers=s.inliers+blockIdx.x*s.leaves;
    for(std::size_t i=threadIdx.x;i<s.leaves;i+=blockDim.x) {
        int keep=0;double loss=0;
        if(i<static_cast<std::size_t>(s.state->count) && result.status==ErrorCode::Success)
            loss=residual(result.matrix,s.points[i],static_cast<double>(config.ransac_threshold)*config.ransac_threshold,
                          config.homography_epsilon,keep);
        losses[i]=loss;inliers[i]=keep;
    }
    __syncthreads();
    for(std::size_t stride=1;stride<s.leaves;stride*=2) {
        for(std::size_t i=threadIdx.x*2*stride;i<s.leaves;i+=blockDim.x*2*stride) {
            losses[i]+=losses[i+stride];inliers[i]+=inliers[i+stride];
        }
        __syncthreads();
    }
    if(threadIdx.x==0){result.loss=losses[0];result.inliers=inliers[0];}
}

__global__ void commit_prefix(DeviceWorkspace w,Scratch s,Config config,int first,int computed) {
    if(w.d_counts->status!=ErrorCode::Success || s.state->done)return;
    V1HomographyDiagnostics& r=s.state->report;
    r.computed_hypotheses+=computed;
    for(int i=0;i<computed;++i) {
        const Hypothesis& h=s.hypotheses[i];
        ++r.attempts;
        for(int k=0;k<4;++k)r.sample_hash=(r.sample_hash^static_cast<std::uint64_t>(h.sample[k]))*UINT64_C(1099511628211);
        if(h.status==ErrorCode::Success) {
            ++r.valid_hypotheses;
            if(better_model(ModelScore(h.loss,h.inliers),first+i,ModelScore(r.best_loss,r.best_inliers),r.best_hypothesis)) {
                r.best_hypothesis=first+i;r.best_loss=h.loss;r.best_inliers=h.inliers;
                s.state->best=h.matrix;
                r.adaptive_budget=adaptive_iteration_budget(h.inliers,s.state->count,config.ransac_iters);
            }
        } else ++r.rejected_samples;
        if(r.attempts>=r.adaptive_budget){s.state->done=1;break;}
    }
}

__device__ int select_points(Scratch s,const std::uint8_t* mask) {
    int n=0;for(int i=0;i<s.state->count;++i)if(mask[i])s.selected[n++]=s.points[i];return n;
}

__global__ void refit_homography(DeviceWorkspace w,Scratch s,Config config) {
    if(w.d_counts->status!=ErrorCode::Success)return;
    V1HomographyDiagnostics& r=s.state->report;
    if(r.best_hypothesis<0){w.d_counts->status=ErrorCode::DegenerateHomography;return;}
    Buffer<Correspondence> points(s.points,s.state->count);
    Buffer<std::uint8_t> best_mask(s.best_mask,s.state->count),mask(s.mask,s.state->count);
    evaluate_msac(s.state->best,points,config.ransac_threshold,config.homography_epsilon,best_mask);
    Matrix3 refined={};
    int n=select_points(s,s.best_mask);
    ErrorCode status=normalized_dlt(Buffer<Correspondence>(s.selected,n),false,config.homography_epsilon,
                                    refined,s.design,s.normalized_a,s.normalized_b);
    if(status!=ErrorCode::Success){w.d_counts->status=status;return;}
    r.refit_passes=1;
    ModelScore score=evaluate_msac(refined,points,config.ransac_threshold,config.homography_epsilon,mask);
    r.first_refit_loss=score.loss;r.first_refit_inliers=score.inliers;r.refit_loss=score.loss;
    if(score.inliers<4){w.d_counts->status=ErrorCode::InsufficientMatches;return;}
    bool changed=false;for(int i=0;i<s.state->count;++i)changed|=s.mask[i]!=s.best_mask[i];
    if(changed) {
        n=select_points(s,s.mask);
        status=normalized_dlt(Buffer<Correspondence>(s.selected,n),false,config.homography_epsilon,
                              refined,s.design,s.normalized_a,s.normalized_b);
        if(status!=ErrorCode::Success){w.d_counts->status=status;return;}
        r.refit_passes=2;
        score=evaluate_msac(refined,points,config.ransac_threshold,config.homography_epsilon,mask);
        r.refit_loss=score.loss;
    }
    Homography candidate;Matrix3 stored={};
    for(int i=0;i<9;++i){candidate.data[i]=static_cast<float>(refined[i]);stored[i]=candidate.data[i];}
    status=validate_matrix(stored);
    if(status!=ErrorCode::Success){w.d_counts->status=status;return;}
    for(int i=0;i<9;++i)candidate.data[i]=static_cast<float>(stored[i]);
    score=evaluate_msac(stored,points,config.ransac_threshold,config.homography_epsilon,mask);
    if(!isfinite(score.loss)){w.d_counts->status=ErrorCode::NumericalFailure;return;}
    if(score.inliers<4){w.d_counts->status=ErrorCode::InsufficientMatches;return;}
    r.final_loss=score.loss;r.final_inliers=score.inliers;*w.d_homography=candidate;
}
}  // namespace

std::size_t v1_homography_scratch_bytes(std::size_t cap,int batch) {
    if(batch<1 || batch>256 || cap>static_cast<std::size_t>(INT32_MAX) || cap>SIZE_MAX/65536u)return 0;
    std::size_t bytes=0;homography_gpu::layout(nullptr,cap,batch,bytes);return bytes;
}
const V1HomographyDiagnostics* v1_homography_diagnostics(const DeviceWorkspace& w) {
    return reinterpret_cast<const V1HomographyDiagnostics*>(w.d_scratch);
}
const std::uint8_t* v1_homography_inlier_mask(const DeviceWorkspace& w,int batch) {
    if(!v1_homography_scratch_bytes(w.match_capacity,batch))return nullptr;
    std::size_t bytes=0;return homography_gpu::layout(w.d_scratch,w.match_capacity,batch,bytes).mask;
}
ErrorCode v1_homography_with_batch_size(DeviceWorkspace& w,const Config& c,cudaStream_t stream,int batch) {
    if(c.ransac_iters<=0 || c.ransac_iters>feature_policy::kMaxIterations ||
       !std::isfinite(c.ransac_threshold) || c.ransac_threshold<=0 ||
       !std::isfinite(c.homography_epsilon) || c.homography_epsilon<=0) return ErrorCode::InvalidConfig;
    if(batch<1 || batch>256 || !w.d_counts || !w.d_homography || !w.d_matches ||
       !w.d_keypointsA || !w.d_keypointsB || w.keypoint_capacityA>static_cast<std::size_t>(INT32_MAX) ||
       w.keypoint_capacityB>static_cast<std::size_t>(INT32_MAX))return ErrorCode::InvalidArgument;
    const std::size_t required=v1_homography_scratch_bytes(w.match_capacity,batch);
    if(!required || !w.d_scratch || w.scratch_capacity_bytes<required ||
       reinterpret_cast<std::uintptr_t>(w.d_scratch)%16u)return ErrorCode::AllocationFailed;
    std::size_t bytes=0;const homography_gpu::Scratch s=homography_gpu::layout(w.d_scratch,w.match_capacity,batch,bytes);
    prepare_homography<<<1,1,0,stream>>>(w,s,c);
    if(w.match_capacity)gather_points<<<static_cast<unsigned>((w.match_capacity+127)/128),128,0,stream>>>(w,s);
    for(int first=0;first<c.ransac_iters;first+=batch) {
        const int computed=std::min(batch,c.ransac_iters-first);
        compute_hypotheses<<<computed,128,0,stream>>>(w,s,c,first);
        commit_prefix<<<1,1,0,stream>>>(w,s,c,first,computed);
    }
    refit_homography<<<1,1,0,stream>>>(w,s,c);
    return cudaPeekAtLastError()==cudaSuccess?ErrorCode::Success:ErrorCode::CudaFailure;
}
ErrorCode v1_homography(DeviceWorkspace& w,const Config& c,cudaStream_t stream) {
    return v1_homography_with_batch_size(w,c,stream,32);
}
}  // namespace panorama
