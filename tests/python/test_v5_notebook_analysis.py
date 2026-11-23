# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""CPU evidence checks for the real report cell, including wrong-baseline failure cases."""

import contextlib
from decimal import Decimal, localcontext
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_final_notebook import section_structure


class V5NotebookAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notebook = json.loads((ROOT / "Group16_Final.ipynb").read_text(encoding="utf-8"))
        cls.cells = notebook["cells"]
        cls.sources = {c["id"]: "".join(c["source"]) for c in cls.cells}
        cls.scope = {"REPO_ROOT": ROOT}
        cls.output = io.StringIO()
        # Run the authored evidence code in dependency order, without source/bootstrap/GPU cells.
        with contextlib.redirect_stdout(cls.output):
            for role in ("method-settings", "v0-evidence", "v1-evidence", "v2-evidence", "v3-evidence",
                         "v4-p9-results", "v4-p9-verification", "v5-p10-results"):
                exec(compile(cls.sources[role], role, "exec"), cls.scope)

    def test_derived_metrics_match_independent_decimal_calculation(self):
        rows = self.scope["standard"]
        with localcontext() as ctx:
            ctx.prec = 40
            value = lambda row, key: Decimal(row[key].replace(",", "."))
            ratios = [value(r, "V4 Production (ms)") / value(r, "V5 DualStream (ms)") for r in rows]
            expected = (sum(r.ln() for r in ratios) / Decimal(9)).exp()
            self.assertAlmostEqual(self.scope["p10_metrics"]["geomean_nine"], float(expected), places=12)
            self.assertAlmostEqual(self.scope["p10_metrics"]["arithmetic_mean"], float(sum(ratios) / 9), places=12)
        metrics = self.scope["p10_metrics"]
        self.assertAlmostEqual(metrics["primary_case"], 61.655 / 59.941, places=12)
        self.assertAlmostEqual(metrics["geomean_medium_large"], 1.0219651473125404, places=12)
        self.assertAlmostEqual(metrics["geomean_v5_v0"], 52.84619652459939, places=10)

    def test_rounded_speedup_columns_and_challenge_do_not_drive_standard_metrics(self):
        scope = dict(self.scope)
        read = scope["report_table"]
        def altered(path, header):
            rows = read(path, header)
            if path == scope["P10_BENCHMARK"]:
                for row in rows:
                    row["Speedup V5 vs V4"] = "999×"
                    if row["Cấu hình"] == "challenge":
                        row["V4 Production (ms)"] = "99999,000"
            return rows
        scope["report_table"] = altered
        with contextlib.redirect_stdout(io.StringIO()):
            exec(self.sources["v5-p10-results"], scope)
        self.assertEqual(scope["p10_metrics"], self.scope["p10_metrics"])

    def test_incomplete_standard_matrix_is_rejected(self):
        scope = dict(self.scope)
        read = scope["report_table"]
        scope["report_table"] = lambda path, header: read(path, header)[1:] if path == scope["P10_BENCHMARK"] else read(path, header)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(AssertionError):
            exec(self.sources["v5-p10-results"], scope)

    def test_measurement_labels_and_completed_conclusion(self):
        text = self.output.getvalue()
        self.assertIn("T01 V4 instrumented probe", text)
        self.assertIn("raw sidecars unavailable", text)
        self.assertIn("Paired-block median", text)
        self.assertIn("unreconciled", text)
        self.assertNotIn("V4 Production Pre-S4:", text)
        self.assertAlmostEqual((1 - self.scope["dual"] / self.scope["seq"]) * 100, 17.178314826910523)
        conclusion = self.sources["conclusion"]
        self.assertNotIn("được bổ sung sau", conclusion)
        self.assertIn("production baseline", conclusion)
        self.assertIn("concurrency case study", conclusion)
        self.assertEqual(section_structure(self.cells)[1], [])
        self.assertTrue(all(not c.get("outputs") and c.get("execution_count") is None
                            for c in self.cells if c["cell_type"] == "code"))


if __name__ == "__main__":
    unittest.main()
