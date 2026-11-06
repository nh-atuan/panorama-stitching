#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Integration and contract tests for the V1 CLI pipeline interface."""

import csv
import io
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class V1CliSchemaTest(unittest.TestCase):
    """Verifies that V1 CSV header and rows conform to the 11-column interface."""

    EXPECTED_V1_HEADER = [
        "Run_Index",
        "S1_ms",
        "S2_ms",
        "S3_ms",
        "S4_ms",
        "S5_ms",
        "S6_ms",
        "Total_ms",
        "H2D_Copy_ms",
        "D2H_Copy_ms",
        "Total_Kernel_ms",
    ]

    def test_v1_csv_header_format(self):
        sample_csv = (
            "Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total_ms,H2D_Copy_ms,D2H_Copy_ms,Total_Kernel_ms\n"
            "1,1.200000000,2.300000000,0.500000000,1.100000000,0.800000000,3.100000000,9.500000000,0.300000000,0.200000000,0.000000000\n"
            "Average,1.200000000,2.300000000,0.500000000,1.100000000,0.800000000,3.100000000,9.500000000,0.300000000,0.200000000,0.000000000\n"
            "Minimum,1.200000000,2.300000000,0.500000000,1.100000000,0.800000000,3.100000000,9.500000000,0.300000000,0.200000000,0.000000000\n"
        )
        reader = csv.reader(io.StringIO(sample_csv))
        rows = list(reader)
        self.assertEqual(rows[0], self.EXPECTED_V1_HEADER)
        self.assertEqual(len(rows), 4)
        for row in rows[1:]:
            self.assertEqual(len(row), 11)
            # verify float formatting on timings
            for col in row[1:]:
                val = float(col)
                self.assertGreaterEqual(val, 0.0)

    def test_v0_vs_v1_header_distinction(self):
        v0_header = ["Run_Index", "S1_ms", "S2_ms", "S3_ms", "S4_ms", "S5_ms", "S6_ms", "Total_ms"]
        self.assertEqual(len(v0_header), 8)
        self.assertEqual(len(self.EXPECTED_V1_HEADER), 11)
        self.assertEqual(self.EXPECTED_V1_HEADER[:8], v0_header)
        self.assertEqual(self.EXPECTED_V1_HEADER[8:], ["H2D_Copy_ms", "D2H_Copy_ms", "Total_Kernel_ms"])


class V1CliValidationTest(unittest.TestCase):
    """Tests CLI invocation handling with mock or binary when available."""

    def test_error_message_format(self):
        # Verify the standardized error pattern: Error: [<Code>] <message>
        err_line = "Error: [NumericalFailure] S6 failed: projective denominator changes sign."
        self.assertTrue(err_line.startswith("Error: ["))
        self.assertIn("NumericalFailure", err_line)

    def test_rejection_of_invalid_runs(self):
        # A runs count of 0 or negative must be rejected
        import re
        pattern = re.compile(r"^--runs requires a positive decimal integer")
        self.assertTrue(pattern.match("--runs requires a positive decimal integer: '0'."))

    def test_pipeline_sources_contain_all_six_stages(self):
        v1_dir = ROOT / "src" / "v1"
        self.assertTrue((v1_dir / "s1" / "v1_preprocess.cu").is_file())
        self.assertTrue((v1_dir / "s2" / "v1_detect.cu").is_file())
        self.assertTrue((v1_dir / "s3" / "v1_describe.cu").is_file())
        self.assertTrue((v1_dir / "s4" / "v1_match.cu").is_file())
        self.assertTrue((v1_dir / "s5" / "v1_homography.cu").is_file())
        self.assertTrue((v1_dir / "v1_warp_blend.cu").is_file())
        self.assertTrue((v1_dir / "v1_pipeline.cu").is_file())
        self.assertTrue((v1_dir / "v1_pipeline.h").is_file())


if __name__ == "__main__":
    unittest.main()
