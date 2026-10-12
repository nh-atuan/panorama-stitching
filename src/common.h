// Authors: Group 16
// External source: none

#ifndef GROUP16_COMMON_H
#define GROUP16_COMMON_H

#include <iostream>
#include <string>
#include <vector>

namespace panorama {

struct CliOptions {
    std::string left_image;
    std::string right_image;
    std::string output_image;
    int version = 0;
    int runs = 5;
    bool debug = false;
};

// Stage data types will be added after the shared interface is agreed upon.

}  // namespace panorama

#endif  // GROUP16_COMMON_H
