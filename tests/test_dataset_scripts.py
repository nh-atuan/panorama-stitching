#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Tests for scripts/prepare_dataset.py, scripts/check_pairs.py and scripts/dataset_common.py on synthetic photos."""

import csv
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_pairs  # noqa: E402
import dataset_common  # noqa: E402
import prepare_dataset  # noqa: E402

ORIENTATION, DATETIME_ORIGINAL, MAKE, MODEL = 274, 36867, 271, 272


def scene(width, height, seed=16):
    """Smooth random texture: blocks of random gray levels, upscaled, so features survive resizing."""
    rng = np.random.default_rng(seed)
    blocks = rng.integers(0, 256, size=(height // 40 + 1, width // 40 + 1, 3), dtype=np.uint8)
    return Image.fromarray(blocks).resize((width, height), Image.Resampling.BILINEAR)


def save_jpeg(image, path, orientation=None, taken=None, gps=False):
    exif = Image.Exif()
    exif[MAKE] = "TestMake"
    exif[MODEL] = "TestPhone"
    if orientation:
        exif[ORIENTATION] = orientation
    # Sub-IFDs are assigned as dicts; Pillow writes each one behind its pointer tag.
    if taken:
        exif[dataset_common.EXIF_IFD] = {DATETIME_ORIGINAL: taken.strftime("%Y:%m:%d %H:%M:%S")}
    if gps:
        exif[dataset_common.GPS_IFD] = {1: "N", 2: (10.0, 45.0, 0.0)}
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=90, exif=exif)


class CropAndNamesTest(unittest.TestCase):
    def test_crop_box(self):
        self.assertEqual(dataset_common.crop_box_16_9(4032, 3024), (0, 378, 4032, 2646))
        self.assertEqual(dataset_common.crop_box_16_9(8160, 6144), (0, 777, 8160, 5367))
        self.assertEqual(dataset_common.crop_box_16_9(3840, 2160), (0, 0, 3840, 2160))
        left, top, right, bottom = dataset_common.crop_box_16_9(5000, 2000)  # wider than 16:9
        self.assertEqual(((right - left) * 9, bottom - top <= 2000), ((bottom - top) * 16, True))
        self.assertEqual(left, (5000 - (right - left)) // 2)

    def test_pair_paths(self):
        left, right = dataset_common.pair_paths("raw", "tuan-standard1-b2")
        self.assertEqual(left.as_posix(), "raw/tuan/standard1_left_b2.jpg")
        self.assertEqual(right.as_posix(), "raw/tuan/standard1_right_b2.jpg")
        with self.assertRaises(ValueError):
            dataset_common.pair_paths("raw", "tuan_standard1")

    def test_scan_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ("standard1_left.jpg", "standard1_right.jpg", "standard1_left_b1.jpg",
                         "standard1_right_b1.jpg", "challenge_left.HEIC", "challenge_right.HEIC",
                         "standard2_1.jpg", "standard3_left", "standard3_right"):
                (folder / name).write_bytes(b"x")
            pairs, unknown = dataset_common.scan_member(folder, "de")
            codes = sorted(pair.code for pair in pairs)
            self.assertEqual(codes, ["de-challenge?", "de-standard1", "de-standard1-b1", "de-standard3"])
            self.assertEqual(unknown, ["standard2_1.jpg"])
            heic = next(pair for pair in pairs if pair.kind == "challenge")
            self.assertEqual(len(heic.naming_problems), 2)
            self.assertIn("thiếu số thứ tự", heic.naming_problems[0])
            plain = next(pair for pair in pairs if pair.number == "3")
            self.assertIn("không có phần mở rộng", plain.naming_problems[0])
            self.assertTrue(all(not p.naming_problems for p in pairs if p.number == "1"))


class PrepareDatasetTest(unittest.TestCase):
    def test_outputs_sizes_orientation_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, out = Path(tmp) / "raw", Path(tmp) / "dataset"
            # Stored portrait with orientation 6 (rotate 90 degrees clockwise to view): landscape after EXIF.
            stored = scene(4000, 3000).transpose(Image.Transpose.ROTATE_90)
            save_jpeg(stored, raw / "tuan" / "standard1_left.jpg", orientation=6, gps=True)
            save_jpeg(stored, raw / "tuan" / "standard1_right.jpg", orientation=6, gps=True)
            save_jpeg(scene(4032, 3024, 3), raw / "tuan" / "challenge1_left.jpg")
            save_jpeg(scene(4032, 3024, 4), raw / "tuan" / "challenge1_right.jpg")
            code = prepare_dataset.main(["--raw", str(raw), "--out", str(out),
                                         "--pair", "site1=tuan-standard1", "--pair", "challenge=tuan-challenge1"])
            self.assertEqual(code, 0)
            for site in ("site1", "challenge"):
                for size, width, height in dataset_common.SIZES:
                    for side in ("left", "right"):
                        with Image.open(out / site / f"{size}_{side}.jpg") as image:
                            self.assertEqual(image.size, (width, height))
                            self.assertEqual(image.format, "JPEG")
                            self.assertEqual(len(image.getexif()), 0, "output keeps no EXIF")
            # Orientation was applied: the large image matches the upright scene, not the stored one.
            expected = np.asarray(scene(4000, 3000).crop(dataset_common.crop_box_16_9(4000, 3000))
                                  .resize((1280, 720)).convert("L"), dtype=float)
            with Image.open(out / "site1" / "small_left.jpg") as image:
                actual = np.asarray(image.convert("L"), dtype=float)
            self.assertLess(np.abs(actual - expected).mean(), 6.0)
            with open(out / "manifest.csv", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 12)
            self.assertEqual(rows[0]["crop_box"], "0 375 4000 2625")
            self.assertEqual(len(rows[0]["sha256"]), 64)

    def test_rejects_invalid_pairs_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, out = Path(tmp) / "raw", Path(tmp) / "dataset"
            save_jpeg(scene(3000, 2000), raw / "tuan" / "standard1_left.jpg")
            save_jpeg(scene(3000, 2000), raw / "tuan" / "standard1_right.jpg")
            save_jpeg(scene(4032, 3024), raw / "tuan" / "standard2_left.jpg")
            save_jpeg(scene(4000, 3000), raw / "tuan" / "standard2_right.jpg")
            save_jpeg(scene(4032, 3024), raw / "tuan" / "standard3_left.jpg")
            save_jpeg(scene(4032, 3024), raw / "tuan" / "standard3_right.jpg")
            cases = [["--pair", "site1=tuan-standard1"],          # crop below 3840x2160
                     ["--pair", "site1=tuan-standard2"],          # left and right sizes differ
                     ["--pair", "site1=tuan-standard9"],          # missing files
                     ["--pair", "site1=tuan-standard3", "--pair", "site1=tuan-standard3"],
                     ["--pair", "nowhere=tuan-standard3"],
                     ["--pair", "site2=tuan-standard3", "--pair", "site1=tuan-standard1"]]
            for case in cases:
                self.assertEqual(prepare_dataset.main(["--raw", str(raw), "--out", str(out), *case]), 1, case)
                self.assertFalse(out.exists(), f"nothing is written when {case} fails")


class CheckPairsTest(unittest.TestCase):
    def test_overlap_estimate(self):
        world = scene(2600, 1000, 7)
        width = 1600
        for overlap in (0.3, 0.4, 0.5):
            shift = round(width * (1 - overlap))
            left = world.crop((0, 0, width, 900))
            right = world.crop((shift, 0, shift + width, 900))
            estimate, score = check_pairs.estimate_overlap(left, right)
            self.assertAlmostEqual(estimate, overlap, delta=0.03)
            self.assertGreater(score, check_pairs.MIN_SHIFT_SCORE)

    def test_check_pair_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "tuan"
            world = scene(7000, 2400, 9)
            t0 = datetime(2026, 10, 7, 12, 0, 0)
            save_jpeg(world.crop((0, 0, 4000, 2250)), folder / "standard1_left.jpg", taken=t0)
            save_jpeg(world.crop((2400, 0, 6400, 2250)), folder / "standard1_right.jpg",
                      taken=t0.replace(second=20), gps=True)
            save_jpeg(world.crop((0, 0, 3000, 2000)), folder / "challenge1_left.jpg", taken=t0)
            save_jpeg(world.crop((0, 0, 3000, 2000)), folder / "challenge1_right.jpg",
                      taken=t0.replace(minute=5))
            pairs, unknown = dataset_common.scan_member(folder, "tuan")
            self.assertEqual(unknown, [])
            results = {pair.code: check_pairs.check_pair(pair)[0] for pair in pairs}
            standard, challenge = results["tuan-standard1"], results["tuan-challenge1"]
            P, F, R = check_pairs.PASS, check_pairs.FAIL, check_pairs.REVIEW
            self.assertEqual(standard["Tên file"][0], P)
            self.assertEqual(standard["Đủ 3840×2160 sau khi cắt 16:9"][0], P)
            self.assertEqual(standard["Không có GPS"][0], R)
            self.assertEqual(standard["Cùng thiết bị"][0], P)
            self.assertEqual(standard["Chụp liền nhau"][0], P)
            self.assertEqual(standard["Camera chính 1x"][0], R, "missing focal length is never a pass")
            self.assertEqual(standard["Chồng lấn 30-50%"][0], P)
            self.assertEqual(standard[check_pairs.MANUAL][0], R)
            self.assertEqual(challenge["Đủ 3840×2160 sau khi cắt 16:9"][0], F)
            self.assertEqual(challenge["Chụp liền nhau"][0], R)
            self.assertEqual(check_pairs.summary(standard), R)
            self.assertEqual(check_pairs.summary(challenge), F)

    def test_unreadable_and_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "de"
            folder.mkdir()
            (folder / "standard1_left.HEIC").write_bytes(b"\0\0\0$ftypheic" + b"\0" * 64)
            (folder / "standard1_right.HEIC").write_bytes(b"\0\0\0$ftypheic" + b"\0" * 64)
            save_jpeg(scene(4000, 2250), folder / "standard2_left.jpg")
            pairs, _ = dataset_common.scan_member(folder, "de")
            results = {pair.code: check_pairs.check_pair(pair)[0] for pair in pairs}
            self.assertEqual(results["de-standard1"]["Đọc được JPEG"][0], check_pairs.FAIL)
            self.assertIn("HEIC", results["de-standard1"]["Đọc được JPEG"][1])
            self.assertEqual(results["de-standard1"]["Tên file"][0], check_pairs.FAIL)
            self.assertEqual(results["de-standard2"]["Đọc được JPEG"][0], check_pairs.FAIL)
            self.assertIn("right", results["de-standard2"]["Đọc được JPEG"][1])

    def test_main_skips_backups_and_ranks(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            world = scene(7000, 2400, 11)
            for suffix in ("", "_b1"):
                save_jpeg(world.crop((0, 0, 4000, 2250)), raw / "tuan" / f"standard1_left{suffix}.jpg")
                save_jpeg(world.crop((2400, 0, 6400, 2250)), raw / "tuan" / f"standard1_right{suffix}.jpg")
            save_jpeg(world.crop((0, 0, 3000, 2000)), raw / "chuong" / "standard1_left.jpg")
            save_jpeg(world.crop((1800, 0, 4800, 2000)), raw / "chuong" / "standard1_right.jpg")
            (raw / "thanh").mkdir(parents=True)
            (raw / "thanh" / "standard1_1.jpg").write_bytes(b"x")
            report_path = Path(tmp) / "report.md"
            self.assertEqual(check_pairs.main(["--raw", str(raw), "--out", str(report_path)]), 0)
            report = report_path.read_text(encoding="utf-8")
            self.assertNotIn("standard1-b1", report, "backup pairs are not checked")
            self.assertIn("thanh: 1 file", report)
            ranking = [line for line in report.splitlines() if line.startswith("| chuẩn |")]
            self.assertEqual(len(ranking), 2)
            self.assertIn("tuan-standard1", ranking[0], "the pair without a failed criterion ranks first")
            self.assertIn("chuong-standard1", ranking[1])


if __name__ == "__main__":
    unittest.main(verbosity=1)
