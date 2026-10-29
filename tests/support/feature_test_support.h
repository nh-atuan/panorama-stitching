// Authors: Nguyen Ho Anh Tuan (23120185)
// External source: none

// Shared helpers for the S2/S3 test binaries. Include from exactly one source file per
// binary: it replaces the global allocation operators to inject std::bad_alloc.

#ifndef GROUP16_FEATURE_TEST_SUPPORT_H
#define GROUP16_FEATURE_TEST_SUPPORT_H

#include "common/common.h"
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
#include <vector>

// While set, every global allocation throws, so stage buffers fail deterministically.
static bool fail_allocations = false;

static void* checked_malloc(std::size_t size) {
    if (fail_allocations) throw std::bad_alloc();
    void* result = std::malloc(size ? size : 1);
    if (!result) throw std::bad_alloc();
    return result;
}
void* operator new(std::size_t size) { return checked_malloc(size); }
void* operator new[](std::size_t size) { return checked_malloc(size); }
void operator delete(void* pointer) noexcept { std::free(pointer); }
void operator delete[](void* pointer) noexcept { std::free(pointer); }

static int checks = 0;
inline void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
    ++checks;
}

// Deterministic 64-bit LCG (Knuth MMIX constants); tests only.
struct TestRandom {
    std::uint64_t state;
    explicit TestRandom(std::uint64_t seed) : state(seed) {}
    std::uint32_t next() {
        state = state * 6364136223846793005ULL + 1442695040888963407ULL;
        return static_cast<std::uint32_t>(state >> 33);
    }
    float unit() { return static_cast<float>(next() % 1000001u) / 1000000.0f; }
    std::int32_t below(std::int32_t n) { return static_cast<std::int32_t>(next() % static_cast<std::uint32_t>(n)); }
};

// Gray image over an exact-size buffer; `padding` extra floats per row are filled with a
// sentinel so tests can verify that the stage never reads them as pixels.
struct GrayFixture {
    std::vector<float> storage;
    panorama::GrayImage image;
    GrayFixture(std::int32_t width, std::int32_t height, std::int32_t padding = 0,
                float value = 0.0f)
        : storage(static_cast<std::size_t>(width + padding) * static_cast<std::size_t>(height),
                  -1000.0f) {
        image.data = storage.data();
        image.width = width;
        image.height = height;
        image.channels = 1;
        image.stride = static_cast<std::size_t>(width + padding) * sizeof(float);
        fill(value);
    }
    float& at(std::int32_t x, std::int32_t y) {
        return storage[static_cast<std::size_t>(y) * (image.stride / sizeof(float)) +
                       static_cast<std::size_t>(x)];
    }
    float at(std::int32_t x, std::int32_t y) const {
        return storage[static_cast<std::size_t>(y) * (image.stride / sizeof(float)) +
                       static_cast<std::size_t>(x)];
    }
    void fill(float value) {
        for (std::int32_t y = 0; y < image.height; ++y)
            for (std::int32_t x = 0; x < image.width; ++x) at(x, y) = value;
    }
    void rect(std::int32_t x0, std::int32_t y0, std::int32_t x1, std::int32_t y1, float value) {
        for (std::int32_t y = y0; y <= y1; ++y)
            for (std::int32_t x = x0; x <= x1; ++x)
                if (x >= 0 && y >= 0 && x < image.width && y < image.height) at(x, y) = value;
    }
};

// Random axis-aligned rectangles: a texture with many corners and no symmetry.
inline void paint_rectangles(GrayFixture& fixture, TestRandom& random, int count) {
    fixture.fill(0.5f);
    for (int i = 0; i < count; ++i) {
        const std::int32_t x0 = random.below(fixture.image.width);
        const std::int32_t y0 = random.below(fixture.image.height);
        const std::int32_t w = 3 + random.below(20);
        const std::int32_t h = 3 + random.below(20);
        fixture.rect(x0, y0, x0 + w, y0 + h, random.unit());
    }
}

#endif  // GROUP16_FEATURE_TEST_SUPPORT_H
