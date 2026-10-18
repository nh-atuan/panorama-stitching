#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Build synthetic pairs with a known homography (docs/stages/s5-homography.md, section 5.2).

A scene C is cut from a real photo and downscaled with Lanczos (never upscaled). A is a crop of C and
B(x) = C(project(H_gt, x)), sampled with the bilinear interpolation below, so H_gt maps B to A.
Each size is generated directly. Output: <out>/<case>/<size>_left.png (A), <size>_right.png (B) and
<size>_truth.json (H_gt and how the pair was made).

Example:
  python scripts/make_synthetic_pair.py --source raw/tuan/standard2_left.jpg --out results/synthetic
"""

import argparse
import hashlib
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset_common import SIZES, load_oriented  # noqa: E402
from homography_common import project, save_truth  # noqa: E402

CASES = ("translation", "projective")
OVERLAP_SHIFT = 0.55   # B starts at round(0.55 * (W - 1)) in A, about 45% overlap
ROTATION_DEG = 3.0     # projective case, in coordinates normalised by W - 1
PERSPECTIVE = (0.10, 0.05)
VERTICAL_SHIFT = 0.02
MARGIN = 2             # pixels of C kept around every sampled position
ROWS_PER_CHUNK = 256


class SyntheticError(Exception):
    pass


def translation(dx, dy):
    return np.array([[1.0, 0.0, dx], [0.0, 1.0, dy], [0.0, 0.0, 1.0]])


def case_homography(case, width, height):
    """H_gt (B -> A) in pixels for one case and size, scaled so that max |h| is 1."""
    if case == "translation":
        return translation(round(OVERLAP_SHIFT * (width - 1)), 0.0)
    if case != "projective":
        raise SyntheticError(f"unknown case '{case}'")
    # Built in coordinates divided by W - 1 so every size gets the same geometry.
    unit = float(width - 1)
    centre_x, centre_y = 0.5, 0.5 * (height - 1) / unit
    angle = math.radians(ROTATION_DEG)
    rotation = np.array([[math.cos(angle), -math.sin(angle), 0.0],
                         [math.sin(angle), math.cos(angle), 0.0],
                         [0.0, 0.0, 1.0]])
    perspective = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [PERSPECTIVE[0], PERSPECTIVE[1], 1.0]])
    normalised = (translation(OVERLAP_SHIFT, VERTICAL_SHIFT) @ translation(centre_x, centre_y)
                  @ rotation @ perspective @ translation(-centre_x, -centre_y))
    to_unit = np.diag([1.0 / unit, 1.0 / unit, 1.0])
    matrix = np.linalg.inv(to_unit) @ normalised @ to_unit
    return matrix / np.max(np.abs(matrix))


def sample_bilinear(scene, xs, ys):
    """Bilinear samples of scene (H x W x 3 float) at points inside [0, W-1] x [0, H-1]."""
    height, width = scene.shape[:2]
    if (np.any(xs < 0) or np.any(ys < 0) or np.any(xs > width - 1) or np.any(ys > height - 1)
            or not np.all(np.isfinite(xs)) or not np.all(np.isfinite(ys))):
        raise SyntheticError("sample position outside the scene")
    x0 = np.floor(xs).astype(np.int64)
    y0 = np.floor(ys).astype(np.int64)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    fx = (xs - x0)[..., None]
    fy = (ys - y0)[..., None]
    top = scene[y0, x0] * (1.0 - fx) + scene[y0, x1] * fx
    bottom = scene[y1, x0] * (1.0 - fx) + scene[y1, x1] * fx
    return top * (1.0 - fy) + bottom * fy


def scene_bounds(matrix, width, height):
    """Integer box (x_min, y_min, x_max, y_max) in A pixels covering A and the projection of B."""
    xs = np.array([0, width - 1, width - 1, 0], dtype=np.float64)
    ys = np.array([0, 0, height - 1, height - 1], dtype=np.float64)
    px, py, w = project(matrix, xs, ys)
    # w is affine in (x, y), so positive corners mean positive w over the whole of B.
    if np.any(w <= 0) or not np.all(np.isfinite(px)) or not np.all(np.isfinite(py)):
        raise SyntheticError("H_gt sends part of B through the horizon")
    all_x = np.concatenate([xs, px])
    all_y = np.concatenate([ys, py])
    return (int(math.floor(all_x.min())) - MARGIN, int(math.floor(all_y.min())) - MARGIN,
            int(math.ceil(all_x.max())) + MARGIN, int(math.ceil(all_y.max())) + MARGIN)


def build_scene(source, scene_width, scene_height):
    """Centred crop of the source with the scene's aspect ratio, downscaled to the scene size."""
    scale = min(source.width / scene_width, source.height / scene_height)
    if scale < 1.0:
        raise SyntheticError(f"source {source.width}x{source.height} is too small for a "
                             f"{scene_width}x{scene_height} scene without upscaling")
    crop_w, crop_h = scene_width * scale, scene_height * scale
    # The limiting side spans the whole source; clamping only absorbs rounding of crop_w, crop_h.
    left = max(0.0, (source.width - crop_w) / 2.0)
    top = max(0.0, (source.height - crop_h) / 2.0)
    box = (left, top, min(float(source.width), left + crop_w), min(float(source.height), top + crop_h))
    scene = source.resize((scene_width, scene_height), Image.Resampling.LANCZOS, box=box)
    return np.asarray(scene, dtype=np.uint8), box, scale


