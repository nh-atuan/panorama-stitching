# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""CPU evidence checks for the real report cell, including wrong-baseline failure cases."""

import contextlib
from decimal import Decimal, localcontext
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_final_notebook import section_structure
from v5_report import read_table, BENCHMARK


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
        rows = self.scope["p10"]["benchmark"].values()
        with localcontext() as ctx:
            ctx.prec = 40
            value = lambda row, key: Decimal(row[key].replace(",", "."))
            ratios = [Decimal(str(r[BENCHMARK[3]])) / Decimal(str(r[BENCHMARK[5]])) for r in rows]
            expected = (sum(r.ln() for r in ratios) / Decimal(9)).exp()
            self.assertAlmostEqual(self.scope["p10_metrics"]["geomean_nine"], float(expected), places=12)
            self.assertAlmostEqual(self.scope["p10_metrics"]["arithmetic_mean"], float(sum(ratios) / 9), places=12)
        metrics = self.scope["p10_metrics"]
        self.assertAlmostEqual(metrics["primary_case"], 62.275 / 58.926, places=12)
        self.assertAlmostEqual(metrics["geomean_medium_large"], 1.0324309195068098, places=12)
        self.assertAlmostEqual(metrics["geomean_v5_v0"], 49.876178117805956, places=10)

    def run_report_cell(self, transform):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in (self.scope["P10_BENCHMARK"], self.scope["P10_VERIFICATION"], self.scope["P10_BASELINE"]):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                text = (ROOT / relative).read_text(encoding="utf-8")
                path.write_text(transform(text) if relative == self.scope["P10_BENCHMARK"] else text, encoding="utf-8")
            scope = dict(self.scope, REPO_ROOT=root)
            scope["report_table"] = lambda relative, header: read_table(root / relative, header)
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(self.sources["v5-p10-results"], "v5-p10-results", "exec"), scope)
            return scope["p10_metrics"]

    def test_rounded_speedup_columns_and_challenge_do_not_drive_standard_metrics(self):
        metrics = self.run_report_cell(lambda s: s.replace("1151,090", "99999,000").replace("1,0686×", "999×"))
        self.assertEqual(metrics, self.scope["p10_metrics"])

    def test_incomplete_standard_matrix_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "nine standard"):
            self.run_report_cell(lambda s: "\n".join(l for l in s.splitlines() if not l.startswith("| site1 | small |")))

    def test_measurement_labels_and_completed_conclusion(self):
        text = self.output.getvalue()
        self.assertIn("T01 V4 instrumented probe", text)
        self.assertIn("raw_independently_verified: False", text)
        self.assertIn("Median tỉ số từng khối", text)
        self.assertIn("có lợi 3/5", text)
        self.assertNotIn("unreconciled", text)
        self.assertNotIn("V4 Production Pre-S4:", text)
        self.assertAlmostEqual((1 - self.scope["dual"] / self.scope["seq"]) * 100, (1 - 10.971 / 13.7) * 100)
        self.assertNotIn(".group(", self.sources["v5-p10-results"])
        conclusion = self.sources["conclusion"]
        self.assertNotIn("được bổ sung sau", conclusion)
        self.assertIn("production baseline", conclusion)
        self.assertIn("concurrency case study", conclusion)
        self.assertEqual(section_structure(self.cells)[1], [])
        self.assertTrue(all(not c.get("outputs") and c.get("execution_count") is None
                            for c in self.cells if c["cell_type"] == "code"))


if __name__ == "__main__":
    unittest.main()
