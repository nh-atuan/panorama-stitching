#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# Adapted from: Vigna, SplitMix64 reference, https://prng.di.unimi.it/splitmix64.c, accessed 2026-10-16;
# Calonder et al., "BRIEF: Binary Robust Independent Elementary Features", ECCV 2010,
# https://www.cs.ubc.ca/~lowe/525/papers/calonder_eccv10.pdf, accessed 2026-10-16
# Changes: SplitMix64 ported to Python; BRIEF sampling G II drawn with Box-Muller, rounded,
# clamped to the patch, and filtered for identical points and repeated or mirrored tests.

"""Generate (or check) the fixed 256-test BRIEF pattern stored in src/common/brief_pattern.cpp."""

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "src" / "common" / "brief_pattern.cpp"
MASK = (1 << 64) - 1
SEED = 16
TESTS = 256
PATCH_RADIUS = 15
SIGMA = 31.0 / 5.0  # BRIEF G II: sigma^2 = S^2 / 25 for an S x S patch, S = 31.


class SplitMix64:
    def __init__(self, seed):
        self.state = seed & MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def uniform(self):
        # 53 random bits mapped to the open interval (0, 1), so log() never sees 0.
        return ((self.next() >> 11) + 0.5) / float(1 << 53)


def gaussian_pairs(rng):
    while True:
        radius = math.sqrt(-2.0 * math.log(rng.uniform()))
        angle = 2.0 * math.pi * rng.uniform()
        yield radius * math.cos(angle)
        yield radius * math.sin(angle)


def to_offset(value):
    offset = math.floor(SIGMA * value + 0.5)
    return max(-PATCH_RADIUS, min(PATCH_RADIUS, offset))


def generate():
    normals = gaussian_pairs(SplitMix64(SEED))
    tests, seen = [], set()
    while len(tests) < TESTS:
        ax, ay, bx, by = (to_offset(next(normals)) for _ in range(4))
        first, second = (ax, ay), (bx, by)
        if first == second or (first, second) in seen or (second, first) in seen:
            continue
        seen.add((first, second))
        tests.append((ax, ay, bx, by))
    return tests


def render(tests):
    lines = [
        "// Authors: Nguyen Ho Anh Tuan (23120185)",
        "// Adapted from: Calonder et al., \"BRIEF: Binary Robust Independent Elementary Features\",",
        "// ECCV 2010, https://www.cs.ubc.ca/~lowe/525/papers/calonder_eccv10.pdf, accessed 2026-10-16",
        "// Changes: Group 16 pattern drawn once by tests/tools/tool_gen_brief_pattern.py (sampling G II,",
        f"// sigma = 31/5, SplitMix64 seed {SEED}); generated file, do not edit by hand.",
        "",
        "#include \"common/brief_pattern.h\"",
        "",
        "namespace panorama {",
        "",
        "const BriefTest kBriefPattern[kBriefTests] = {",
    ]
    for index, (ax, ay, bx, by) in enumerate(tests):
        lines.append(f"    {{{ax:3d}, {ay:3d}, {bx:3d}, {by:3d}}},  // {index}")
    lines += ["};", "", "}  // namespace panorama", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="compare the committed table with a fresh generation")
    args = parser.parse_args()
    text = render(generate())
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"MISMATCH: {OUTPUT.relative_to(ROOT).as_posix()} differs from the generator output")
            return 1
        print(f"OK: {OUTPUT.name} matches the generator ({TESTS} tests, seed {SEED})")
        return 0
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"Wrote {OUTPUT.relative_to(ROOT).as_posix()} ({TESTS} tests, seed {SEED})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
