#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Tests for scripts/make_synthetic_pair.py, scripts/homography_error.py and scripts/homography_common.py.

Expected values come from crops and linear ramps whose answer is known without the code under test.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import homography_common  # noqa: E402
import homography_error  # noqa: E402
import make_synthetic_pair  # noqa: E402

WIDTH, HEIGHT = 96, 54


def texture(width, height, seed=16):
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8))


class HomographyTest(unittest.TestCase):
    def test_translation_matrix(self):
        matrix = make_synthetic_pair.case_homography("translation", 1280, 720)
        np.testing.assert_array_equal(matrix, [[1, 0, 703], [0, 1, 0], [0, 0, 1]])  # round(0.55 * 1279)

    def test_projective_matrix_is_normalised_and_keeps_b_in_front(self):
        for _, width, height in make_synthetic_pair.SIZES:
            matrix = make_synthetic_pair.case_homography("projective", width, height)
            self.assertAlmostEqual(np.max(np.abs(matrix)), 1.0)
            self.assertNotEqual(matrix[2, 0], 0.0)
            _, _, w = homography_common.project(matrix, [0, width - 1, width - 1, 0], [0, 0, height - 1, height - 1])
            self.assertTrue(np.all(w > 0))

    def test_projective_geometry_matches_across_sizes(self):
        # The B centre lands at the same place of A relative to the width, for every size.
        positions = []
        for _, width, height in make_synthetic_pair.SIZES:
            matrix = make_synthetic_pair.case_homography("projective", width, height)
            x, y, _ = homography_common.project(matrix, [(width - 1) / 2], [(height - 1) / 2])
            positions.append((x[0] / (width - 1), y[0] / (width - 1)))
        np.testing.assert_allclose(positions, [positions[0]] * 3, atol=1e-3)

    def test_unknown_case(self):
        with self.assertRaises(make_synthetic_pair.SyntheticError):
            make_synthetic_pair.case_homography("rotation", WIDTH, HEIGHT)


class BilinearTest(unittest.TestCase):
    def test_reproduces_a_linear_ramp(self):
        ys, xs = np.mgrid[0:20, 0:30].astype(np.float64)
        scene = np.stack([2.0 * xs + 3.0 * ys + 1.0, xs, 100.0 - ys], axis=-1)
        px = np.array([0.0, 4.25, 28.9, 29.0])
        py = np.array([0.0, 7.5, 0.1, 19.0])
        values = make_synthetic_pair.sample_bilinear(scene, px, py)
        expected = np.stack([2.0 * px + 3.0 * py + 1.0, px, 100.0 - py], axis=-1)
        np.testing.assert_allclose(values, expected, atol=1e-12)

    def test_rejects_points_outside(self):
        scene = np.zeros((4, 5, 3))
        for px, py in (([-0.01], [0.0]), ([4.01], [0.0]), ([0.0], [3.5]), ([np.nan], [0.0])):
            with self.assertRaises(make_synthetic_pair.SyntheticError):
                make_synthetic_pair.sample_bilinear(scene, np.array(px), np.array(py))


