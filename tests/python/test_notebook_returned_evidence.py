# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Returned evidence must not turn arbitrary failures into accepted executions."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review_notebook_evidence import aggregates, checksums, recovery_scope


class ReturnedEvidenceTests(unittest.TestCase):
    def test_checksum_inventory_rejects_modified_and_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "execution.log"
            path.write_bytes(b"real log")
            inventory = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}
            (root / "evidence_checksums.json").write_text(json.dumps(inventory))
            self.assertEqual(checksums(root), 1)
            path.write_bytes(b"edited log")
            with self.assertRaisesRegex(ValueError, "checksum"):
                checksums(root)
            path.unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                checksums(root)

    def test_checksum_inventory_rejects_escaping_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "evidence_checksums.json").write_text(json.dumps({"../outside": "0" * 64}))
            with self.assertRaises(ValueError):
                checksums(root)

    def test_only_isolated_pdf_qa_failure_can_be_reviewed_as_completed_execution(self):
        summary = dict(status="failed", error="PDF automatic QA failed; see pdf/pdf_export.json",
                       outputs={"status": "passed"}, benchmark={"status": "passed"}, pdf={"status": "qa_failed"})
        self.assertIn("original PDF QA failure retained", recovery_scope(summary))
        self.assertEqual(summary["status"], "failed")
        for changed in (dict(summary, error="CUDA launch failed"),
                        dict(summary, outputs={"status": "failed"}),
                        dict(summary, benchmark={"status": "failed"})):
            with self.assertRaisesRegex(ValueError, "Not an isolated"):
                recovery_scope(changed)

    def test_standard_geomeans_exclude_challenge(self):
        values = {(v, f"site{i}", size): 100 / (v + 1)
                  for v in range(6) for i in (1, 2, 3) for size in ("small", "medium", "large")}
        expected = aggregates(values)
        values[(5, "challenge", "small")] = 999999
        self.assertEqual(aggregates(values), expected)
        self.assertAlmostEqual(expected["V5"]["vs_v0"], 6)
        self.assertAlmostEqual(expected["V5"]["vs_previous"], 6 / 5)

    def test_missing_standard_case_cannot_silently_change_the_aggregate(self):
        with self.assertRaises(KeyError):
            aggregates({})


if __name__ == "__main__":
    unittest.main()