def warp_right(scene, matrix, width, height, offset_x, offset_y):
    """B(x, y) = scene(project(H, (x, y)) + offset), rounded to uint8."""
    scene_f = scene.astype(np.float64)
    right = np.empty((height, width, 3), dtype=np.uint8)
    xs = np.arange(width, dtype=np.float64)
    for row in range(0, height, ROWS_PER_CHUNK):
        ys = np.arange(row, min(row + ROWS_PER_CHUNK, height), dtype=np.float64)
        grid_x, grid_y = np.meshgrid(xs, ys)
        px, py, _ = project(matrix, grid_x, grid_y)
        values = sample_bilinear(scene_f, px + offset_x, py + offset_y)
        right[row:row + len(ys)] = np.clip(np.rint(values), 0, 255).astype(np.uint8)
    return right


def overlap_fraction(matrix, width, height, step=4):
    """Share of B pixels (on a grid with the given step) that land inside A."""
    grid_x, grid_y = np.meshgrid(np.arange(0, width, step, dtype=np.float64),
                                 np.arange(0, height, step, dtype=np.float64))
    px, py, _ = project(matrix, grid_x, grid_y)
    inside = (px >= 0) & (px <= width - 1) & (py >= 0) & (py <= height - 1)
    return float(inside.mean())


def make_pair(source, matrix, width, height):
    """Return (A, B, info) for a source PIL RGB image and H_gt in pixels."""
    x_min, y_min, x_max, y_max = scene_bounds(matrix, width, height)
    scene, box, scale = build_scene(source, x_max - x_min + 1, y_max - y_min + 1)
    offset_x, offset_y = -x_min, -y_min
    left = scene[offset_y:offset_y + height, offset_x:offset_x + width].copy()
    right = warp_right(scene, matrix, width, height, offset_x, offset_y)
    info = {
        "scene_size": [int(scene.shape[1]), int(scene.shape[0])],
        "a_offset_in_scene": [offset_x, offset_y],
        "source_box": [round(value, 3) for value in box],
        "source_scale": round(scale, 6),
        "overlap_fraction": round(overlap_fraction(matrix, width, height), 4),
    }
    return left, right, info


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def generate(source_path, out_dir, cases, sizes):
    source, _, _ = load_oriented(source_path)
    source = source.convert("RGB")
    source_hash = sha256(source_path)
    written = []
    for case in cases:
        for name, width, height in sizes:
            matrix = case_homography(case, width, height)
            left, right, info = make_pair(source, matrix, width, height)
            folder = Path(out_dir) / case
            folder.mkdir(parents=True, exist_ok=True)
            Image.fromarray(left).save(folder / f"{name}_left.png")
            Image.fromarray(right).save(folder / f"{name}_right.png")
            truth = {
                "case": case, "size": name, "width": width, "height": height,
                "direction": "B->A", "H_gt": [float(value) for value in matrix.reshape(-1)],
                "source": Path(source_path).name, "source_sha256": source_hash,
                "resampling": "Lanczos downscale of the source to C; bilinear sampling of C for B",
            }
            truth.update(info)
            save_truth(folder / f"{name}_truth.json", truth)
            written.append((case, name, info["overlap_fraction"]))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="real photo used as the scene")
    parser.add_argument("--out", required=True, help="output folder, kept out of Git")
    parser.add_argument("--case", choices=CASES + ("all",), default="all")
    parser.add_argument("--size", choices=[name for name, _, _ in SIZES] + ["all"], default="all")
    args = parser.parse_args(argv)
    cases = CASES if args.case == "all" else (args.case,)
    sizes = [size for size in SIZES if args.size in ("all", size[0])]
    try:
        written = generate(args.source, args.out, cases, sizes)
    except (OSError, SyntheticError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    for case, name, overlap in written:
        print(f"{case}/{name}: overlap={overlap:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
