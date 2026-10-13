// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// Dev tool, outside the timed region: runs S1 on one image and writes two 8-bit PNGs,
// <prefix>_gray.png (grayscale only) and <prefix>_blur.png (grayscale + Gaussian blur).
// Each PNG has a lossless twin, <prefix>_gray.f32 and <prefix>_blur.f32, for feeding later stages:
// int32 width, int32 height, then width * height float values in [0, 1], row-major, packed
// (stride = width * 4 bytes), all little-endian.
// The gray-only image uses sigma = 1e-3, radius = 1: its weights are exactly {0, 1, 0},
// so the blur is the identity and the output still comes from v0_preprocess.
// Usage: tool_export_gray <input_image> <output_prefix> [sigma radius]

#include "v0_preprocess.h"
#include "stb_image.h"
#include "stb_image_write.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace panorama;

static bool write_f32(const std::string& path, const std::vector<float>& gray, int w, int h) {
    std::FILE* file = std::fopen(path.c_str(), "wb");
    if (!file) return false;
    const std::int32_t header[2] = {w, h};
    const bool ok = std::fwrite(header, sizeof(header), 1, file) == 1 &&
                    std::fwrite(gray.data(), sizeof(float), gray.size(), file) == gray.size();
    return std::fclose(file) == 0 && ok;
}

static bool run_and_save(const Image& in, const Config& config, const std::string& base) {
    const std::string path = base + ".png";
    std::vector<float> gray(static_cast<std::size_t>(in.width) * in.height);
    GrayImage out;
    out.data = gray.data(); out.width = in.width; out.height = in.height; out.channels = 1;
    out.stride = static_cast<std::size_t>(in.width) * sizeof(float);
    if (v0_preprocess(in, out, config) != ErrorCode::Success) return false;
    std::vector<unsigned char> bytes(gray.size());
    double lo = 1.0, hi = 0.0;
    for (std::size_t i = 0; i < gray.size(); ++i) {
        lo = std::min<double>(lo, gray[i]);
        hi = std::max<double>(hi, gray[i]);
        bytes[i] = static_cast<unsigned char>(std::floor(gray[i] * 255.0f + 0.5f));
    }
    std::cout << path << ": " << in.width << "x" << in.height << " min=" << lo << " max=" << hi << '\n';
    return stbi_write_png(path.c_str(), in.width, in.height, 1, bytes.data(), in.width) != 0 &&
           write_f32(base + ".f32", gray, in.width, in.height);
}

int main(int argc, char** argv) {
    if (argc != 3 && argc != 5) {
        std::cerr << "Usage: tool_export_gray <input_image> <output_prefix> [sigma radius]\n";
        return 2;
    }
    int w = 0, h = 0, channels = 0;
    std::uint8_t* pixels = stbi_load(argv[1], &w, &h, &channels, 3);
    if (!pixels) { std::cerr << "Cannot read " << argv[1] << '\n'; return 1; }
    Image in;
    in.data = pixels; in.width = w; in.height = h; in.channels = 3;
    in.stride = static_cast<std::size_t>(w) * 3;

    Config identity;
    identity.gaussian_sigma = 1e-3f; identity.gaussian_radius = 1;
    Config blur;
    blur.gaussian_sigma = argc == 5 ? static_cast<float>(std::atof(argv[3])) : 1.0f;
    blur.gaussian_radius = argc == 5 ? std::atoi(argv[4]) : 3;

    const std::string prefix = argv[2];
    const bool ok = run_and_save(in, identity, prefix + "_gray") &&
                    run_and_save(in, blur, prefix + "_blur");
    stbi_image_free(pixels);
    return ok ? 0 : 1;
}
