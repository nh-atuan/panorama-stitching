# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import notebook_preflight as pf


class PreflightTests(unittest.TestCase):
    def test_only_t4_sm75_is_certified(self):
        self.assertEqual(pf.parse_gpu("Tesla T4, gpu-id, 580.82, 7.5, 15000, 12000")["free_mib"], 12000)
        for text in ("NVIDIA L4, id, 580, 8.9, 24000, 20000", "T4, id, 580, 8.0, 15000, 12000",
                     "T4, id, 580, 7.5, 15000, 0", "", "T4, id, 580, 7.5, 1, 1\nT4, id, 580, 7.5, 1, 1"):
            with self.assertRaises(ValueError):
                pf.parse_gpu(text)

    def test_failed_environment_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pf.shutil, "which", return_value=None):
            with self.assertRaises(RuntimeError):
                pf.environment(folder)
            result = json.loads((Path(folder) / "environment.json").read_text())
            self.assertEqual(result["status"], "failed")
            self.assertIn("dependencies", result["error"])

    def test_missing_dataset_has_actionable_error_and_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(FileNotFoundError, "fetch_dataset"):
                pf.dataset(root / "absent", root)
            self.assertEqual(json.loads((root / "dataset.json").read_text())["status"], "failed")

    def test_wrong_manifest_rejected_before_image_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "manifest.csv").write_text("not the official manifest")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                pf.dataset(root, root / "evidence")


if __name__ == "__main__":
    unittest.main()
