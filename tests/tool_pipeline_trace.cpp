// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// Dev tool: runs the V0 pipeline once (untimed) through v0_prepare/v0_run and writes the
// result of every stage, to see what each stage does on a real pair:
//   <prefix>_s1_left.png, <prefix>_s1_right.png   gray image after the S1 blur
//   <prefix>_s2_left.png, <prefix>_s2_right.png   S2 keypoints (red) kept by S3
//   <prefix>_s5_matches.png                       A | B side by side; S4 matches rejected
//                                                 by S5 in red, S5 inliers in green
//   <prefix>_s6_panorama.png                      S6 output
// and prints one "name=value" line per stage to stdout.
// Usage: tool_pipeline_trace <left_image> <right_image> <output_prefix>

#include "v0_config.h"
#include "v0_pipeline.h"
#include "stb_image.h"
#include "stb_image_write.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace panorama;

namespace {

struct Rgb {
    std::int32_t width = 0;
    std::int32_t height = 0;
    std::vector<std::uint8_t> pixels;
    Rgb(std::int32_t w, std::int32_t h) : width(w), height(h),
        pixels(static_cast<std::size_t>(w) * h * 3, 0) {}
    void set(std::int32_t x, std::int32_t y, const std::uint8_t color[3]) {
        if (x < 0 || y < 0 || x >= width || y >= height) return;
        std::uint8_t* p = pixels.data() + (static_cast<std::size_t>(y) * width + x) * 3;
        p[0] = color[0]; p[1] = color[1]; p[2] = color[2];
    }
    bool write(const std::string& path) const {
        return stbi_write_png(path.c_str(), width, height, 3, pixels.data(), width * 3) != 0;
    }
};

const std::uint8_t kRed[3] = {255, 40, 40};
const std::uint8_t kGreen[3] = {40, 230, 40};

// Marks scale with the image so they stay visible at 3840x2160.
std::int32_t mark_scale(std::int32_t width) {
    return std::max<std::int32_t>(1, width / 1280);
}

void cross(Rgb& image, std::int32_t x, std::int32_t y, std::int32_t arm, std::int32_t thick,
           const std::uint8_t color[3]) {
    for (std::int32_t d = -arm; d <= arm; ++d)
        for (std::int32_t t = -thick / 2; t <= thick / 2; ++t) {
            image.set(x + d, y + t, color);
            image.set(x + t, y + d, color);
        }
}

void line(Rgb& image, double x0, double y0, double x1, double y1, std::int32_t thick,
          const std::uint8_t color[3]) {
    const double steps = std::max(std::fabs(x1 - x0), std::fabs(y1 - y0));
    const std::int32_t n = static_cast<std::int32_t>(std::ceil(steps)) + 1;
    for (std::int32_t i = 0; i < n; ++i) {
        const double t = n > 1 ? static_cast<double>(i) / (n - 1) : 0.0;
        const std::int32_t x = static_cast<std::int32_t>(std::floor(x0 + t * (x1 - x0) + 0.5));
        const std::int32_t y = static_cast<std::int32_t>(std::floor(y0 + t * (y1 - y0) + 0.5));
        for (std::int32_t dy = -thick / 2; dy <= thick / 2; ++dy)
            for (std::int32_t dx = -thick / 2; dx <= thick / 2; ++dx) image.set(x + dx, y + dy, color);
    }
}

std::uint8_t to_byte(float value) {
    const float clamped = std::max(0.0f, std::min(1.0f, value));
    return static_cast<std::uint8_t>(std::floor(clamped * 255.0f + 0.5f));
}

Rgb gray_to_rgb(const GrayImage& gray) {
    Rgb out(gray.width, gray.height);
    for (std::int32_t y = 0; y < gray.height; ++y) {
        const float* row = reinterpret_cast<const float*>(
            reinterpret_cast<const std::uint8_t*>(gray.data) + static_cast<std::size_t>(y) * gray.stride);
        for (std::int32_t x = 0; x < gray.width; ++x) {
            const std::uint8_t v = to_byte(row[x]);
            const std::uint8_t c[3] = {v, v, v};
            out.set(x, y, c);
        }
    }
    return out;
}

bool write_gray(const std::string& path, const GrayImage& gray) {
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(gray.width) * gray.height);
    for (std::int32_t y = 0; y < gray.height; ++y) {
        const float* row = reinterpret_cast<const float*>(
            reinterpret_cast<const std::uint8_t*>(gray.data) + static_cast<std::size_t>(y) * gray.stride);
        for (std::int32_t x = 0; x < gray.width; ++x)
            bytes[static_cast<std::size_t>(y) * gray.width + x] = to_byte(row[x]);
    }
    return stbi_write_png(path.c_str(), gray.width, gray.height, 1, bytes.data(), gray.width) != 0;
}

bool write_keypoints(const std::string& path, const GrayImage& gray,
                     const std::vector<Keypoint>& keypoints) {
    Rgb image = gray_to_rgb(gray);
    const std::int32_t s = mark_scale(gray.width);
    for (const Keypoint& k : keypoints)
        cross(image, static_cast<std::int32_t>(k.x), static_cast<std::int32_t>(k.y), 4 * s, s, kRed);
    return image.write(path);
}

