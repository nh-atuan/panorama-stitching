# Authors: Nguyen Ho Anh Tuan (23120185)
# Adapted from: tests/python/test_verify_v4_cli.py by Nguyen Ho Anh Tuan (23120185)
# Changes: Adapted to test verify_v5_cli with version 5 schema, sidecar CSV, and dual/sequential modes.

import csv
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_benchmark import version_columns
from verify_v5_cli import SIDECAR_HEADER, check_failure, check_panorama, smoke, verify_csv, verify_sidecar


def csv_text(rows):
    output = io.StringIO()
    csv.writer(output, lineterminator="\n").writerows(rows)
    return output.getvalue()


class V5CliContractTest(unittest.TestCase):
    def setUp(self):
        header = version_columns(5)
        first = dict(zip(header[1:], (1, 2, 3, 4, 5, 6, 30, 0.2, 0.4, 22)))
        second = dict(first, Total_ms=34, H2D_ms=0.4, D2H_ms=0.2, Total_Kernel_ms=23)
        a, b = list(first.values()), list(second.values())
        self.rows = [header, ["1", *a], ["2", *b],
                     ["Average", *((x + y) / 2 for x, y in zip(a, b))],
                     ["Minimum", *map(min, zip(a, b))]]

    def test_parses_runner_schema_and_both_summaries(self):
        result = verify_csv(csv_text(self.rows), 2, 5)
        self.assertAlmostEqual(result["average"]["D2H_ms"], 0.3)
        self.assertEqual(result["minimum"]["Total_Kernel_ms"], 22)
        self.assertTrue(result["is_gpu"])

    def test_rejects_wrong_schema_order_width_and_invalid_timings(self):
        self.rows[0][1], self.rows[0][2] = self.rows[0][2], self.rows[0][1]
        with self.assertRaisesRegex(ValueError, "header disagrees"):
            verify_csv(csv_text(self.rows), 2, 5)
        self.rows[0] = version_columns(5)
        with self.assertRaisesRegex(ValueError, "header disagrees"):
            verify_csv(csv_text(self.rows), 2, 4)
        timing = self.rows[1].pop()
        with self.assertRaisesRegex(ValueError, "column count"):
            verify_csv(csv_text(self.rows), 2, 5)
        self.rows[1].append(float("nan"))
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            verify_csv(csv_text(self.rows), 2, 5)
        self.rows[1][-1] = timing
        for index, message in ((3, "average"), (4, "minimum")):
            original = self.rows[index][1]
            self.rows[index][1] += 1
            with self.assertRaisesRegex(ValueError, message):
                verify_csv(csv_text(self.rows), 2, 5)
            self.rows[index][1] = original

    def test_verifies_sidecar_csv(self):
        with TemporaryDirectory() as directory:
            sidecar_file = Path(directory) / "detail.csv"
            rows = [
                SIDECAR_HEADER,
                ["1", "dual", "0.5", "0.5", "1.2", "1.1", "2.0", "1.9", "3.0", "3.1", "7.5", "7.2", "0.1", "0.2"],
                ["2", "dual", "0.4", "0.5", "1.1", "1.1", "1.9", "2.0", "3.1", "3.0", "7.4", "7.1", "0.1", "0.1"],
            ]
            sidecar_file.write_text(csv_text(rows), encoding="utf-8")
            verify_sidecar(sidecar_file, 2, "dual")

            with self.assertRaisesRegex(ValueError, "metadata mismatch"):
                verify_sidecar(sidecar_file, 2, "sequential")

            with self.assertRaisesRegex(ValueError, "header mismatch"):
                sidecar_bad = Path(directory) / "bad.csv"
                sidecar_bad.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
                verify_sidecar(sidecar_bad, 1, "dual")

    def test_checks_expanded_png_and_version_trace(self):
        with TemporaryDirectory() as directory:
            left, output = (Path(directory) / name for name in ("left.png", "output.png"))
            Image.new("RGB", (4, 4)).save(left)
            Image.new("RGB", (6, 5)).save(output)
            debug = "[debug] GPU=Tesla T4 version=5 seed=16 runs=2\n[debug] S6 canvas=6x5 offset=(2, 1)\n"
            self.assertEqual(check_panorama(debug, output, left, 5), ((6, 5, 2, 1), 16))
            with self.assertRaisesRegex(ValueError, "debug version"):
                check_panorama(debug, output, left, 4)
            with self.assertRaisesRegex(ValueError, "contain image A"):
                check_panorama(debug.replace("(2, 1)", "(-1, 1)"), output, left, 5)
            Image.new("RGB", (4, 4)).save(output)
            with self.assertRaisesRegex(ValueError, "PNG does not match"):
                check_panorama(debug, output, left, 5)

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
