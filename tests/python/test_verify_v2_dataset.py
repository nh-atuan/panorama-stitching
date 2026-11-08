# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

import csv
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from verify_v2_dataset import V2_HEADER, memcheck_result, parse_v2_csv, projection_drift, rgb_delta


def csv_text(rows):
    output = io.StringIO()
    csv.writer(output).writerows(rows)
    return output.getvalue()


class V2AcceptanceTest(unittest.TestCase):
    def setUp(self):
        first = [1, 2, 3, 4, 5, 6, 0.1, 0.2, 20, 25]
        second = [2, 1, 3, 4, 5, 6, 0.3, 0.1, 21, 26]
        self.rows = [list(V2_HEADER), ["1", *first], ["2", *second],
                     ["Average", *((a + b) / 2 for a, b in zip(first, second))],
                     ["Minimum", *map(min, zip(first, second))]]

    def test_exact_schema_and_all_summaries(self):
        self.assertEqual(",".join(V2_HEADER),
                         "Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,H2D_ms,D2H_ms,Total_Kernel_ms,Total_ms")
        result = parse_v2_csv(csv_text(self.rows), 2)
        self.assertEqual(result["average"]["Total_ms"], 25.5)
        self.assertEqual(result["minimum"]["D2H_ms"], 0.1)
        self.rows[0][-1], self.rows[0][-2] = self.rows[0][-2], self.rows[0][-1]
        with self.assertRaisesRegex(ValueError, "header"):
            parse_v2_csv(csv_text(self.rows), 2)

    def test_non_finite_and_incorrect_summary_are_rejected(self):
        self.rows[-1][1] = 1.1
        with self.assertRaisesRegex(ValueError, "Incorrect Minimum"):
            parse_v2_csv(csv_text(self.rows), 2)
        self.rows[-1][1] = float("nan")
        with self.assertRaisesRegex(ValueError, "invalid timing"):
            parse_v2_csv(csv_text(self.rows), 2)

    def test_memcheck_requires_both_zero_summaries_and_success_exit(self):
        clean = "========= LEAK SUMMARY: 0 bytes leaked in 0 allocations\n========= ERROR SUMMARY: 0 errors\n"
        self.assertTrue(memcheck_result({"returncode": 0}, clean, "")["passed"])
        self.assertFalse(memcheck_result({"returncode": 0}, "ERROR SUMMARY: 0 errors", "")["passed"])
        self.assertFalse(memcheck_result({"returncode": 99}, clean, "")["passed"])
        self.assertFalse(memcheck_result({"returncode": 0}, clean.replace("0 bytes", "16 bytes"), "")["passed"])

    def test_projection_is_scale_invariant_and_rgb_uses_signed_differences(self):
        identity = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        self.assertEqual(projection_drift(identity, [-2 * value for value in identity], 100, 100), 0)
        with TemporaryDirectory() as folder:
            a, b = Path(folder) / "a.png", Path(folder) / "b.png"
            Image.new("RGB", (5, 130), (0, 0, 0)).save(a)
            other = Image.new("RGB", (5, 130), (0, 0, 0))
            other.putpixel((4, 129), (255, 0, 0))
            other.save(b)
            self.assertEqual(rgb_delta(a, b), 255)
            self.assertEqual(rgb_delta(b, a), 255)
