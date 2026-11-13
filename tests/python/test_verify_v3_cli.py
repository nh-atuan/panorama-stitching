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
from run_benchmark import version_columns
from verify_v3_cli import check_failure, check_panorama, smoke, verify_csv


def csv_text(rows):
    output = io.StringIO()
    csv.writer(output).writerows(rows)
    return output.getvalue()


class V3CliContractTest(unittest.TestCase):
    def setUp(self):
        header = version_columns(3)
        first = dict(zip(header[1:], (1, 2, 3, 4, 5, 6, 30, 0.2, 0.4, 22)))
        second = dict(first, Total_ms=34, H2D_ms=0.4, D2H_ms=0.2, Total_Kernel_ms=23)
        a, b = list(first.values()), list(second.values())
        self.rows = [header, ["1", *a], ["2", *b],
                     ["Average", *((x + y) / 2 for x, y in zip(a, b))],
                     ["Minimum", *map(min, zip(a, b))]]

    def test_parses_runner_schema_and_both_summaries(self):
        result = verify_csv(csv_text(self.rows), 2, 3)
        self.assertAlmostEqual(result["average"]["D2H_ms"], 0.3)
        self.assertEqual(result["minimum"]["Total_Kernel_ms"], 22)
        self.assertTrue(result["is_gpu"])

    def test_rejects_wrong_schema_order_width_and_invalid_timings(self):
        self.rows[0][1], self.rows[0][2] = self.rows[0][2], self.rows[0][1]
        with self.assertRaisesRegex(ValueError, "header disagrees"):
            verify_csv(csv_text(self.rows), 2, 3)
        self.rows[0] = version_columns(3)
        with self.assertRaisesRegex(ValueError, "header disagrees"):
            verify_csv(csv_text(self.rows), 2, 2)
        timing = self.rows[1].pop()
        with self.assertRaisesRegex(ValueError, "column count"):
            verify_csv(csv_text(self.rows), 2, 3)
        self.rows[1].append(float("nan"))
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            verify_csv(csv_text(self.rows), 2, 3)
        self.rows[1][-1] = timing
        for index, message in ((3, "average"), (4, "minimum")):
            original = self.rows[index][1]
            self.rows[index][1] += 1
            with self.assertRaisesRegex(ValueError, message):
                verify_csv(csv_text(self.rows), 2, 3)
            self.rows[index][1] = original

    def test_checks_expanded_png_and_version_trace(self):
        with TemporaryDirectory() as directory:
            left, output = (Path(directory) / name for name in ("left.png", "output.png"))
            Image.new("RGB", (4, 4)).save(left)
            Image.new("RGB", (6, 5)).save(output)
            debug = "[debug] GPU=Tesla T4 version=3 seed=16 runs=2\n[debug] S6 canvas=6x5 offset=(2, 1)\n"
            self.assertEqual(check_panorama(debug, output, left, 3), ((6, 5, 2, 1), 16))
            with self.assertRaisesRegex(ValueError, "debug version"):
                check_panorama(debug, output, left, 2)
            with self.assertRaisesRegex(ValueError, "contain image A"):
                check_panorama(debug.replace("(2, 1)", "(-1, 1)"), output, left, 3)
            Image.new("RGB", (4, 4)).save(output)
            with self.assertRaisesRegex(ValueError, "PNG does not match"):
                check_panorama(debug, output, left, 3)

    def test_challenge_requires_expected_stage_and_no_artifacts(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "challenge.png"
            record = {"returncode": 1}
            error = "Error: [NumericalFailure] S6 warp_blend failed."
            check_failure(record, "", error, output, "NumericalFailure", "warp_blend")
            with self.assertRaisesRegex(ValueError, "from warp_blend"):
                check_failure(record, "", error.replace("warp_blend", "homography"), output,
                              "NumericalFailure", "warp_blend")
            with self.assertRaisesRegex(ValueError, "exit 1"):
                check_failure(record, "Run_Index", error, output, "NumericalFailure")
            output.touch()
            with self.assertRaisesRegex(ValueError, "no CSV/PNG"):
                check_failure(record, "", error, output, "NumericalFailure")

    def test_missing_real_fixtures_fail_before_dispatch(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "evidence"
            with self.assertRaisesRegex(ValueError, "Missing required smoke inputs"):
                smoke(root / "stitch", root, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
