#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Shared helpers for the synthetic homography pair (docs/stages/s5-homography.md, section 5).

H is a 3x3 row-major matrix mapping B pixels to A pixels (docs/interface.md, section 5); pixel
centres sit on integer coordinates.
"""

import json

import numpy as np


def as_matrix(values):
    """3x3 float64 matrix from 9 row-major values or a 3x3 nested list."""
    matrix = np.asarray(values, dtype=np.float64).reshape(3, 3)
    if not np.all(np.isfinite(matrix)):
        raise ValueError("homography has non-finite entries")
    return matrix


def project(matrix, xs, ys):
    """Apply H to points (xs, ys). Returns (x, y, w); x and y are NaN where w is 0."""
    xs = np.asarray(xs, dtype=np.float64)
    ys = np.asarray(ys, dtype=np.float64)
    u = matrix[0, 0] * xs + matrix[0, 1] * ys + matrix[0, 2]
    v = matrix[1, 0] * xs + matrix[1, 1] * ys + matrix[1, 2]
    w = matrix[2, 0] * xs + matrix[2, 1] * ys + matrix[2, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.where(w != 0, u / w, np.nan)
        y = np.where(w != 0, v / w, np.nan)
    return x, y, w


def save_truth(path, truth):
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(truth, stream, indent=2)
        stream.write("\n")


def load_truth(path):
    with open(path, encoding="utf-8") as stream:
        truth = json.load(stream)
    for key in ("width", "height", "H_gt"):
        if key not in truth:
            raise ValueError(f"{path}: missing '{key}'")
    return truth
