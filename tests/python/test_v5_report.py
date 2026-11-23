# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Validate the real APOD schema and failure paths without GPU/raw archive dependencies."""

from decimal import Decimal, localcontext
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import v5_report as report


class V5ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "report.md"
        self.text = (ROOT / "docs/report/p10-t05-v5-apod.md").read_text(encoding="utf-8")

    def analyze(self, text=None):
        self.path.write_text(self.text if text is None else text, encoding="utf-8")
        return report.analyze(self.path, self.path.parent)

    def test_current_committed_tables_and_provenance(self):
        result = self.analyze()
        self.assertEqual(set(result["benchmark"]), report.STANDARD_CASES)
        self.assertEqual(set(result["challenge"]), {("challenge", "small")})
        self.assertEqual(result["provenance"]["measurement_source_sha"],
                         "26c8f241e056a7cf5e0c5bb0d85f036d9eafd9e1")
        self.assertEqual(result["provenance"]["measured_at"], "2026-11-23T06:47:04Z")
        self.assertEqual(result["decision"]["production"], "V4")
        self.assertEqual(result["decision"]["case_study"], "V5")

    def test_geometric_means_use_independent_decimal_calculation(self):
        result = self.analyze()
        with localcontext() as ctx:
            ctx.prec = 40
            ratios = [Decimal(str(r[report.BENCHMARK[3]])) / Decimal(str(r[report.BENCHMARK[5]]))
                      for r in result["benchmark"].values()]
            expected = (sum(r.ln() for r in ratios) / Decimal(9)).exp()
        m = result["metrics"]
        self.assertAlmostEqual(m["geomean_nine"], float(expected), places=12)
        self.assertAlmostEqual(m["geomean_v5_v0"], 49.876178117805956, places=10)
        self.assertAlmostEqual(m["geomean_dual_seq"], 1.0364129897885086, places=12)
        self.assertNotAlmostEqual(m["arithmetic_mean"], m["geomean_nine"], places=4)
        self.assertNotAlmostEqual(m["ratio_of_sums"], m["geomean_nine"], places=4)

    def test_challenge_and_rounded_claims_do_not_drive_aggregates(self):
        base = self.analyze()["metrics"]
        changed = self.text.replace("1151,090", "999999,999").replace("1,0686×", "999×")
        self.assertEqual(self.analyze(changed)["metrics"], base)

    def test_pres4_is_complete_and_separate_from_total(self):
        result = self.analyze()
        self.assertEqual(set(result["pres4"]), report.STANDARD_CASES)
        primary = result["pres4"][report.PRIMARY_CASE]
        self.assertEqual(primary[report.PRES4[2]], 13.7)
        self.assertEqual(primary[report.PRES4[3]], 10.971)
        self.assertEqual(primary[report.PRES4[4]], 7.68)
        self.assertAlmostEqual(result["metrics"]["geomean_pres4"], 1.2564295264650986, places=12)

    def test_five_alternating_blocks_and_adoption_gates(self):
        result = self.analyze()
        self.assertEqual(set(result["paired"]), set(range(1, 6)))
        self.assertAlmostEqual(result["metrics"]["paired_median"], 66.819 / 62.645, places=12)
        self.assertEqual(result["metrics"]["beneficial_blocks"], 3)
        self.assertTrue(result["decision"]["median_gate"])
        self.assertFalse(result["decision"]["consistency_gate"])

    def test_profile_overlap_vram_and_memory_metric_scope(self):
        result = self.analyze()
        self.assertEqual(len(result["profile_rows"]), 9)
        self.assertEqual((result["metrics"]["overlap_min"], result["metrics"]["overlap_max"]), (16.6, 24.5))
        for delta in result["metrics"]["vram_increases_mib"]:
            self.assertAlmostEqual(delta, 64.3, places=10)
        # NSYS remaining allocation bytes are not a substitute for Compute Sanitizer.
        self.assertFalse(result["provenance"]["raw_independently_verified"])

    def test_vietnamese_numbers_units_and_whitespace(self):
        for value in ("**13,700** ms", "`13.700`\u00a0ms", " 13,700 ms "):
            self.assertEqual(report.number(value, "latency", "ms"), 13.7)
        self.assertEqual(report.number("1,257 ×", "speedup", "×"), 1.257)
        self.assertEqual(report.number("16,6 %", "overlap", "%"), 16.6)
        self.assertEqual(report.number("0 B", "remaining allocations", "B", positive=False, integer=True), 0)

    def test_missing_required_table_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "expected one table.*Pre-S4"):
            self.analyze(self.text.replace("| Pre-S4 Seq (ms) |", "| Old Pre-S4 (ms) |"))

    def test_missing_field_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "missing required fields.*V5 Sequential"):
            self.analyze(self.text.replace("| V5 Sequential (ms) |", "| Unknown (ms) |"))

    def test_malformed_numbers_fail_without_default_values(self):
        for value in ("NaN", "inf", "—", "1,2.3", "0", "-1", "12 seconds"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.analyze(self.text.replace("1372,184", value))

    def test_duplicate_missing_and_unknown_configurations_fail(self):
        for changed in (self.text.replace("| site1 | small |", "| site2 | small |", 1),
                        self.text.replace("| site1 | small |", "| site4 | small |", 1),
                        "\n".join(l for l in self.text.splitlines() if not l.startswith("| site1 | small |"))):
            with self.assertRaisesRegex(ValueError, "duplicated|unexpected|nine standard"):
                self.analyze(changed)

    def test_block_order_and_profile_matrix_are_validated(self):
        with self.assertRaisesRegex(ValueError, "alternating"):
            self.analyze(self.text.replace("| 2 | `v5_dual → v4` |", "| 2 | `v4 → v5_dual` |"))
        with self.assertRaisesRegex(ValueError, "NSYS.*nine"):
            self.analyze("\n".join(l for l in self.text.splitlines() if not l.startswith("| `site1/large` | V4 Prod |")))
        with self.assertRaisesRegex(ValueError, "must identify site2/large"):
            self.analyze(self.text.replace("5 khối đo ghép cặp luân phiên trên ca chính `site2/large`",
                                           "5 khối đo ghép cặp luân phiên trên ca chính `site1/large`"))

    def test_decision_must_come_from_the_explicit_apod_section(self):
        with self.assertRaisesRegex(ValueError, "missing explicit"):
            self.analyze(self.text.replace("**phiên bản sản phẩm (Production Baseline)**", "**phiên bản sản phẩm**"))
        changed = self.text.replace("Nhóm giữ **V4 (Single-pass Canvas Fusion)**", "Nhóm giữ **V3 (Single-pass Canvas Fusion)**")
        self.assertEqual(self.analyze(changed)["decision"]["production"], "V3")

    def test_missing_raw_archive_never_fabricates_verification(self):
        result = self.analyze()
        self.assertFalse(result["provenance"]["raw_archive_present"])
        archive = self.path.parent / result["provenance"]["archive_reference"]
        archive.parent.mkdir()
        archive.write_bytes(b"not verified raw measurements")
        provenance = self.analyze()["provenance"]
        self.assertTrue(provenance["raw_archive_present"])
        self.assertFalse(provenance["raw_independently_verified"])

    def test_source_sha_and_provenance_fields_are_required(self):
        for changed in (self.text.replace("26c8f241e056a7cf5e0c5bb0d85f036d9eafd9e1", "main"),
                        self.text.replace("**Thời điểm hoàn tất:**", "**Unknown:**")):
            with self.assertRaisesRegex(ValueError, "source SHA|provenance field"):
                self.analyze(changed)

    def test_generic_table_reader_rejects_ambiguous_or_malformed_rows(self):
        self.path.write_text("| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
        self.assertEqual(report.read_table(self.path, ("A",))[0], {"A": "1", "B": "2"})
        self.path.write_text(self.path.read_text() * 2, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "found 2"):
            report.read_table(self.path, ("A",))
        self.path.write_text("| A | B |\n|---|---|\n| 1 |\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformed row"):
            report.read_table(self.path, ("A",))


if __name__ == "__main__":
    unittest.main()
