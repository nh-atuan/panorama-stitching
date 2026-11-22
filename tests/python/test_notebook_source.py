# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import package_notebook_acceptance as source


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        for name in (*source.PIN_FILES, "Group16_Final.ipynb"):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("committed\n")
        fixture = self.root / "experiments/Group16_Midterm.ipynb"
        fixture.parent.mkdir()
        fixture.write_text("committed notebook fixture\n")
        self.git("init")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.org", "commit", "-m", "fixture")
        self.sha = self.git("rev-parse", "HEAD")
        self.archive = Path(self.temp.name) / "source.zip"
        self.out = Path(self.temp.name) / "extract"

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, stderr=subprocess.DEVNULL,
                                       text=True).strip()

    def test_committed_only_round_trip_and_checksum(self):
        (self.root / "src/main.cu").write_text("uncommitted change")
        (self.root / "src/private.tmp").write_text("untracked")
        metadata = source.package(self.root, "HEAD", self.archive)
        source.verify_archive(self.archive, self.out, self.sha, metadata["archive_sha256"])
        self.assertEqual((self.out / "src/main.cu").read_text(), "committed\n")
        self.assertFalse((self.out / "src/private.tmp").exists())
        self.assertTrue((self.out / "experiments/Group16_Midterm.ipynb").is_file())
        self.assertEqual(json.loads(self.archive.with_suffix(".json").read_text())["source_sha"], self.sha)
        with self.assertRaises(FileExistsError):
            source.verify_archive(self.archive, self.out, self.sha, metadata["archive_sha256"])

    def test_tampering_wrong_sha_and_extra_code_rejected(self):
        metadata = source.package(self.root, "HEAD", self.archive)
        with self.assertRaisesRegex(ValueError, "ZIP SHA"):
            source.verify_archive(self.archive, self.out, self.sha, "0" * 64)
        with self.assertRaisesRegex(ValueError, "Git SHA"):
            source.verify_archive(self.archive, self.out, "a" * 40, metadata["archive_sha256"])
        source.verify_archive(self.archive, self.out, self.sha, metadata["archive_sha256"])
        (self.out / "src/extra.cu").write_text("injected")
        with self.assertRaisesRegex(ValueError, "inventory"):
            source.verify_tree(self.out, self.sha)
        (self.out / "src/extra.cu").unlink()
        (self.out / "src/main.cu").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            source.verify_tree(self.out, self.sha)

    def test_non_sha_refs_rejected_for_execution(self):
        with self.assertRaises(ValueError):
            source.full_sha("main")

    def test_freeze_scope_distinguishes_tooling_from_cuda_changes(self):
        (self.root / "scripts/tool.py").write_text("# Tooling only\n")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.org", "commit", "-m", "tooling")
        check = source.compare_freeze(self.root, self.git("rev-parse", "HEAD"), self.sha)
        self.assertTrue(check["src_build_equivalent"])
        self.assertIn("scripts/tool.py", check["tooling_changes"])
        (self.root / "src/main.cu").write_text("// Changed CUDA behavior\n")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.org", "commit", "-m", "production")
        check = source.compare_freeze(self.root, self.git("rev-parse", "HEAD"), self.sha)
        self.assertFalse(check["src_build_equivalent"])
        self.assertEqual(check["production_changes"], ["src/main.cu"])

    def test_traversal_archive_rejected(self):
        # Even a locally supplied hash must not authorize path traversal.
        payload = b"malicious"
        manifest = dict(git_commit=self.sha, payload_files={"../outside": source.hashlib.sha256(payload).hexdigest()})
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr(source.MANIFEST, json.dumps(manifest))
            archive.writestr("../outside", payload)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            source.verify_archive(self.archive, self.out, self.sha, source.sha256(self.archive))
        self.assertFalse((self.out.parent / "outside").exists())


if __name__ == "__main__":
    unittest.main()
