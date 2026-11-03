// Authors: Tran Huu Kim Thanh (23120166)
// External source: none

// Compares a stage result read back from the Device with its V0 reference.
// Every function returns an empty string on a match, otherwise a description of the
// first difference, so a test failure names the element to debug. Host code only.

#ifndef GROUP16_GPU_COMPARE_H
#define GROUP16_GPU_COMPARE_H

#include "common/common.h"
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

namespace gpu_test {

inline std::uint32_t float_bits(float value) {
    std::uint32_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

inline std::string size_mismatch(std::size_t expected, std::size_t actual) {
    std::ostringstream message;
    message << "size: expected " << expected << ", actual " << actual;
    return message.str();
}

// Bit comparison: 0.0f and -0.0f differ, and so do two NaN payloads.
inline std::string float_field_mismatch(const char* name, std::size_t index, float expected, float actual) {
    if (float_bits(expected) == float_bits(actual)) return std::string();
    std::ostringstream message;
    message.precision(9);
    message << "[" << index << "]." << name << ": expected " << expected << " (0x" << std::hex
            << float_bits(expected) << "), actual " << std::dec << actual << " (0x" << std::hex
            << float_bits(actual) << ")";
    return message.str();
}

inline std::string keypoint_mismatch(const std::vector<panorama::Keypoint>& expected,
                                     const std::vector<panorama::Keypoint>& actual) {
    if (expected.size() != actual.size()) return size_mismatch(expected.size(), actual.size());
    for (std::size_t i = 0; i < expected.size(); ++i) {
        std::string message = float_field_mismatch("x", i, expected[i].x, actual[i].x);
        if (message.empty()) message = float_field_mismatch("y", i, expected[i].y, actual[i].y);
        if (message.empty()) message = float_field_mismatch("score", i, expected[i].score, actual[i].score);
        if (message.empty()) message = float_field_mismatch("angle", i, expected[i].angle, actual[i].angle);
        if (!message.empty()) return message;
    }
    return std::string();
}

inline std::string descriptor_mismatch(const std::vector<panorama::Descriptor>& expected,
                                       const std::vector<panorama::Descriptor>& actual) {
    if (expected.size() != actual.size()) return size_mismatch(expected.size(), actual.size());
    for (std::size_t i = 0; i < expected.size(); ++i) {
        for (std::size_t word = 0; word < 8; ++word) {
            if (expected[i].data[word] == actual[i].data[word]) continue;
            std::ostringstream message;
            message << "[" << i << "].data[" << word << "]: expected 0x" << std::hex
                    << expected[i].data[word] << ", actual 0x" << actual[i].data[word];
            return message.str();
        }
    }
    return std::string();
}

// tolerance == 0 compares bits; a positive tolerance bounds the absolute difference
// and still rejects non-finite values.
inline std::string float_array_mismatch(const std::vector<float>& expected, const std::vector<float>& actual,
                                        float tolerance = 0.0f) {
    if (expected.size() != actual.size()) return size_mismatch(expected.size(), actual.size());
    for (std::size_t i = 0; i < expected.size(); ++i) {
        if (tolerance == 0.0f) {
            const std::string message = float_field_mismatch("value", i, expected[i], actual[i]);
            if (!message.empty()) return message;
        } else if (!(std::fabs(expected[i] - actual[i]) <= tolerance)) {
            std::ostringstream message;
            message.precision(9);
            message << "[" << i << "]: expected " << expected[i] << ", actual " << actual[i]
                    << ", tolerance " << tolerance;
            return message.str();
        }
    }
    return std::string();
}

}  // namespace gpu_test

#endif  // GROUP16_GPU_COMPARE_H
