// Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185)
// Adapted from: algorithm descriptions in Lowe (2004),
// https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf, accessed 2026-10-13;
// OpenCV BFMatcher documentation, https://docs.opencv.org/4.13.0/d3/da1/classcv_1_1BFMatcher.html,
// accessed 2026-10-13. No external implementation copied.
// Changes: scalar binary Hamming, deterministic 2-NN ties, exact ratio 4/5,
// no mutual check, transactional host output and project ErrorCode handling.

#include "v0/v0_match.h"
#include "common/feature_support.h"
#include <cmath>
#include <new>
#include <stdexcept>

namespace panorama {
namespace {

std::uint32_t hamming_distance(const Descriptor& a, const Descriptor& b) {
    std::uint32_t distance = 0;
    for (int word = 0; word < 8; ++word) {
        std::uint32_t bits = a.data[word] ^ b.data[word];
        while (bits != 0) {
            bits &= bits - 1u;
            ++distance;
        }
    }
    return distance;
}

struct Neighbor {
    std::uint32_t distance;
    std::int32_t index;
    Neighbor(std::uint32_t value = 257u, std::int32_t position = -1)
        : distance(value), index(position) {}
};

bool precedes(const Neighbor& a, const Neighbor& b) {
    return a.distance < b.distance ||
           (a.distance == b.distance && a.index < b.index);
}

void keep_two(const Neighbor& candidate, Neighbor& best, Neighbor& second) {
    if (precedes(candidate, best)) {
        second = best;
        best = candidate;
    } else if (precedes(candidate, second)) {
        second = candidate;
    }
}

}  // namespace

ErrorCode v0_match(FeatureView<Descriptor> left, FeatureView<Descriptor> right,
                   std::vector<Match>& output, const Config& config) {
    output.clear();
    if (!std::isfinite(config.match_ratio_threshold) ||
        config.match_ratio_threshold != feature_policy::kRatio ||
        config.match_cross_check != 0u)
        return ErrorCode::InvalidConfig;
    if (!valid_feature_view(left) || !valid_feature_view(right))
        return ErrorCode::InvalidArgument;
    if (left.count < 1 || right.count < 2) return ErrorCode::InsufficientKeypoints;
    try {
        std::vector<Match> candidate_output;
        candidate_output.reserve(static_cast<std::size_t>(left.count));
        for (std::int32_t i = 0; i < left.count; ++i) {
            Neighbor best, second;
            for (std::int32_t j = 0; j < right.count; ++j)
                keep_two(Neighbor(hamming_distance(left.data[i], right.data[j]), j),
                         best, second);
            if (second.index < 0 || 5u * best.distance >= 4u * second.distance)
                continue;
            Match match;
            match.indexA = i;
            match.indexB = best.index;
            match.distance = best.distance;
            candidate_output.push_back(match);
        }
        if (candidate_output.size() < 4) return ErrorCode::InsufficientMatches;
        output.swap(candidate_output);
        return ErrorCode::Success;
    } catch (const std::bad_alloc&) {
        return ErrorCode::AllocationFailed;
    } catch (const std::length_error&) {
        return ErrorCode::AllocationFailed;
    }
}

}  // namespace panorama