void paste(Rgb& canvas, const Image& source, std::int32_t left) {
    for (std::int32_t y = 0; y < source.height; ++y)
        for (std::int32_t x = 0; x < source.width; ++x)
            canvas.set(left + x, y, source.data + static_cast<std::size_t>(y) * source.stride +
                                        static_cast<std::size_t>(x) * 3);
}

bool write_matches(const std::string& path, const Image& left, const Image& right,
                   const V0Workspace& ws, const std::vector<std::uint8_t>& inlier) {
    Rgb image(left.width + right.width, std::max(left.height, right.height));
    paste(image, left, 0);
    paste(image, right, left.width);
    const std::int32_t s = mark_scale(left.width);
    // Rejected matches first, so inliers stay visible on top.
    for (int pass = 0; pass < 2; ++pass)
        for (std::size_t i = 0; i < ws.matches.size(); ++i) {
            const bool is_inlier = i < inlier.size() && inlier[i] != 0;
            if (is_inlier != (pass == 1)) continue;
            const Keypoint& a = ws.keypoints_a[ws.matches[i].indexA];
            const Keypoint& b = ws.keypoints_b[ws.matches[i].indexB];
            const std::uint8_t* color = is_inlier ? kGreen : kRed;
            line(image, a.x, a.y, b.x + left.width, b.y, s, color);
            cross(image, static_cast<std::int32_t>(a.x), static_cast<std::int32_t>(a.y), 3 * s, s, color);
            cross(image, static_cast<std::int32_t>(b.x) + left.width, static_cast<std::int32_t>(b.y),
                  3 * s, s, color);
        }
    return image.write(path);
}

bool load(const char* path, std::vector<std::uint8_t>& storage, Image& image) {
    int w = 0, h = 0, channels = 0;
    std::uint8_t* pixels = stbi_load(path, &w, &h, &channels, 3);
    if (!pixels) {
        std::cerr << "Cannot read " << path << '\n';
        return false;
    }
    storage.assign(pixels, pixels + static_cast<std::size_t>(w) * h * 3);
    stbi_image_free(pixels);
    image.data = storage.data();
    image.width = w;
    image.height = h;
    image.channels = 3;
    image.stride = static_cast<std::size_t>(w) * 3;
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "Usage: tool_pipeline_trace <left_image> <right_image> <output_prefix>\n";
        return 2;
    }
    std::vector<std::uint8_t> left_pixels, right_pixels;
    Image left, right;
    if (!load(argv[1], left_pixels, left) || !load(argv[2], right_pixels, right)) return 1;
    const std::string prefix = argv[3];

    Config config;
    if (make_v0_config(left.width, left.height, config) != ErrorCode::Success) return 1;
    V0Workspace ws;
    if (v0_prepare(left, right, config, ws) != ErrorCode::Success) {
        std::cerr << "Cannot prepare buffers\n";
        return 1;
    }
    HomographyReport report;
    Stage stage = Stage::Preprocess;
    const ErrorCode status = v0_run(left, right, config, ws, nullptr, &stage, &report);

    std::cout << "input A=" << left.width << 'x' << left.height << " B=" << right.width << 'x'
              << right.height << '\n';
    std::cout << "config ";
    write_config(std::cout, config);
    // Stages that ran before a failure still leave their output in the workspace.
    bool ok = write_gray(prefix + "_s1_left.png", ws.gray_a) &&
              write_gray(prefix + "_s1_right.png", ws.gray_b);
    std::cout << "S2 keypoints A=" << ws.detected_a << " B=" << ws.detected_b << '\n';
    std::cout << "S3 descriptors A=" << ws.descriptors_a.size() << " B=" << ws.descriptors_b.size()
              << '\n';
    ok = ok && write_keypoints(prefix + "_s2_left.png", ws.gray_a, ws.keypoints_a) &&
         write_keypoints(prefix + "_s2_right.png", ws.gray_b, ws.keypoints_b);
    std::cout << "S4 matches=" << ws.matches.size() << '\n';
    std::cout << "S5 inliers=" << report.final_inliers << " of " << ws.matches.size() << '\n';
    std::cout << "S5 H(B->A)=";
    for (int i = 0; i < 9; ++i) std::cout << (i ? " " : "") << ws.homography.data[i];
    std::cout << '\n';
    if (!ws.matches.empty()) {
        ok = ok && write_matches(prefix + "_s5_matches.png", left, right, ws, report.inlier_mask);
    }
    if (status != ErrorCode::Success) {
        std::cout << "FAILED at " << stage_name(stage) << " with code "
                  << static_cast<unsigned>(status) << '\n';
        return 1;
    }
    const Panorama& p = ws.panorama;
    std::cout << "S6 canvas=" << p.image.width << 'x' << p.image.height << " offset=("
              << p.offset_x << ',' << p.offset_y << ")\n";
    ok = ok && stbi_write_png((prefix + "_s6_panorama.png").c_str(), p.image.width, p.image.height,
                              3, p.image.data, static_cast<int>(p.image.stride)) != 0;
    if (!ok) {
        std::cerr << "Cannot write output images with prefix " << prefix << '\n';
        return 1;
    }
    return 0;
}
