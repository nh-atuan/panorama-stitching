# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import export_notebook_pdf as pdf


@unittest.skipUnless(importlib.util.find_spec("nbformat"), "nbformat is an acceptance-tool dependency")
class PDFTests(unittest.TestCase):
    def setUp(self):
        import nbformat as nbf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "smoke.ipynb"
        self.notebook = nbf.v4.new_notebook(cells=[nbf.v4.new_code_cell('print("SMOKE ONLY")',
            execution_count=1, outputs=[nbf.v4.new_output("stream", name="stdout", text="SMOKE ONLY\n")])])
        self.nbf = nbf

    def save(self):
        self.nbf.write(self.notebook, self.path)

    def test_requires_saved_output_not_just_count(self):
        self.notebook.cells[0].outputs = []
        self.save()
        with self.assertRaisesRegex(ValueError, "missing"):
            pdf.executed_notebook(self.path)

    def test_errors_and_skipped_counts_rejected(self):
        for count, output in [(None, []), (2, []), (1, [self.nbf.v4.new_output("error", ename="Error", evalue="x", traceback=[])])]:
            self.notebook.cells[0].execution_count = count
            self.notebook.cells[0].outputs = output
            self.save()
            with self.assertRaises(ValueError):
                pdf.executed_notebook(self.path)

    def test_failure_logs_and_smoke_is_not_final_pdf(self):
        self.save()
        with patch.object(pdf, "browser_pdf", side_effect=RuntimeError("browser unavailable")), \
                patch.object(pdf, "dependencies", return_value={"latex": {"pandoc": None, "xelatex": None}}):
            with self.assertRaisesRegex(RuntimeError, "fallback"):
                pdf.export(self.path, self.root / "out", smoke=True)
        report = json.loads((self.root / "out/pdf_export.json").read_text())
        self.assertTrue(report["smoke"])
        self.assertEqual(report["status"], "failed")
        self.assertTrue((self.root / "out/chromium-error.log").is_file())
        self.assertFalse((self.root / "out/Group16_Final.pdf").exists())


if __name__ == "__main__":
    unittest.main()
