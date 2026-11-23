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

    def test_mermaid_copy_preserves_authored_source(self):
        source = 'Giới thiệu\n```mermaid\nflowchart LR\n A["Ảnh A"] --> B["Panorama"]\n```\n'
        self.notebook.cells.insert(0, self.nbf.v4.new_markdown_cell(source))
        rendered, diagrams = pdf.prepare_mermaid(self.notebook)
        self.assertEqual(self.notebook.cells[0].source, source)
        self.assertEqual(diagrams, ['flowchart LR\n A["Ảnh A"] --> B["Panorama"]\n'])
        self.assertIn('class="group16-mermaid"', rendered.cells[0].source)
        self.assertNotIn('```mermaid', rendered.cells[0].source)

    def test_mathjax_v3_inline_config_replaces_legacy_hub(self):
        html = '<head><!-- Load mathjax --><script>MathJax.Hub.Config({});</script><!-- End of mathjax configuration --></head>'
        configured = pdf.configure_mathjax(html)
        self.assertNotIn("MathJax.Hub", configured)
        self.assertIn("inlineMath:[['$','$']", configured)
        self.assertIn("startup:{typeset:false}", configured)
        with self.assertRaisesRegex(RuntimeError, "template"):
            pdf.configure_mathjax("<head>unknown template</head>")

    def test_vietnamese_pdf_glyph_spacing_is_not_a_missing_heading(self):
        # Reproduces the text extracted by pypdf from the returned Colab PDF.
        pages = ["1. Thông tin nhóm\n2. Gi ớ i thi ệ u", "9. K ế t lu ậ n"]
        found = pdf.heading_pages(pages, ("Thông tin nhóm", "Giới thiệu", "Kết luận"))
        self.assertEqual(found, {"Thông tin nhóm": [1], "Giới thiệu": [1], "Kết luận": [2]})
        self.assertEqual(pdf.heading_pages(["Gioi thieu"], ("Giới thiệu",)), {"Giới thiệu": []})
        self.assertEqual(pdf.heading_pages(["Giới thiệu"], ("Kết luận",)), {"Kết luận": []})

    def test_pdf_inspection_still_rejects_an_actually_missing_heading(self):
        from types import SimpleNamespace
        path = self.root / "mock.pdf"
        path.write_bytes(b"%PDF-1.7\n" + b"x" * 120)
        reader = SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: "2. Gi ớ i thi ệ u", images=[])])
        with patch("pypdf.PdfReader", return_value=reader):
            result = pdf.inspect_pdf(path, ("Giới thiệu", "Kết luận"))
        self.assertEqual(result["missing_headings"], ["Kết luận"])
        self.assertTrue(result["problems"])

    def test_mermaid_failure_cannot_fall_back_to_raw_latex_code(self):
        self.notebook.cells.insert(0, self.nbf.v4.new_markdown_cell('```mermaid\nflowchart LR\n A --> B\n```'))
        self.save()
        with patch.object(pdf, "browser_pdf", side_effect=RuntimeError("diagram renderer unavailable")):
            with self.assertRaisesRegex(RuntimeError, "raw Mermaid"):
                pdf.export(self.path, self.root / "out", smoke=True)
        self.assertTrue((self.root / "out/mermaid_sources.json").is_file())

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
