// Authors: Thanh Chuong (23120195), Nguyen Ho Anh Tuan (23120185)
// External source: none

#include "v0/v0_warp_blend.h"
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <vector>

// Deterministic allocation failure for the output array, without large allocations.
static bool fail_array_allocation = false;
void* operator new[](std::size_t size) {
    if (fail_array_allocation) throw std::bad_alloc();
    void* result = std::malloc(size ? size : 1);
    if (!result) throw std::bad_alloc();
    return result;
}
void operator delete[](void* pointer) noexcept { std::free(pointer); }

using namespace panorama;
static int checks = 0;
static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}

struct Fixture {
    std::vector<std::uint8_t> storage;
    Image image;
    Fixture(int width, int height, std::uint8_t value, int padding = 0)
        : storage((width * 3 + padding) * height, 231) {
        image.data = storage.data(); image.width = width; image.height = height;
        image.channels = 3; image.stride = width * 3 + padding;
        for (int y = 0; y < height; ++y)
            for (int x = 0; x < width * 3; ++x)
                storage[static_cast<std::size_t>(y) * image.stride + x] = value;
    }
    void set(int x, int y, std::uint8_t value) {
        for (int c = 0; c < 3; ++c)
            storage[static_cast<std::size_t>(y) * image.stride + x * 3 + c] = value;
    }
};
struct Output {
    Panorama panorama;
    ~Output() { delete[] panorama.image.data; }
};
static Config settings() {
    Config config;
    config.homography_epsilon = 1e-6f;
    config.max_canvas_pixels = 100000000;
    return config;
}
static Homography matrix(float a, float b, float c, float d, float e, float f,
                         float g, float h, float i) {
    Homography result;
    const float values[9] = {a,b,c,d,e,f,g,h,i};
    for (int k = 0; k < 9; ++k) result.data[k] = values[k];
    return result;
}
static Homography identity() { return matrix(1,0,0, 0,1,0, 0,0,1); }
static void expect_pixel(const Panorama& p, int x, int y, int value) {
    for (int c = 0; c < 3; ++c)
        require(p.image.data[static_cast<std::size_t>(y)*p.image.stride + x*3+c] == value,
                "Unexpected output pixel");
}
static void expect_error(const Image& a, const Image& b, const Homography& h,
                         const Config& config, ErrorCode expected) {
    Output out;
    const ErrorCode actual = v0_warp_blend(a,b,h,out.panorama,config);
    if (actual != expected) {
        throw std::runtime_error("Expected ErrorCode " + std::to_string(static_cast<unsigned>(expected)) +
                                 ", got " + std::to_string(static_cast<unsigned>(actual)));
    }
    ++checks;
    require(out.panorama.image.data == nullptr, "Failure published a partial buffer");
}

