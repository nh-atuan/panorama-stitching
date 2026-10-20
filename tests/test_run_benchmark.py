#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166)
# External source: none

"""Tests for scripts/run_benchmark.py with a fake stitch, so no GPU or nvcc is needed."""

import csv
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_benchmark  # noqa: E402

# The fake reads its behaviour from a JSON file, then the stitch arguments follow.
FAKE_STITCH = r'''
import json, sys
from pathlib import Path
spec = json.loads(Path(sys.argv[1]).read_text())
args = sys.argv[2:]
Path(spec["calls"]).open("a").write(json.dumps(args) + "\n")
if spec["mode"] == "fail":
    print("[error] Detect failed.", file=sys.stderr)
    sys.exit(3)
runs = int(args[args.index("--runs") + 1])
stages = spec["stages"]
total = sum(stages) + spec["overhead"]
row = ",".join(f"{value:.9f}" for value in [*stages, total])
print("[debug] version=0 seed=16 runs=%d" % runs, file=sys.stderr)
print("[debug] config: gaussian_sigma=2 seed=16", file=sys.stderr)
print("Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total_ms")
count = runs - 1 if spec["mode"] == "short" else runs
for index in range(1, count + 1):
    print(f"{index},{row}")
print(f"Average,{row}")
print(f"Minimum,{row}")
'''


class RunBenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.dataset = self.root / "dataset"
        for site, size in run_benchmark.configurations():
            for path in run_benchmark.input_paths(self.dataset, site, size):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"jpeg")
        self.fake = self.root / "fake_stitch.py"
        self.fake.write_text(FAKE_STITCH)
        self.calls = self.root / "calls.txt"
        self.out = self.root / "out"

    def tearDown(self):
        self.tmp.cleanup()

    def stitch_cmd(self, mode="ok", stages=(1.0, 2.0, 3.0, 4.0, 10.0, 5.0), overhead=5.0):
        spec = self.root / "spec.json"
        spec.write_text(json.dumps({"mode": mode, "stages": list(stages), "overhead": overhead,
                                    "calls": str(self.calls)}))
        return [sys.executable, self.fake, spec]

    def run_quiet(self, stitch_cmd, runs=5):
        with redirect_stdout(io.StringIO()):
            return run_benchmark.run_benchmark(stitch_cmd, self.fake, self.dataset, runs, self.out)

    def calls_made(self):
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_full_run_writes_handoff_layout_and_summaries(self):
        self.run_quiet(self.stitch_cmd())
        for site, size in run_benchmark.configurations():
            self.assertTrue((self.out / site / f"{size}.csv").is_file())
            self.assertTrue((self.out / site / f"{size}.log").is_file())
        self.assertEqual(len(run_benchmark.configurations()), 9)
        with (self.out / "summary.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 18)
        self.assertEqual(list(rows[0]), run_benchmark.SUMMARY_COLUMNS)
        environment = json.loads((self.out / "environment.json").read_text())
        for key in ("gpu", "cpu", "time_utc", "runs", "stitch_sha256", "commands"):
            self.assertIn(key, environment)
        self.assertEqual(len(environment["commands"]), 9)
        self.assertIn("Hot stage", (self.out / "summary.md").read_text(encoding="utf-8"))

    def test_percentages_hot_stage_and_amdahl(self):
        rows = self.run_quiet(self.stitch_cmd())
        average, minimum = rows[0], rows[1]
        # Total = 1 + 2 + 3 + 4 + 10 + 5 + 5 overhead = 30 ms.
        self.assertAlmostEqual(average["S5_pct"], 100.0 / 3.0)
        self.assertAlmostEqual(average["S1_pct"], 100.0 / 30.0)
        self.assertAlmostEqual(average["other_pct"], 100.0 / 6.0)
        self.assertEqual(average["hot_stage"], "S5")
        self.assertAlmostEqual(average["p_hot"], 1.0 / 3.0)
        self.assertAlmostEqual(average["amdahl_limit"], 1.5)
        self.assertEqual(minimum["stat"], "minimum")
        self.assertNotIn("S1_pct", minimum)
        self.assertNotIn("amdahl_limit", minimum)

    def test_hot_stage_tie_picks_earlier_stage(self):
        self.assertEqual(run_benchmark.hot_stage([30.0, 30.0, 5.0, 5.0, 5.0, 5.0]), 0)
        rows = self.run_quiet(self.stitch_cmd(stages=(5.0, 5.0, 1.0, 1.0, 1.0, 1.0), overhead=0.0))
        self.assertEqual(rows[0]["hot_stage"], "S1")

    def test_runs_must_be_positive_integer(self):
        for value in ("0", "-1", "abc", "2.5"):
            with self.subTest(value=value), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    run_benchmark.parse_args(["--stitch", "s", "--dataset", "d", "--out", "o", "--runs", value])
        self.assertEqual(run_benchmark.parse_args(["--stitch", "s", "--dataset", "d", "--out", "o"]).runs, 5)

    def test_missing_input_fails_before_any_stitch_call(self):
        (self.dataset / "site2" / "medium_right.jpg").unlink()
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, "medium_right.jpg"):
            self.run_quiet(self.stitch_cmd())
        self.assertEqual(self.calls_made(), [])

    def test_stitch_failure_stops_with_log_path(self):
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, r"exit code 3.*small\.log"):
            self.run_quiet(self.stitch_cmd(mode="fail"))
        self.assertEqual(len(self.calls_made()), 1)
        self.assertIn("Detect failed", (self.out / "site1" / "small.log").read_text())

    def test_malformed_csv_is_rejected(self):
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, "Invalid CSV from site1/small"):
            self.run_quiet(self.stitch_cmd(mode="short"))

    def test_command_arguments(self):
        self.run_quiet(self.stitch_cmd(), runs=3)
        first = self.calls_made()[0]
        left, right = run_benchmark.input_paths(self.dataset, "site1", "small")
        self.assertEqual(first, [str(left), str(right), str(self.out / "site1" / "small_panorama.jpg"),
                                 "--version", "0", "--runs", "3", "--debug"])

    def test_debug_config_is_read_from_log(self):
        version, config = run_benchmark.read_debug_config(
            "[debug] Reading images...\n[debug] version=0 seed=16 runs=5\n"
            "[debug] config: gaussian_sigma=2 seed=16\n")
        self.assertEqual(version, "[debug] version=0 seed=16 runs=5")
        self.assertEqual(config, "[debug] config: gaussian_sigma=2 seed=16")
        self.assertEqual(run_benchmark.read_debug_config("no debug"), ["", ""])
        self.run_quiet(self.stitch_cmd())
        self.assertIn("seed=16", (self.out / "summary.md").read_text(encoding="utf-8"))

    def test_main_rejects_missing_binary(self):
        with redirect_stderr(io.StringIO()) as error:
            code = run_benchmark.main(["--stitch", str(self.root / "nope"), "--dataset", str(self.dataset),
                                       "--out", str(self.out)])
        self.assertEqual(code, 1)
        self.assertIn("not found", error.getvalue())


if __name__ == "__main__":
    unittest.main()
