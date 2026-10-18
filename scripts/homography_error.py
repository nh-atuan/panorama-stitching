#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Homography error of stitch against a synthetic pair (docs/stages/s5-homography.md, section 5.3).

Q is a fixed 20x20 grid over B, kept only where H_gt lands inside A; it never depends on H_est.
e(q) = |project(H_est, q) - project(H_gt, q)|, reported as RMSE and Max in pixels of A and as
NRMSE = RMSE / diagonal of A. H_est is the float32 H that stitch prints with --debug.

Example:
  ./stitch results/synthetic/translation/small_left.png results/synthetic/translation/small_right.png \\
      results/synthetic/translation/small_pano.png --version 0 --runs 1 --debug 2> small.log
  python scripts/homography_error.py --truth results/synthetic/translation/small_truth.json --log small.log
"""

import argparse
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from homography_common import as_matrix, load_truth, project  # noqa: E402

GRID = 20
H_PREFIX = "[debug] H(B->A)="


class EvaluationError(Exception):
    pass


def parse_estimate(log_text):
    """The 9 values of the last H(B->A) line printed by stitch --debug."""
    lines = [line for line in log_text.splitlines() if line.startswith(H_PREFIX)]
    if not lines:
        raise EvaluationError(f"no '{H_PREFIX}' line in the stitch log")
    values = lines[-1][len(H_PREFIX):].split()
    if len(values) != 9:
        raise EvaluationError(f"expected 9 values after '{H_PREFIX}', got {len(values)}")
    try:
        return as_matrix([float(value) for value in values])
    except ValueError as error:
        raise EvaluationError(f"bad H line: {error}") from error


def check_points(truth_matrix, width, height):
    """Grid points of B whose ground-truth image lies inside A."""
    grid_x, grid_y = np.meshgrid(np.linspace(0, width - 1, GRID), np.linspace(0, height - 1, GRID))
    xs, ys = grid_x.reshape(-1), grid_y.reshape(-1)
    px, py, w = project(truth_matrix, xs, ys)
    keep = (w > 0) & (px >= 0) & (px <= width - 1) & (py >= 0) & (py <= height - 1)
    return xs[keep], ys[keep]


def evaluate(truth, estimate):
    """Error metrics of H_est against the truth dict written by make_synthetic_pair.py."""
    width, height = int(truth["width"]), int(truth["height"])
    truth_matrix = as_matrix(truth["H_gt"])
    xs, ys = check_points(truth_matrix, width, height)
    if xs.size == 0:
        raise EvaluationError("no check point of B lands inside A")
    gt_x, gt_y, _ = project(truth_matrix, xs, ys)
    est_x, est_y, est_w = project(estimate, xs, ys)
    # H is defined up to scale, including sign: every check point must sit on one side of the horizon.
    if not (np.all(est_w > 0) or np.all(est_w < 0)) or not np.all(np.isfinite(est_x + est_y)):
        raise EvaluationError("H_est sends part of the check points through the horizon")
    errors = np.hypot(est_x - gt_x, est_y - gt_y)
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    return {
        "points": int(xs.size),
        "grid_points": GRID * GRID,
        "rmse_px": rmse,
        "max_px": float(errors.max()),
        "nrmse": rmse / math.hypot(width, height),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--truth", required=True, help="<size>_truth.json from make_synthetic_pair.py")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--log", help="stderr of stitch --debug")
    source.add_argument("--h", nargs=9, type=float, metavar="h", help="H_est as 9 row-major values")
    args = parser.parse_args(argv)
    try:
        truth = load_truth(args.truth)
        if args.log:
            estimate = parse_estimate(Path(args.log).read_text(encoding="utf-8", errors="replace"))
        else:
            estimate = as_matrix(args.h)
        result = evaluate(truth, estimate)
    except (OSError, ValueError, EvaluationError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    label = f"{truth.get('case', '?')}/{truth.get('size', '?')}"
    print(f"{label}: points={result['points']}/{result['grid_points']} "
          f"rmse_px={result['rmse_px']:.6f} max_px={result['max_px']:.6f} nrmse={result['nrmse']:.3e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
