# Authors: Thanh Chuong (23120195), Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Offline checks of notebook structure, evidence parsing, and dataset integrity.

These checks are not evidence of an official Colab T4 Run all.
"""

import ast
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from midterm_notebook import (CSV_COLUMNS, SITES, SIZES, collect_benchmark_csv,
                              parse_stitch_csv, safe_extract, sha256,
                              source_manifest, validate_dataset, overlap_box)


def timing_csv(runs=5):
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    values = []
    for i in range(1, runs + 1):
        row = [float(i)] * 6 + [6.0 * i + 0.2]
        values.append(row)
        writer.writerow([i, *row])
    writer.writerow(["Average", *[sum(row[i] for row in values) / runs for i in range(7)]])
    writer.writerow(["Minimum", *values[0]])
    return stream.getvalue()


class TimingTests(unittest.TestCase):
    def test_valid_runs_and_summaries(self):
        result = parse_stitch_csv(timing_csv())
        self.assertEqual(len(result["runs"]), 5)
        self.assertEqual(result["average"]["S6_ms"], 3.0)
        self.assertAlmostEqual(result["minimum"]["Total_ms"], 6.2)
        self.assertEqual(len(parse_stitch_csv(timing_csv(1), 1)["runs"]), 1)

    def test_rejects_missing_duplicate_and_reordered_runs(self):
        for text in (timing_csv().replace("3,3.0,", "2,3.0,"),
                     "\n".join(timing_csv().splitlines()[:-1]),
                     timing_csv().replace("Run_Index", "run")):
            with self.subTest(text=text[:50]), self.assertRaises(ValueError):
                parse_stitch_csv(text)

    def test_rejects_bad_values_and_inconsistent_summary(self):
        for text in (timing_csv().replace("1,1.0,", "1,nan,"),
                     timing_csv().replace("1,1.0,", "1,-1.0,"),
                     timing_csv().replace("1,1.0,", "1,inf,"),
                     timing_csv().replace("Average,3.0", "Average,4.0"),
                     timing_csv().replace("6.2", "0.0")):
            with self.subTest(text=text[:50]), self.assertRaises(ValueError):
                parse_stitch_csv(text)

    def test_rejects_zero_runs_and_wrong_column_count(self):
        with self.assertRaises(ValueError):
            parse_stitch_csv(timing_csv(), 0)
        with self.assertRaises(ValueError):
            parse_stitch_csv(timing_csv().replace("1,1.0,", "1,1.0,2.0,"))

    def test_nine_cases_and_forty_five_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for site in SITES[:3]:
                (root / site).mkdir()
                for size in SIZES:
                    (root / site / f"{size}.csv").write_text(timing_csv())
            averages, minima, measurements = collect_benchmark_csv(root)
            self.assertEqual((len(averages), len(minima), len(measurements)), (9, 9, 45))
            (root / "site3/large.csv").unlink()
            with self.assertRaises(FileNotFoundError):
                collect_benchmark_csv(root)


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.rows = []
        for site in SITES:
            (self.root / site).mkdir()
            for size, (width, height) in SIZES.items():
                for side in ("left", "right"):
                    relative = f"{site}/{size}_{side}.jpg"
                    path = self.root / relative
                    path.write_bytes(relative.encode())
                    self.rows.append({"file": relative, "site": site, "side": side,
                                      "width": width, "height": height, "sha256": sha256(path)})
        self.write_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self):
        with (self.root / "manifest.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
            writer.writeheader()
            writer.writerows(self.rows)

    @staticmethod
    def fake_image(path):
        class FakeImage:
            format, mode = "JPEG", "RGB"
            size = SIZES[Path(path).stem.split("_")[0]]

            def __enter__(self): return self
            def __exit__(self, *args): return False
            def getexif(self): return {}
            def load(self): return None
        return FakeImage()

    def test_all_images_verified(self):
        with patch("PIL.Image.open", side_effect=self.fake_image):
            self.assertEqual(len(validate_dataset(self.root)), 24)

    def test_rejects_changed_image_bytes(self):
        (self.root / self.rows[0]["file"]).write_bytes(b"changed bytes")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_dataset(self.root)

    def test_rejects_missing_or_duplicate_manifest_row(self):
        for rows in (self.rows[:-1], [*self.rows[:-1], self.rows[0]]):
            self.rows = rows
            self.write_manifest()
            with self.assertRaises(ValueError):
                validate_dataset(self.root)

    def test_rejects_wrong_image_layout(self):
        def wrong_layout(path):
            image = self.fake_image(path)
            image.mode = "RGBA"
            return image
        with patch("PIL.Image.open", side_effect=wrong_layout), self.assertRaises(ValueError):
            validate_dataset(self.root)

    def test_rejects_wrong_manifest_dimensions(self):
        self.rows[0]["width"] = 1
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "dimensions"):
            validate_dataset(self.root)


class ReproducibilityTests(unittest.TestCase):
    def test_archive_rejects_traversal_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("../escape.txt", "..\\escape.txt", "/escape.txt"):
                with zipfile.ZipFile(root / "input.zip", "w") as archive:
                    archive.writestr("safe.txt", "safe")
                    archive.writestr(name, "unsafe")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    safe_extract(root / "input.zip", root / "out")
                self.assertFalse((root / "out/safe.txt").exists())

    def test_archive_and_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(root / "input.zip", "w") as archive:
                archive.writestr("src/main.cu", "// source\n")
            safe_extract(root / "input.zip", root / "out")
            first = source_manifest(root / "out")
            (root / "out/src/main.cu").write_text("// modified\n")
            self.assertNotEqual(first, source_manifest(root / "out"))

    def test_overlap_translation_and_negative_offset(self):
        log = "[debug] H(B->A)=1 0 2 0 1 0 0 0 1\n[debug] S6 canvas=6x3 offset=(0,0)"
        self.assertEqual(overlap_box(log, 4, 3, 4, 3), (2, 0, 4, 3))
        log = "[debug] H(B->A)=1 0 -2 0 1 0 0 0 1\n[debug] S6 canvas=6x3 offset=(2,0)"
        self.assertEqual(overlap_box(log, 4, 3, 4, 3), (2, 0, 4, 3))
        with self.assertRaises(ValueError):
            overlap_box("missing diagnostics", 4, 3, 4, 3)


NOTEBOOK = ROOT / "Group16_Midterm.ipynb"


# The Colab workspace holds src/, scripts/, tests/ and data, not the notebook file itself.
@unittest.skipUnless(NOTEBOOK.is_file(), "notebook file is not part of this workspace")
class NotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    def test_code_cells_compile_and_are_clean(self):
        ids = []
        for cell in self.notebook["cells"]:
            ids.append(cell["id"])
            if cell["cell_type"] == "code":
                source = "".join(cell["source"])
                ast.parse(source)
                compile(source, cell["id"], "exec")
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])
                self.assertNotIn("%%writefile", source)
        self.assertEqual(len(ids), len(set(ids)))

    def test_required_sections_and_english_headings(self):
        text = "\n".join("".join(cell["source"]) for cell in self.notebook["cells"]
                         if cell["cell_type"] == "markdown")
        for number in range(1, 8):
            self.assertIn(f"## 3.{number} ", text)
        for line in text.splitlines():
            if line.startswith("#"):
                self.assertTrue(all(ord(character) < 128 or character in "—·" for character in line), line)

    def configuration_value(self, name):
        by_id = {cell["id"]: "".join(cell["source"]) for cell in self.notebook["cells"]}
        for node in ast.parse(by_id["configuration"]).body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
        self.fail(f"{name} is not assigned in the configuration cell")

    def test_benchmark_arguments_match_runner(self):
        from run_benchmark import parse_args
        arguments = self.configuration_value("BENCHMARK_ARGS")
        values = {"stitch": "build/stitch", "dataset": "dataset", "runs": "5", "out": "results/b"}
        parsed = parse_args([argument.format(**values) for argument in arguments])
        self.assertEqual((str(parsed.stitch), str(parsed.dataset), parsed.runs, str(parsed.out)),
                         (str(Path("build/stitch")), "dataset", 5, str(Path("results/b"))))

    def test_accelerated_stages_follow_team_decision(self):
        self.assertEqual(self.configuration_value("ACCELERATED_STAGES"), [2, 4, 6])

    def test_benchmark_and_readiness_are_not_claimed_in_advance(self):
        by_id = {cell["id"]: "".join(cell["source"]) for cell in self.notebook["cells"]}
        self.assertIn("BENCHMARK_EXECUTED = False", by_id["benchmark-integration"])
        self.assertIn("not ready", by_id["readiness"])
        self.assertIn("source_manifest(PROJECT) == SOURCE_HASHES", by_id["readiness"])
        self.assertIn("src/ comes only from the submission", by_id["workspace"])


if __name__ == "__main__":
    unittest.main()
