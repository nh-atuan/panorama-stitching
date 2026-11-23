# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import accept_final_notebook as accept


class EvidenceTests(unittest.TestCase):
    def test_distinct_attempts_and_preserved_failure_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = accept.new_run(folder), accept.new_run(folder)
            self.assertNotEqual(a, b)
            (a / "failure.log").write_text("execution failed: retain me")
            archive = accept.bundle(a)
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as zipped:
                checks = json.loads(zipped.read(f"{a.name}/evidence_checksums.json"))
                self.assertEqual(checks["failure.log"], accept.sha256(a / "failure.log"))
                self.assertIn("retain me", zipped.read(f"{a.name}/failure.log").decode())
            self.assertTrue(accept.bundle(a).is_file())
            self.assertTrue(archive.is_file())


@unittest.skipUnless(importlib.util.find_spec("nbformat"), "nbformat is an acceptance-tool dependency")
class AcceptanceTests(unittest.TestCase):
    def test_colab_wrapper_is_output_free_and_syntactically_valid(self):
        import ast
        import nbformat as nbf
        path = Path(__file__).resolve().parents[2] / "Group16_P11_T06_Acceptance.ipynb"
        if not path.is_file():
            self.skipTest("Colab wrapper is not in this snapshot")
        n = nbf.read(path, as_version=4)
        nbf.validate(n)
        cells = [c for c in n.cells if c.cell_type == "code"]
        self.assertEqual(len(cells), 5)
        for cell in cells:
            ast.parse(cell.source)
            self.assertEqual(cell.outputs, [])
            self.assertIsNone(cell.execution_count)

    def test_overlay_preserves_authored_prose_and_producer_semantics(self):
        import nbformat as nbf
        root = Path(__file__).resolve().parents[2]
        original = root / "Group16_Final.ipynb"
        before = original.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            n = accept.prepare_notebook(original, root, "a" * 40, folder, root / "scripts")
            authored = nbf.read(original, as_version=4)
            self.assertEqual([c.source for c in n.cells if c.cell_type == "markdown"],
                             [c.source for c in authored.cells if c.cell_type == "markdown"])
            changed = [c.get("id") for c, old in zip(n.cells, authored.cells) if c.source != old.source]
            self.assertEqual(changed, ["runtime-setup", "thanh-producer"])
            self.assertIn("candidates=BASELINE_VERSIONS", n.cells[4].source)
            self.assertEqual(n.metadata.group16_acceptance.source_sha, "a" * 40)
            self.assertTrue(n.metadata.group16_acceptance.candidate)
            self.assertIn("docs/dataset.md", n.metadata.group16_acceptance.local_reference_hashes)
            self.assertEqual(n.metadata.group16_acceptance.tooling_files["v5_report.py"],
                             accept.sha256(root / "scripts/v5_report.py"))
            self.assertIn("spec_from_file_location", n.cells[2].source)
            self.assertEqual(original.read_bytes(), before)
            path = Path(folder) / "unexecuted.ipynb"
            nbf.write(n, path)
            with self.assertRaises(ValueError):
                accept.inspect_outputs(path)

    def test_preflight_failure_still_has_summary_logs_and_zip(self):
        with tempfile.TemporaryDirectory() as folder:
            args = argparse.Namespace(evidence_root=Path(folder), frozen=False, source_sha="a" * 40,
                source_mode="published", repo_url="unused", dataset=Path(folder) / "data", notebook=None,
                source_archive=None, archive_sha256=None, cell_timeout=1, kernel="python3")
            with patch.object(accept, "published", side_effect=RuntimeError("freeze unavailable")):
                run, result = accept.execute(args)
            self.assertEqual(result["status"], "failed")
            self.assertIn("freeze unavailable", (run / "failure.log").read_text())
            self.assertTrue((run / "execution_summary.json").is_file())
            self.assertEqual(len(list(Path(folder).glob("*.zip"))), 1)
            validation = accept.validate_artifacts(run)
            self.assertEqual(validation["status"], "failed")
            self.assertIn("did not complete", validation["error"])

    def test_public_production_pin_uses_the_current_hashed_report_helper(self):
        import contextlib
        import io
        import os
        import package_notebook_acceptance as source_tools
        from audit_final_notebook import constants
        root = Path(__file__).resolve().parents[2]
        raw = json.loads((root / "Group16_Final.ipynb").read_text(encoding="utf-8"))
        setup = next(c for c in raw["cells"] if c.get("id") == "runtime-setup")
        pin = constants("".join(setup["source"]))["SOURCE_REF"]
        old_path = list(sys.path)
        old_module = sys.modules.get("v5_report")
        try:
            with tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                archive = folder / "production.zip"
                meta = source_tools.package(root, pin, archive)
                source = folder / "production"
                source_tools.verify_archive(archive, source, pin, meta["archive_sha256"])
                self.assertFalse((source / "scripts/v5_report.py").exists())
                run = folder / "run"
                run.mkdir()
                n = accept.prepare_notebook(root / "Group16_Final.ipynb", source, pin, run, root / "scripts")
                scope = {}
                with patch.dict(os.environ, {"GROUP16_DATASET_DIR": str(folder / "dataset")}), contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(n.cells[2].source, "runtime-setup", "exec"), scope)
                    for role in ("method-settings", "v0-evidence", "v1-evidence", "v2-evidence", "v3-evidence",
                                 "v4-p9-results", "v4-p9-profiling", "v4-p9-verification", "v5-p10-results"):
                        cell = next(c for c in n.cells if c.get("id") == role)
                        exec(compile(cell.source, role, "exec"), scope)
                self.assertEqual(scope["SOURCE_REF"], pin)
                self.assertEqual(n.metadata.group16_acceptance.source_sha, pin)
                self.assertEqual(scope["p10_metrics"]["beneficial_blocks"], 3)
                self.assertEqual(Path(sys.modules["v5_report"].__file__), root / "scripts/v5_report.py")
                self.assertTrue(all((source / p).is_file() for p in source_tools.NOTEBOOK_ASSETS))
        finally:
            sys.path[:] = old_path
            if old_module is not None:
                sys.modules["v5_report"] = old_module
            else:
                sys.modules.pop("v5_report", None)


if __name__ == "__main__":
    unittest.main()
