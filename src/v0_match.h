// Authors: Le Thuong De (23120232)
// External source: none

#ifndef GROUP16_V0_MATCH_H
#define GROUP16_V0_MATCH_H

#include "feature_views.h"
#include <vector>

namespace panorama {

// Exact Hamming 2-NN, strict ratio 4/5, no cross-check.
// Output is a caller-owned host vector, ordered by indexA; empty on failure.
// No logging occurs here, so callers can time the stage without debug I/O.
ErrorCode v0_match(FeatureView<Descriptor> left, FeatureView<Descriptor> right,
                   std::vector<Match>& output, const Config& config);

}  // namespace panorama

#endif
