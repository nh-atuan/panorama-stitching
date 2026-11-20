# Authors: Le Ha Thanh Chuong (23120195)
# External source: none
"""CPU protocol fixtures for V5 timing and missing-T02 build behavior."""
import csv
import io
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from smoke_v5_dispatcher import DETAIL_COLUMNS, check_detail
from run_benchmark import parse_version_csv, version_columns


class DispatcherContractTests(unittest.TestCase):
    def fixture(self, **updates):
        row = {key: 1 for key in DETAIL_COLUMNS}
        row.update(Run_Index=1, Mode="dual", **updates)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
        return output.getvalue()

    def primary(self):
        return {"runs": [{key: 2 for key in ("H2D_ms", "S1_ms", "S2_ms", "S3_ms")}]}

    def test_stream_duration_sums(self):
        self.assertEqual(len(check_detail(self.fixture(), "dual", self.primary())), 1)

    def test_mismatched_stage_fails(self):
        with self.assertRaises(ValueError):
            check_detail(self.fixture(S2_A_ms=5), "dual", self.primary())

    def test_wrong_mode_fails(self):
        with self.assertRaises(ValueError):
            check_detail(self.fixture(), "sequential", self.primary())

    def test_nonfinite_fails(self):
        with self.assertRaises(ValueError):
            check_detail(self.fixture(PreS4_ms="nan"), "dual", self.primary())

    def test_missing_runs_fail(self):
        with self.assertRaises(ValueError):
            check_detail(",".join(DETAIL_COLUMNS), "dual", self.primary())

    def test_missing_t02_fails_before_compilation(self):
        if (ROOT / "src/v5/v5_image_branch.cu").is_file():
            self.skipTest("Real T02 implementation is present")
        result = subprocess.run([sys.executable, "scripts/build.py", "--enable-v5", "--print-command"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("P10-T02", result.stderr)

    def test_overlap_allows_work_sum_above_wall_time_only_for_v5(self):
        for version in (4, 5):
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(version_columns(version))
            values = [2] * 6 + [8, 1, 1, 12]
            for label in ("1", "Average", "Minimum"):
                writer.writerow([label, *values])
            if version == 5:
                self.assertEqual(parse_version_csv(output.getvalue(), 1, version)["average"]["Total_ms"], 8)
            else:
                with self.assertRaises(ValueError):
                    parse_version_csv(output.getvalue(), 1, version)


if __name__ == "__main__":
    unittest.main()
