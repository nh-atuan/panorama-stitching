// Authors: Thanh Chuong (23120195)
// External source: none

#ifndef GROUP16_CUDA_UTILS_CUH
#define GROUP16_CUDA_UTILS_CUH

// API semantics: NVIDIA CUDA Runtime API, Event and Memory Management.
// https://docs.nvidia.com/cuda/cuda-runtime-api/index.html
// Host-only V0 builds must not require CUDA headers or a CUDA driver.
#ifdef __CUDACC__
#include <cuda_runtime.h>
#include <cstdio>
#include <limits>
#include <stdexcept>

namespace panorama {

class CudaError : public std::runtime_error {
public:
    explicit CudaError(cudaError_t status)
        : std::runtime_error(cudaGetErrorString(status)), status(status) {}
    cudaError_t status;
};

inline void check_cuda(cudaError_t status, const char* call, const char* file, int line) {
    if (status == cudaSuccess) return;
    std::fprintf(stderr, "Error: [CudaFailure] %s:%d: %s: %s (%d)\n",
                 file, line, call, cudaGetErrorString(status), static_cast<int>(status));
    // Throw first: exit() here would bypass destructors and leak owned resources.
    // main catches this only after stack unwinding, then exits with EXIT_FAILURE.
    throw CudaError(status);
}

inline void cuda_cleanup_warning(cudaError_t status, const char* operation) noexcept {
    if (status != cudaSuccess) {
        std::fprintf(stderr, "Error: [CudaFailure] cleanup %s: %s\n",
                     operation, cudaGetErrorString(status));
    }
}

template <typename T>
inline void device_allocate(T*& pointer, std::size_t count) {
    if (pointer) throw std::invalid_argument("Device allocation requires an empty pointer");
    if (!count) return;
    if (count > std::numeric_limits<std::size_t>::max() / sizeof(T)) {
        throw std::length_error("Device allocation byte size overflows");
    }
    void* storage = nullptr;
    check_cuda(cudaMalloc(&storage, count * sizeof(T)), "cudaMalloc", __FILE__, __LINE__);
    pointer = static_cast<T*>(storage);
}

template <typename T>
inline void device_free(T*& pointer) noexcept {
    if (pointer) cuda_cleanup_warning(cudaFree(pointer), "cudaFree");
    pointer = nullptr;
}

// Pinned staging is prepared outside timing, avoiding hidden pageable-copy staging.
template <typename T>
class PinnedBuffer {
public:
    explicit PinnedBuffer(std::size_t count) {
        if (!count || count > std::numeric_limits<std::size_t>::max() / sizeof(T)) {
            throw std::length_error("Invalid pinned allocation size");
        }
        void* storage = nullptr;
        check_cuda(cudaMallocHost(&storage, count * sizeof(T)), "cudaMallocHost",
                   __FILE__, __LINE__);
        pointer_ = static_cast<T*>(storage);
    }
    ~PinnedBuffer() { cuda_cleanup_warning(cudaFreeHost(pointer_), "cudaFreeHost"); }
    PinnedBuffer(const PinnedBuffer&) = delete;
    PinnedBuffer& operator=(const PinnedBuffer&) = delete;
    T* get() const { return pointer_; }
private:
    T* pointer_ = nullptr;
};

class CudaStream {
public:
    CudaStream() {
        check_cuda(cudaStreamCreateWithFlags(&stream_, cudaStreamNonBlocking),
                   "cudaStreamCreateWithFlags", __FILE__, __LINE__);
    }
    ~CudaStream() {
        cuda_cleanup_warning(cudaStreamSynchronize(stream_), "cudaStreamSynchronize");
        cuda_cleanup_warning(cudaStreamDestroy(stream_), "cudaStreamDestroy");
    }
    CudaStream(const CudaStream&) = delete;
    CudaStream& operator=(const CudaStream&) = delete;
    cudaStream_t get() const { return stream_; }
private:
    cudaStream_t stream_ = nullptr;
};

class CudaEvent {
public:
    CudaEvent() {
        check_cuda(cudaEventCreate(&event_), "cudaEventCreate", __FILE__, __LINE__);
    }
    ~CudaEvent() { cuda_cleanup_warning(cudaEventDestroy(event_), "cudaEventDestroy"); }
    CudaEvent(const CudaEvent&) = delete;
    CudaEvent& operator=(const CudaEvent&) = delete;
    void record(cudaStream_t stream) {
        check_cuda(cudaEventRecord(event_, stream), "cudaEventRecord", __FILE__, __LINE__);
    }
    void synchronize() const {
        check_cuda(cudaEventSynchronize(event_), "cudaEventSynchronize", __FILE__, __LINE__);
    }
    double elapsed_since(const CudaEvent& start) const {
        float milliseconds = 0.0f;
        check_cuda(cudaEventElapsedTime(&milliseconds, start.event_, event_),
                   "cudaEventElapsedTime", __FILE__, __LINE__);
        return static_cast<double>(milliseconds);
    }
private:
    cudaEvent_t event_ = nullptr;
};

}  // namespace panorama

#define CUDA_CHECK(call) \
    ::panorama::check_cuda((call), #call, __FILE__, __LINE__)
#endif  // __CUDACC__

#endif  // GROUP16_CUDA_UTILS_CUH