class MakePairTest(unittest.TestCase):
    def test_translation_pair_is_two_crops_of_one_scene(self):
        matrix = make_synthetic_pair.case_homography("translation", WIDTH, HEIGHT)
        shift = int(matrix[0, 2])
        left, right, info = make_synthetic_pair.make_pair(texture(600, 300), matrix, WIDTH, HEIGHT)
        self.assertEqual(left.shape, (HEIGHT, WIDTH, 3))
        self.assertEqual(right.shape, (HEIGHT, WIDTH, 3))
        np.testing.assert_array_equal(left[:, shift:], right[:, :WIDTH - shift])
        offset_x, offset_y = info["a_offset_in_scene"]
        self.assertEqual((offset_x, offset_y), (make_synthetic_pair.MARGIN, make_synthetic_pair.MARGIN))
        self.assertAlmostEqual(info["overlap_fraction"], (WIDTH - shift) / WIDTH, delta=0.05)

    def test_projective_pair_samples_the_scene_through_h(self):
        # A linear ramp scene: B must equal the ramp evaluated at H(x) + offset, up to rounding.
        matrix = make_synthetic_pair.case_homography("projective", WIDTH, HEIGHT)
        bounds = make_synthetic_pair.scene_bounds(matrix, WIDTH, HEIGHT)
        scene_w, scene_h = bounds[2] - bounds[0] + 1, bounds[3] - bounds[1] + 1
        ys, xs = np.mgrid[0:scene_h, 0:scene_w].astype(np.float64)
        ramp = np.stack([xs * 200.0 / scene_w, ys * 200.0 / scene_h, np.full_like(xs, 77.0)], axis=-1)
        right = make_synthetic_pair.warp_right(ramp, matrix, WIDTH, HEIGHT, -bounds[0], -bounds[1])
        grid_x, grid_y = np.meshgrid(np.arange(WIDTH, dtype=np.float64), np.arange(HEIGHT, dtype=np.float64))
        px, py, _ = homography_common.project(matrix, grid_x, grid_y)
        expected = np.stack([(px - bounds[0]) * 200.0 / scene_w, (py - bounds[1]) * 200.0 / scene_h,
                             np.full_like(px, 77.0)], axis=-1)
        self.assertLessEqual(np.max(np.abs(right.astype(np.float64) - expected)), 0.5 + 1e-9)

    def test_source_too_small_is_rejected(self):
        matrix = make_synthetic_pair.case_homography("translation", WIDTH, HEIGHT)
        with self.assertRaises(make_synthetic_pair.SyntheticError):
            make_synthetic_pair.make_pair(texture(120, 300), matrix, WIDTH, HEIGHT)

    def test_horizon_is_rejected(self):
        matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0 / 50.0, 0.0, 1.0]])
        with self.assertRaises(make_synthetic_pair.SyntheticError):
            make_synthetic_pair.scene_bounds(matrix, WIDTH, HEIGHT)

    def test_generate_writes_png_and_truth(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.jpg"
            texture(800, 400).save(source, quality=95)
            sizes = [("tiny", WIDTH, HEIGHT)]
            written = make_synthetic_pair.generate(source, Path(folder) / "out", make_synthetic_pair.CASES, sizes)
            self.assertEqual([(case, name) for case, name, _ in written],
                             [("translation", "tiny"), ("projective", "tiny")])
            for case in make_synthetic_pair.CASES:
                case_dir = Path(folder) / "out" / case
                for side in ("left", "right"):
                    with Image.open(case_dir / f"tiny_{side}.png") as image:
                        self.assertEqual((image.format, image.mode, image.size), ("PNG", "RGB", (WIDTH, HEIGHT)))
                truth = json.loads((case_dir / "tiny_truth.json").read_text(encoding="utf-8"))
                self.assertEqual((truth["width"], truth["height"], truth["direction"]), (WIDTH, HEIGHT, "B->A"))
                np.testing.assert_allclose(truth["H_gt"],
                                           make_synthetic_pair.case_homography(case, WIDTH, HEIGHT).reshape(-1))


class ErrorMetricTest(unittest.TestCase):
    def setUp(self):
        self.matrix = make_synthetic_pair.case_homography("projective", WIDTH, HEIGHT)
        self.truth = {"width": WIDTH, "height": HEIGHT, "H_gt": self.matrix.reshape(-1).tolist()}

    def test_exact_estimate_has_zero_error_up_to_scale_and_sign(self):
        for scale in (1.0, 3.5, -2.0):
            result = homography_error.evaluate(self.truth, scale * self.matrix)
            self.assertLess(result["max_px"], 1e-9)
        self.assertGreater(result["points"], 100)
        self.assertLess(result["points"], 400)  # part of B lies outside A

    def test_one_pixel_shift(self):
        shifted = make_synthetic_pair.translation(0.0, 1.0) @ self.matrix
        result = homography_error.evaluate(self.truth, shifted)
        self.assertAlmostEqual(result["rmse_px"], 1.0, places=9)
        self.assertAlmostEqual(result["max_px"], 1.0, places=9)
        self.assertAlmostEqual(result["nrmse"], 1.0 / np.hypot(WIDTH, HEIGHT), places=12)

    def test_check_points_ignore_h_est(self):
        xs, ys = homography_error.check_points(self.matrix, WIDTH, HEIGHT)
        gx, gy, _ = homography_common.project(self.matrix, xs, ys)
        self.assertTrue(np.all((gx >= 0) & (gx <= WIDTH - 1) & (gy >= 0) & (gy <= HEIGHT - 1)))

    def test_no_overlap_fails(self):
        truth = dict(self.truth, H_gt=make_synthetic_pair.translation(500.0, 0.0).reshape(-1).tolist())
        with self.assertRaises(homography_error.EvaluationError):
            homography_error.evaluate(truth, np.eye(3))

    def test_estimate_through_horizon_fails(self):
        bad = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0 / 40.0, 0.0, 1.0]])
        with self.assertRaises(homography_error.EvaluationError):
            homography_error.evaluate(self.truth, bad)

    def test_parse_estimate_takes_the_h_line(self):
        log = ("[debug] S4 matches=10\n[debug] H(B->A)=1 0 2.5 0 1 -1e-3 0 0 1\n"
               "[debug] S6 canvas=10x10 offset=(0,0)\n")
        np.testing.assert_array_equal(homography_error.parse_estimate(log),
                                      [[1, 0, 2.5], [0, 1, -1e-3], [0, 0, 1]])
        for bad in ("[debug] S4 matches=10\n", "[debug] H(B->A)=1 2 3\n", "[debug] H(B->A)=1 0 0 0 1 0 0 0 nan\n"):
            with self.assertRaises(homography_error.EvaluationError):
                homography_error.parse_estimate(bad)

    def test_cli_reads_truth_and_log(self):
        with tempfile.TemporaryDirectory() as folder:
            truth_path = Path(folder) / "truth.json"
            homography_common.save_truth(truth_path, dict(self.truth, case="projective", size="tiny"))
            log_path = Path(folder) / "stitch.log"
            values = " ".join(repr(float(value)) for value in self.matrix.reshape(-1))
            log_path.write_text(f"[debug] H(B->A)={values}\n", encoding="utf-8")
            self.assertEqual(homography_error.main(["--truth", str(truth_path), "--log", str(log_path)]), 0)
            self.assertEqual(homography_error.main(["--truth", str(truth_path), "--log", str(Path(folder) / "none")]), 1)


if __name__ == "__main__":
    unittest.main()
