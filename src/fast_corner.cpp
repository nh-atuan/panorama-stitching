// Authors: Nguyen Ho Anh Tuan (23120185)
// Adapted from: Rosten and Drummond, "Machine learning for high-speed corner detection",
// ECCV 2006, https://www.edwardrosten.com/work/rosten_2006_machine.pdf, accessed 2026-10-16
// Changes: only the full segment test and the score V of the paper; no learned decision tree.

#include "fast_corner.h"

namespace panorama {

float fast_corner_score(float center, const float ring[kFastCircleSize], float threshold) {
    // +1 bright, -1 dark, 0 similar.
    std::int32_t state[kFastCircleSize];
    for (std::int32_t i = 0; i < kFastCircleSize; ++i) {
        const float d = ring[i] - center;
        state[i] = d > threshold ? 1 : (d < -threshold ? -1 : 0);
    }

    // Walk the ring once plus kFastArcLength - 1 steps so arcs crossing 15 -> 0 are seen.
    bool corner = false;
    std::int32_t bright_run = 0;
    std::int32_t dark_run = 0;
    for (std::int32_t step = 0; step < kFastCircleSize + kFastArcLength - 1; ++step) {
        const std::int32_t s = state[step % kFastCircleSize];
        bright_run = s > 0 ? bright_run + 1 : 0;
        dark_run = s < 0 ? dark_run + 1 : 0;
        if (bright_run >= kFastArcLength || dark_run >= kFastArcLength) {
            corner = true;
            break;
        }
    }
    if (!corner) return 0.0f;

    float bright_sum = 0.0f;
    float dark_sum = 0.0f;
    for (std::int32_t i = 0; i < kFastCircleSize; ++i) {
        const float d = ring[i] - center;
        if (state[i] > 0) bright_sum += d - threshold;
        if (state[i] < 0) dark_sum += -d - threshold;
    }
    return bright_sum > dark_sum ? bright_sum : dark_sum;
}

}  // namespace panorama
