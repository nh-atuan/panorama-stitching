# Authors: Le Ha Thanh Chuong (23120195)
# External source: none
"""CPU-only tests with temporary, explicitly synthetic measurement fixtures."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from profiling import pres4_baseline as baseline
from profiling.build_pres4_probe import overlay_sources, replace_once
from run_benchmark import version_columns


class BaselineTests(unittest.TestCase):
    def test_statistics_preserve_outliers(self):
        rows = [{key: value for key in baseline.PROBE_COLUMNS} for value in (1, 1, 1, 1, 100)]
        stats = baseline.summarize(rows)["PreS4_ms"]
        self.assertEqual(stats["median"], 1)
        self.assertEqual(stats["mean"], 20.8)
        self.assertEqual(stats["maximum"], 100)

    def test_missing_anchor_fails(self):
        with self.assertRaises(ValueError):
            replace_once("changed source", "expected source", "new source")

    def test_overlay_keeps_production_unchanged(self):
        root = Path(__file__).resolve().parents[2]
        original = (root / "src/main.cu").read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            mapping = overlay_sources(Path(temp))
            self.assertEqual(len(mapping), 5)
            pipeline = Path(mapping["src/v1/v1_pipeline.cu"]).read_text()
            self.assertIn("pres4::before_s4(stream)", pipeline)
            self.assertEqual((root / "src/main.cu").read_bytes(), original)

    def test_raw_schema_and_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "probe.csv"
            rows = [{key: 1 for key in baseline.PROBE_COLUMNS} for _ in range(5)]
            baseline.write_csv(path, rows)
            self.assertEqual(len(baseline.read_probe(path, 5)), 5)
            with self.assertRaises(ValueError):
                baseline.read_probe(path, 6)
            rows[0]["PreS4_ms"] = float("nan")
            baseline.write_csv(path, rows)
            with self.assertRaises(ValueError):
                baseline.read_probe(path, 5)

    def make_evidence(self, root):
        (root / "logs").mkdir()
        for site in baseline.SITES:
            rows = [{key: 1 for key in baseline.PROBE_COLUMNS} for _ in range(5)]
            for row in rows:
                row.update(PreS4_ms=2, Total_ms=10, WorkspaceFree_bytes=900,
                           AfterD2HFree_bytes=800, TotalVRAM_bytes=1000)
            baseline.write_csv(root / f"{site}_probe.csv", rows)
            baseline.dump(root / f"{site}_gpu.json", {
                "total_bytes": 1000, "before_workspace_free_bytes": 950,
                "branch_scratch_A_bytes": 50, "branch_scratch_B_bytes": 50,
            })
            for kind in ("production", "probe"):
                # Bytes are only equality-test tokens, not actual panorama fixtures.
                (root / f"{site}_{kind}.png").write_bytes(b"CPU test token")
                with (root / "logs" / f"{site}_{kind}.stdout").open("w", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(version_columns(4))
                    for label in ("1", "2", "3", "4", "5", "Average", "Minimum"):
                        writer.writerow([label, *([1] * 6), 10, 1, 1, 6])

    def test_analysis_and_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_evidence(root)
            rows = baseline.analyze(root, 5)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["Sampled_min_free_bytes"], 800)
            self.assertEqual(rows[0]["Sampled_max_device_used_bytes"], 200)
            self.assertEqual(baseline.assessment(rows)["frozen_primary"], "site2/large")
            self.assertTrue((root / "memory.csv").is_file())

    def test_panorama_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_evidence(root)
            (root / "site1_probe.png").write_bytes(b"different test token")
            with self.assertRaises(ValueError):
                baseline.analyze(root, 5)

    def test_zip_checksums_and_no_self_inclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "evidence"
            root.mkdir()
            (root / "log.txt").write_text("CPU fixture")
            archive = baseline.package(root)
            with zipfile.ZipFile(archive) as zipped:
                manifest = json.loads(zipped.read("evidence/checksums.json"))
                self.assertEqual(manifest["log.txt"], baseline.sha256(root / "log.txt"))
                self.assertNotIn(archive.name, zipped.namelist())

    def test_plot(self):
        try:
            import matplotlib
        except ImportError:
            self.skipTest("matplotlib unavailable in this CPU environment")
        matplotlib.use("Agg")
        rows = [{"case": f"{site}/large", "PreS4_mean_ms": 1,
                 "PreS4_stdev_ms": 0.1, "Probe_PreS4_share": 0.2} for site in baseline.SITES]
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "plot.png"
            baseline.plot_summary(rows, image)
            self.assertGreater(image.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