int main() {
    try {
        Fixture a(4,3,100,5), b(4,3,20,7);
        const Config config = settings();
        {
            Output out;
            const std::vector<std::uint8_t> before = a.storage;
            require(v0_warp_blend(a.image,a.image,identity(),out.panorama,config) == ErrorCode::Success, "Identity failed");
            require(out.panorama.image.width == 4 && out.panorama.image.height == 3, "Identity clipped final row/column");
            require(out.panorama.offset_x == 0 && out.panorama.offset_y == 0, "Identity offset");
            expect_pixel(out.panorama,3,2,100);
            require(a.storage == before, "Modified input or padding");
        }
        {
            Output out;
            require(v0_warp_blend(a.image,b.image,identity(),out.panorama,config) == ErrorCode::Success, "Average failed");
            expect_pixel(out.panorama,0,0,60); expect_pixel(out.panorama,3,2,60);
        }
        {
            Output out;
            require(v0_warp_blend(a.image,b.image,matrix(1,0,-2,0,1,-1,0,0,1),out.panorama,config) == ErrorCode::Success, "Negative translation");
            require(out.panorama.image.width == 6 && out.panorama.image.height == 4, "Translation bbox");
            require(out.panorama.offset_x == 2 && out.panorama.offset_y == 1, "Negative offset");
            expect_pixel(out.panorama,0,0,20); expect_pixel(out.panorama,2,1,60);
            expect_pixel(out.panorama,5,3,100); expect_pixel(out.panorama,5,0,0);
        }
        {
            Output out;
            require(v0_warp_blend(a.image,b.image,matrix(1,0,2,0,1,1,0,0,1),out.panorama,config) == ErrorCode::Success, "Positive translation");
            require(out.panorama.image.width == 6 && out.panorama.image.height == 4, "Positive bbox");
            expect_pixel(out.panorama,0,0,100); expect_pixel(out.panorama,5,3,20);
            expect_pixel(out.panorama,5,0,0);
        }
        {
            Fixture black(1,1,0), white(1,1,255);
            Output out;
            require(v0_warp_blend(black.image,white.image,identity(),out.panorama,config) == ErrorCode::Success, "1x1 failed");
            expect_pixel(out.panorama,0,0,128); // Black is valid; half-up rounding.
        }
        {
            Fixture flat(3,1,20), ramp(2,1,0,4);
            ramp.set(1,0,100);
            Output out;
            require(v0_warp_blend(flat.image,ramp.image,matrix(1,0,0.5f,0,1,0,0,0,1),out.panorama,config) == ErrorCode::Success, "Fractional translation");
            expect_pixel(out.panorama,0,0,20); expect_pixel(out.panorama,1,0,35);
            expect_pixel(out.panorama,2,0,20);
        }
        {
            Fixture flat(3,3,10), ramp(3,3,0);
            for (int y=0;y<3;++y) for (int x=0;x<3;++x) ramp.set(x,y,x*60);
            Output out;
            require(v0_warp_blend(flat.image,ramp.image,matrix(1,0,0,0,1,0,0.25f,0,1),out.panorama,config) == ErrorCode::Success, "Projective mapping");
            expect_pixel(out.panorama,1,1,45); // B=(4/3,4/3), B intensity=80; average with 10.
            expect_pixel(out.panorama,2,1,10); // Inverse maps outside B.
        }
        {
            Fixture flat(1,1,9), rotated(3,2,0);
            rotated.set(0,0,41); rotated.set(2,1,73);
            Output out;
            require(v0_warp_blend(flat.image,rotated.image,matrix(0,-1,2,1,0,0,0,0,1),out.panorama,config) == ErrorCode::Success, "Rotation");
            require(out.panorama.image.width == 3 && out.panorama.image.height == 3, "Rotated bbox");
            expect_pixel(out.panorama,2,0,41); expect_pixel(out.panorama,1,2,73);
        }
        {
            Fixture small(1,1,12);
            Output out;
            require(v0_warp_blend(small.image,small.image,matrix(1,0,2,0,1,0,0,0,1),out.panorama,config) == ErrorCode::Success, "Disjoint images");
            expect_pixel(out.panorama,0,0,12); expect_pixel(out.panorama,1,0,0); expect_pixel(out.panorama,2,0,12);
        }
        {
            Output reference, negative, tiny;
            require(v0_warp_blend(a.image,b.image,identity(),reference.panorama,config) == ErrorCode::Success, "Reference");
            require(v0_warp_blend(a.image,b.image,matrix(-1,0,0,0,-1,0,0,0,-1),negative.panorama,config) == ErrorCode::Success, "Negative H");
            require(v0_warp_blend(a.image,b.image,matrix(1e-20f,0,0,0,1e-20f,0,0,0,1e-20f),tiny.panorama,config) == ErrorCode::Success, "Scaled H");
            for (int i=0;i<36;++i) {
                require(reference.panorama.image.data[i] == negative.panorama.image.data[i], "H and -H differ");
                require(reference.panorama.image.data[i] == tiny.panorama.image.data[i], "Scaled H differs");
            }
        }
        for (float shift : {-5e-7f, -2e-6f}) {
            Fixture small(2,1,5);
            Output out;
            require(v0_warp_blend(small.image,small.image,matrix(1,0,shift,0,1,0,0,0,1),out.panorama,config) == ErrorCode::Success, "Snap threshold");
            require(out.panorama.image.width == (shift > -1e-6f ? 2 : 3), "Snap bbox mismatch");
        }
        expect_error(a.image,b.image,Homography(),config,ErrorCode::DegenerateHomography);
        expect_error(a.image,b.image,matrix(1,0,0,1,0,0,0,0,1),config,ErrorCode::DegenerateHomography);
        expect_error(a.image,b.image,matrix(1,0,0,0,1,0,0,0,1e-14f),config,ErrorCode::DegenerateHomography);
        expect_error(a.image,b.image,matrix(1,0,0,0,1,0,1,0,-1),config,ErrorCode::NumericalFailure);
        expect_error(a.image,b.image,matrix(1,0,1,0,1,0,1,0,0),config,ErrorCode::NumericalFailure);
        Homography nan_h = identity(); nan_h.data[2] = std::nanf("");
        expect_error(a.image,b.image,nan_h,config,ErrorCode::NumericalFailure);
        Homography inf_h = identity(); inf_h.data[2] = HUGE_VALF;
        expect_error(a.image,b.image,inf_h,config,ErrorCode::NumericalFailure);
        expect_error(a.image,b.image,matrix(1,0,10001,0,1,0,0,0,1),config,ErrorCode::InvalidCanvas);
        Config limited = config; limited.max_canvas_pixels = 2;
        expect_error(a.image,b.image,identity(),limited,ErrorCode::InvalidCanvas);
        Config unset;
        expect_error(a.image,b.image,identity(),unset,ErrorCode::InvalidConfig);
        Config bad = config; bad.homography_epsilon = -1;
        expect_error(a.image,b.image,identity(),bad,ErrorCode::InvalidConfig);
        bad = config; bad.homography_epsilon = std::nanf("");
        expect_error(a.image,b.image,identity(),bad,ErrorCode::InvalidConfig);
        Image invalid = a.image; invalid.data = nullptr;
        expect_error(invalid,b.image,identity(),config,ErrorCode::InvalidImage);
        invalid = a.image; invalid.channels = 1;
        expect_error(invalid,b.image,identity(),config,ErrorCode::InvalidImage);
        invalid = a.image; invalid.stride = 1;
        expect_error(invalid,b.image,identity(),config,ErrorCode::InvalidImage);
        invalid = a.image; invalid.stride = static_cast<std::size_t>(-1);
        expect_error(invalid,b.image,identity(),config,ErrorCode::InvalidImage);
        {
            Panorama borrowed; borrowed.image = a.image;
            require(v0_warp_blend(a.image,b.image,identity(),borrowed,config) == ErrorCode::InvalidImage, "Accepted nonempty output");
            require(borrowed.image.data == a.image.data, "Lost existing buffer ownership");
        }
        fail_array_allocation = true;
        expect_error(a.image,b.image,identity(),config,ErrorCode::AllocationFailed);
        fail_array_allocation = false;
        std::cout << "PASS: " << checks << " assertions for S6 geometry, pixels, error handling and OOM\n";
        return 0;
    } catch (const std::exception& error) {
        fail_array_allocation = false;
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
