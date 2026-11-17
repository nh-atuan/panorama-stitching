#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166)
# External source: none

"""Tests for scripts/final_notebook.py on benchmark folders with known numbers.

The fixtures are written by the run_benchmark.py writers, so the loader reads the same files
that a real session produces. No stitch binary or GPU is needed.
"""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import final_notebook as fn  # noqa: E402
import run_benchmark as rb  # noqa: E402

SIZES = ("small", "medium", "large")
# Stage times of V0; version k divides every stage by FACTORS[k].
V0_STAGES = (4.0, 10.0, 6.0, 8.0, 2.0, 20.0)
FACTORS = {0: 1.0, 1: 4.0, 2: 5.0}


def parsed_for(version, size):
    scale = {"small": 1.0, "medium": 2.0, "large": 4.0}[size]
    stages = [value * scale / FACTORS[version] for value in V0_STAGES]
    row = dict(zip(rb.BASE_STAGE_COLUMNS, stages), Total_ms=sum(stages))
    if version:
        row.update(H2D_ms=0.5, D2H_ms=0.25, Total_Kernel_ms=sum(stages) * 0.9)
    return {"average": row, "minimum": dict(row)}


def write_session(root, versions=(0, 1, 2), challenge_failed=("medium", "large"), skip=None):
    """A benchmark folder as run_benchmark.py writes it, challenge included."""
    root = Path(root)
    averages, failures = {}, []
    for version in versions:
        folder = root / f"v{version}"
        folder.mkdir(parents=True)
        rows, version_failures = [], []
        for site, size in rb.configurations(include_challenge=True):
            if (site, size) == skip:
                continue
            if site == rb.CHALLENGE_SITE and size in challenge_failed:
                version_failures.append({"version": f"V{version}", "site": site, "size": size,
                                         "exit_code": 1, "error": "NumericalFailure"})
                (folder / site).mkdir(exist_ok=True)
                (folder / site / f"{size}.log").write_text(
                    "[debug] One warm-up (not timed).\nError: [NumericalFailure] S6 warp_blend failed.\n",
                    encoding="utf-8")
                continue
            rows.extend(rb.summary_rows(site, size, parsed_for(version, size), version=version))
        rb.write_summary_csv(folder / "summary.csv", rows)
        rb.write_failures_csv(folder / "failures.csv", version_failures)
        averages[version] = {(r["site"], r["size"]): r for r in rows if r["stat"] == "average"}
        failures.extend(version_failures)
    rb.write_speedup_csv(root / "speedup.csv", rb.compute_speedups(averages, list(versions), True))
    environment = {"gpu": "Tesla T4", "versions": list(versions), "include_challenge": True, "runs": 5}
    (root / "environment.json").write_text(json.dumps(environment), encoding="utf-8")
    return root


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp)

    def test_loads_the_four_objects(self):
        data = fn.load_benchmark(write_session(self.temp), [0, 1, 2])
        self.assertEqual(data.versions, ["V0", "V1", "V2"])
        self.assertEqual(data.environment["gpu"], "Tesla T4")
        # 10 measured configurations x 2 stats x 3 versions.
        self.assertEqual(len(data.summary), 60)
        self.assertEqual(len(data.failures), 6)
        self.assertEqual(len(data.speedup), 30)
        self.assertAlmostEqual(data.averages("V1")[("site1", "small")]["Total_ms"], 12.5)
        self.assertIsNone(data.averages("V0")[("site1", "small")]["H2D_ms"])

    def test_versions_must_match_the_session(self):
        root = write_session(self.temp)
        with self.assertRaisesRegex(fn.NotebookDataError, "environment.json lists versions"):
            fn.load_benchmark(root, [0, 1])

    def test_missing_standard_configuration_is_an_error(self):
        root = write_session(self.temp, skip=("site2", "large"))
        with self.assertRaisesRegex(fn.NotebookDataError, "site2/large"):
            fn.load_benchmark(root, [0, 1, 2])

    def test_challenge_needs_timing_or_failure(self):
        root = write_session(self.temp, skip=("challenge", "small"))
        with self.assertRaisesRegex(fn.NotebookDataError, "challenge has neither timing nor failure"):
            fn.load_benchmark(root, [0, 1, 2])

    def test_header_only_failures_are_valid(self):
        data = fn.load_benchmark(write_session(self.temp, challenge_failed=()), [0, 1, 2])
        self.assertEqual(data.failures, [])
        self.assertEqual(fn.failure_table(data), "No configuration failed.")

    def test_missing_failures_file_is_an_error(self):
        root = write_session(self.temp)
        (root / "v1" / "failures.csv").unlink()
        with self.assertRaisesRegex(fn.NotebookDataError, "Missing benchmark file"):
            fn.load_benchmark(root, [0, 1, 2])

    def test_header_of_another_schema_is_an_error(self):
        root = write_session(self.temp)
        text = (root / "speedup.csv").read_text(encoding="utf-8").replace("speedup_vs_v0", "vs_v0", 1)
        (root / "speedup.csv").write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(fn.NotebookDataError, "Unexpected header"):
            fn.load_benchmark(root, [0, 1, 2])

    def test_rows_of_another_version_are_an_error(self):
        root = write_session(self.temp)
        shutil.copy2(root / "v1" / "summary.csv", root / "v2" / "summary.csv")
        with self.assertRaisesRegex(fn.NotebookDataError, "another version"):
            fn.load_benchmark(root, [0, 1, 2])


class ViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = Path(tempfile.mkdtemp())
        cls.data = fn.load_benchmark(write_session(cls.temp / "bench"), [0, 1, 2])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp)

    def test_stage_table_columns_follow_the_version(self):
        v0 = fn.stage_table(self.data, "V0").splitlines()
        v1 = fn.stage_table(self.data, "V1").splitlines()
        self.assertNotIn("H2D", v0[0])
        self.assertIn("| H2D | D2H | Kernel |", v1[0])
        self.assertIn("| site1 | small | 4.00 | 10.00 |", v0[2])
        self.assertIn("S6 (40.0%)", v0[2])
        self.assertIn("failed: NumericalFailure", fn.stage_table(self.data, "V1"))

    def test_dominant_stage_is_the_largest_mean_share(self):
        shares = fn.dominant_stages(self.data, "V0")
        self.assertEqual(shares["large"]["hot_stage"], "S6")
        self.assertAlmostEqual(shares["small"]["shares"]["S2"], 20.0)
        self.assertIn("| small | 8.0 | 20.0 |", fn.dominant_stage_table(self.data, "V0"))

    def test_speedup_table_and_failures(self):
        table = fn.speedup_table(self.data, "V2")
        self.assertIn("| site1 | small | V2 | 10.00 | 5.00x | 1.25x | 9.00 | 5.56x |", table)
        self.assertIn("| challenge | large | V2 | failed: NumericalFailure |", table)
        self.assertIn("| site1 | small | V0 | 50.00 | 1.00x | 1.00x | — | — |", fn.speedup_table(self.data))
        sites = [row["site"] for row in fn.speedup_rows(self.data)]
        self.assertEqual(sites[-1], "challenge")
        self.assertEqual(sites.index("challenge"), sites.count("site1") * 3)

    def test_best_version_uses_the_geometric_mean(self):
        means = fn.geomean_speedups(self.data)
        self.assertAlmostEqual(means["V1"], 4.0)
        self.assertAlmostEqual(means["V2"], 5.0)
        self.assertEqual(fn.best_version(self.data), "V2")
        self.assertIn("| V2 | 5.00x |", fn.geomean_table(self.data))

    def test_empty_ratio_prints_a_dash(self):
        self.assertEqual(fn.fmt(None), fn.MISSING)
        self.assertEqual(fn.fmt(float("nan")), fn.MISSING)
        self.assertEqual(fn.fmt(2.0, suffix="x"), "2.00x")

    def test_charts_are_written(self):
        paths = fn.plot_speedup_charts(self.data, self.temp / "charts")
        breakdown = fn.plot_stage_breakdown(self.data, "V2", self.temp / "charts")
        names = sorted(path.name for path in [*paths, breakdown])
        self.assertEqual(names, ["speedup.png", "stage_speedup_v1.png", "stage_speedup_v2.png",
                                 "stage_timing_v2.png"])
        self.assertTrue(all(path.stat().st_size > 0 for path in [*paths, breakdown]))

    def test_gallery_shows_failures_as_status(self):
        from PIL import Image

        dataset = self.temp / "dataset"
        for site in (*rb.BENCHMARK_SITES, rb.CHALLENGE_SITE):
            (dataset / site).mkdir(parents=True)
            for side in ("left", "right"):
                Image.new("RGB", (64, 36), (40, 80, 120)).save(dataset / site / f"medium_{side}.jpg")
            panorama = self.temp / "bench" / "v2" / site
            panorama.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (100, 40)).save(panorama / "medium_panorama.jpg")
        entries = fn.gallery_entries(self.data, dataset, "V2", "medium")
        self.assertEqual([entry["status"] for entry in entries], ["ok", "ok", "ok", "failed: NumericalFailure"])
        self.assertIsNone(entries[-1]["panorama"])
        self.assertIn("NumericalFailure", fn.log_tail(entries[-1]["log"]))
        self.assertTrue(fn.panorama_preview(self.data, "V2", "site1", "medium").startswith(b"\xff\xd8"))
        with self.assertRaisesRegex(fn.NotebookDataError, "Missing panorama"):
            fn.panorama_preview(self.data, "V2", "site1", "small")
        out = fn.plot_gallery(entries, self.temp / "gallery.png")
        self.assertEqual(out.suffix, ".jpg")
        self.assertGreater(out.stat().st_size, 0)


class ProducerTests(unittest.TestCase):
    def test_supported_versions_reads_the_cli_error(self):
        def fake_run(command, **_):
            version = int(command[command.index("--version") + 1])
            stderr = "Error: [UnsupportedVersion] ..." if version > 3 else "Error: [InvalidImage] ..."
            return type("Result", (), {"stderr": stderr, "returncode": 1})()

        with patch.object(fn.subprocess, "run", side_effect=fake_run):
            self.assertEqual(fn.supported_versions("stitch"), [0, 1, 2, 3])

    def test_session_refuses_a_used_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "old.csv").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(fn.NotebookDataError, "not empty"):
                fn.run_benchmark_session(ROOT, "stitch", "dataset", temp, [0])

    def test_failed_command_raises_with_the_log_tail(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "step.log"
            command = [sys.executable, "-c", "print('step one'); raise SystemExit(3)"]
            with self.assertRaisesRegex(fn.NotebookDataError, "exited with 3"):
                fn.run_logged(command, temp, log)
            self.assertIn("step one", log.read_text(encoding="utf-8"))

    def test_dataset_with_another_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "manifest.csv").write_text("file\n", encoding="utf-8")
            with self.assertRaisesRegex(fn.NotebookDataError, "not the final dataset"):
                fn.fetch_dataset(temp, temp)


if __name__ == "__main__":
    unittest.main()
