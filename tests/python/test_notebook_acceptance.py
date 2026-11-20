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


if __name__ == "__main__":
    unittest.main()
