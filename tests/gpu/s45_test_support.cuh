// Authors: Le Thuong De (23120232)
// External source: none
#ifndef GROUP16_S45_TEST_SUPPORT_CUH
#define GROUP16_S45_TEST_SUPPORT_CUH
#include "common/common.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace gpu_test {
inline int& checks() { static int count=0; return count; }
inline void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
    ++checks();
}
inline void cuda(cudaError_t status) {
    if (status!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(status));
}
template<class T> struct DeviceBuffer {
    T* data=nullptr; std::size_t count;
    explicit DeviceBuffer(std::size_t n) : count(n) {
        cuda(cudaMalloc(reinterpret_cast<void**>(&data),std::max<std::size_t>(1,n)*sizeof(T)));
    }
    DeviceBuffer(const DeviceBuffer&)=delete;
    DeviceBuffer& operator=(const DeviceBuffer&)=delete;
    ~DeviceBuffer() { cudaFree(data); }
    void upload(const std::vector<T>& values) {
        require(values.size()<=count,"upload capacity");
        if (!values.empty()) cuda(cudaMemcpy(data,values.data(),values.size()*sizeof(T),cudaMemcpyHostToDevice));
    }
    std::vector<T> read(std::size_t n) const {
        require(n<=count,"download capacity");
        std::vector<T> values(n);
        if(n) cuda(cudaMemcpy(values.data(),data,n*sizeof(T),cudaMemcpyDeviceToHost));
        return values;
    }
};
struct Stream {
    cudaStream_t value;
    Stream() { cuda(cudaStreamCreateWithFlags(&value,cudaStreamNonBlocking)); }
    ~Stream() { cudaStreamDestroy(value); }
    void wait() { cuda(cudaStreamSynchronize(value)); }
};
inline void print_gpu() {
    cudaDeviceProp device;
    cuda(cudaGetDeviceProperties(&device,0));
    std::cout<<"GPU: "<<device.name<<'\n';
}
}  // namespace gpu_test
#endif
