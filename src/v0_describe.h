// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

#ifndef GROUP16_V0_DESCRIBE_H
#define GROUP16_V0_DESCRIBE_H

#include "common.h"
#include <vector>

namespace panorama {

// 256-bit BRIEF descriptors (no orientation) for keypoints of one gray image in [0, 1].
// The image is first smoothed with a Gaussian (kBriefSmoothSigma, kBriefSmoothRadius,
// clamped borders) into a private buffer; `image` is not modified. Each keypoint is sampled
// at its rounded centre (floor(x + 0.5), floor(y + 0.5)); keypoints whose 31 x 31 patch
// leaves the image are dropped. Bit k of a descriptor is data[k / 32] bit k % 32 and is set
// when the first point of kBriefPattern[k] is strictly darker than the second.
// On Success `keypoints` keeps the surviving entries in their original order and
// descriptors[i] belongs to keypoints[i]. `descriptors` is cleared on entry; on error
// `keypoints` is unchanged and `descriptors` stays empty.
// S3 has no Config fields; `config` is accepted for a uniform stage signature.
// Errors: InvalidImage, InvalidArgument (non-finite coordinates or more than INT32_MAX
// keypoints), AllocationFailed.
// Pass debug_mode=false inside benchmark timing regions; debug only logs to stderr.
ErrorCode v0_describe(const GrayImage& image, std::vector<Keypoint>& keypoints,
                      std::vector<Descriptor>& descriptors, const Config& config,
                      bool debug_mode = false);

}  // namespace panorama

#endif  // GROUP16_V0_DESCRIBE_H
