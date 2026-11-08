// Authors: Le Ha Thanh Chuong (23120195)
// External source: none

#ifndef GROUP16_KERNEL_TIMING_CUH
#define GROUP16_KERNEL_TIMING_CUH

#include "cuda_utils.cuh"

#include <memory>
#include <stdexcept>

namespace panorama {

// The warm-up counts launches without recording events. Subsequent runs reuse
// those event pairs and read them only after the final stream synchronization.
class KernelTiming {
public:
    void prepare() {
        capacity_ = count_;
        events_.reset(new EventPair[capacity_]);
    }

    void reset() { count_ = 0; }

    template<class Launch>
    void record(cudaStream_t stream, const Launch& launch) {
        if (!events_) {
            ++count_;
            launch();
            return;
        }
        if (count_ >= capacity_) throw std::logic_error("Kernel launch count exceeded warm-up");
        EventPair& pair = events_[count_++];
        pair.start.record(stream);
        launch();
        pair.stop.record(stream);
    }

    double milliseconds() const {
        if (!events_ || count_ != capacity_) throw std::logic_error("Kernel launch count differs from warm-up");
        double sum = 0.0;
        for (std::size_t i = 0; i < count_; ++i) sum += events_[i].stop.elapsed_since(events_[i].start);
        return sum;
    }

private:
    struct EventPair { CudaEvent start, stop; };
    std::unique_ptr<EventPair[]> events_;
    std::size_t capacity_ = 0;
    std::size_t count_ = 0;
};

inline KernelTiming*& active_kernel_timing() {
    static thread_local KernelTiming* active = nullptr;
    return active;
}

class KernelTimingScope {
public:
    explicit KernelTimingScope(KernelTiming& timing) : previous_(active_kernel_timing()) {
        active_kernel_timing() = &timing;
    }
    ~KernelTimingScope() { active_kernel_timing() = previous_; }
    KernelTimingScope(const KernelTimingScope&) = delete;
    KernelTimingScope& operator=(const KernelTimingScope&) = delete;

private:
    KernelTiming* previous_;
};

template<class Launch>
inline void timed_kernel_launch(cudaStream_t stream, const Launch& launch) {
    KernelTiming* timing = active_kernel_timing();
    if (timing) timing->record(stream, launch);
    else launch();
}

}  // namespace panorama

#define PANORAMA_LAUNCH_KERNEL(stream, ...) \
    ::panorama::timed_kernel_launch((stream), [&] { __VA_ARGS__; })

#endif  // GROUP16_KERNEL_TIMING_CUH
