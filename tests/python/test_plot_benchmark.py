#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166), Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Tests for scripts/plot_benchmark.py on summary files with known numbers."""

import csv
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "python"))
import plot_benchmark  # noqa: E402
import run_benchmark  # noqa: E402
import test_run_benchmark  # noqa: E402  (module import, so its tests are not collected twice)

# S4 is hot at small and medium, S2 at large for site1, S6 at large for the other sites.
STAGES_BY_SIZE = {
    "small": (1.0, 2.0, 1.0, 10.0, 1.0, 5.0),
    "medium": (2.0, 6.0, 2.0, 10.0, 1.0, 9.0),
}
LARGE = {"site1": (5.0, 20.0, 5.0, 10.0, 2.0, 18.0),
         "site2": (5.0, 16.0, 5.0, 10.0, 2.0, 22.0),
         "site3": (5.0, 15.0, 5.0, 10.0, 2.0, 23.0)}


def stages_for(site, size):
    return LARGE[site] if size == "large" else STAGES_BY_SIZE[size]


def write_summary(path, skip=None):
    """Write a summary.csv as run_benchmark does, with Total_ms equal to the sum of the stages."""
    rows = []
    for site, size in run_benchmark.configurations():
        if (site, size) == skip:
            continue
        stages = stages_for(site, size)
        parsed = {"average": dict(zip(run_benchmark.TIMING_COLUMNS, [*stages, sum(stages)])),
                  "minimum": dict(zip(run_benchmark.TIMING_COLUMNS, [*stages, sum(stages)]))}
        rows.extend(run_benchmark.summary_rows(site, size, parsed))
    run_benchmark.write_summary_csv(path, rows)


class PlotBenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.summary = self.root / "summary.csv"
        self.out = self.root / "analysis"

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_charts_and_tables(self):
        write_summary(self.summary)
        plot_benchmark.analyse(self.summary, self.out)
        for name in ("stage_timing.png", "stage_share.png"):
            path = self.out / name
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        with (self.out / "hot_stages.csv").open(newline="") as stream:
            self.assertEqual(len(list(csv.DictReader(stream))), 9)
        text = (self.out / "hot_stages.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("| site"), 9)

    def test_hot_stage_share_p_and_limit(self):
        write_summary(self.summary)
        table, _ = plot_benchmark.analyse(self.summary, self.out)
        rows = {(row["site"], row["size"]): row for row in table}
        small = rows[("site1", "small")]  # S4 = 10 of 20 ms
        self.assertEqual(small["hot_stage"], "S4")
        self.assertAlmostEqual(small["hot_pct"], 50.0, places=4)
        self.assertAlmostEqual(small["p_hot"], 0.5, places=6)
        self.assertAlmostEqual(small["amdahl_limit"], 2.0, places=5)
        self.assertEqual(rows[("site1", "large")]["hot_stage"], "S2")
        self.assertEqual(rows[("site2", "large")]["hot_stage"], "S6")

    def test_mean_shares_by_size(self):
        write_summary(self.summary)
        _, means = plot_benchmark.analyse(self.summary, self.out)
        self.assertAlmostEqual(means["small"]["shares"][3], 50.0, places=4)
        self.assertAlmostEqual(sum(means["medium"]["shares"]), 100.0, places=3)
        self.assertEqual(means["small"]["hot_stage"], "S4")
        self.assertEqual(means["large"]["hot_stage"], "S6")  # mean of 30.0, 36.7, 38.3 %

    def test_summary_line_names_stage_and_sites(self):
        write_summary(self.summary)
        table, _ = plot_benchmark.analyse(self.summary, self.out)
        line = plot_benchmark.hot_stage_summary(table)
        self.assertIn("small: S4 (site1, site2, site3)", line)
        self.assertIn("large: S2 (site1); S6 (site2, site3)", line)

    def test_missing_configuration_is_rejected(self):
        write_summary(self.summary, skip=("site3", "medium"))
        with self.assertRaisesRegex(plot_benchmark.AnalysisError, "site3/medium"):
            plot_benchmark.analyse(self.summary, self.out)
        self.assertFalse((self.out / "stage_timing.png").exists())

    def test_minimum_rows_are_ignored(self):
        write_summary(self.summary)
        averages = plot_benchmark.load_averages(self.summary)
        self.assertEqual(len(averages), 9)
        self.assertTrue(all(row["stat"] == "average" for row in averages.values()))

    def test_main_reports_missing_summary(self):
        with redirect_stderr(io.StringIO()) as err:
            code = plot_benchmark.main(["--summary", str(self.root / "none.csv"), "--out", str(self.out)])
        self.assertEqual(code, 1)
        self.assertIn("summary not found", err.getvalue())

    def test_reads_summary_written_by_run_benchmark(self):
        helper = test_run_benchmark.RunBenchmarkTest("test_full_run_writes_handoff_layout_and_summaries")
        helper.setUp()
        try:
            helper.run_quiet(helper.stitch_cmd())
            with redirect_stdout(io.StringIO()):
                code = plot_benchmark.main(["--summary", str(helper.out / "summary.csv"),
                                            "--out", str(self.out)])
            self.assertEqual(code, 0)
            self.assertTrue((self.out / "hot_stages.md").is_file())
        finally:
            helper.tearDown()

    def test_plots_speedup_chart(self):
        speedup_csv = self.root / "speedup.csv"
        rows = [
            {"site": site, "size": size, "version": "V1", "Total_ms": 10.0, "Total_Kernel_ms": 8.0,
             "speedup_vs_v0": 2.5, "speedup_vs_prev": 2.5, "kernel_speedup_vs_v0": 3.0}
            for site in run_benchmark.BENCHMARK_SITES for size in SIZES
        ]
        run_benchmark.write_speedup_csv(speedup_csv, rows)
        with redirect_stdout(io.StringIO()):
            code = plot_benchmark.main(["--speedup", str(speedup_csv), "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertTrue((self.out / "speedup.png").is_file())
        self.assertEqual((self.out / "speedup.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
