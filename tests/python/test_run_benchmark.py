#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166), Nguyen Ho Anh Tuan (23120185)
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

ROOT = Path(__file__).resolve().parents[2]
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
version = int(args[args.index("--version") + 1]) if "--version" in args else 0
left = Path(args[0])
site, size = left.parent.name, left.name.split("_")[0]


def listed(key):
    """True if spec[key] names this site and size, for every version or only the given one."""
    return any(entry[:2] == [site, size] and (len(entry) < 3 or entry[2] == version)
               for entry in spec.get(key, []))


if listed("fail_on"):
    print("[debug] Reading images...", file=sys.stderr)
    print("Error: [NumericalFailure] S6 failed: projective denominator changes sign.", file=sys.stderr)
    sys.exit(1)
stages = spec.get("stages_by_version", {}).get(str(version), spec["stages"])
total = sum(stages) + spec["overhead"]
count = runs - 1 if spec["mode"] == "short" or listed("short_on") else runs
if version == 0:
    row = ",".join(f"{value:.9f}" for value in [*stages, total])
    print("[debug] version=0 seed=16 runs=%d" % runs, file=sys.stderr)
    print("[debug] config: gaussian_sigma=2 seed=16", file=sys.stderr)
    print("Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total_ms")
else:
    h2d = spec.get("h2d", 0.5)
    d2h = spec.get("d2h", 0.5)
    kernel_total = sum(stages)
    columns = [h2d, d2h, kernel_total, total] if version == 2 else [total, h2d, d2h, kernel_total]
    row = ",".join(f"{value:.9f}" for value in [*stages, *columns])
    if spec.get("scaffold"):
        print("Warning: V1 is an infrastructure scaffold with six stubs. Timings are not a benchmark.",
              file=sys.stderr)
    print("[debug] GPU=Tesla T4 version=%d runs=%d seed=16" % (version, runs), file=sys.stderr)
    print("[debug] Config: gaussian_sigma=2 seed=16", file=sys.stderr)
    if version == 2:
        print("Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,H2D_ms,D2H_ms,Total_Kernel_ms,Total_ms")
    else:
        stage_names = ",".join(f"S{index}_V{version}_ms" for index in range(1, 7))
        print(f"Run_Index,{stage_names},Total_ms,H2D_ms,D2H_ms,Total_Kernel_ms")
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

    def stitch_cmd(self, mode="ok", stages=(1.0, 2.0, 3.0, 4.0, 10.0, 5.0), overhead=5.0, **extra):
        """extra: fail_on, short_on ([site, size] or [site, size, version]), stages_by_version, scaffold."""
        spec = self.root / "spec.json"
        spec.write_text(json.dumps({"mode": mode, "stages": list(stages), "overhead": overhead,
                                    "calls": str(self.calls), **extra}))
        return [sys.executable, self.fake, spec]

    def run_quiet(self, stitch_cmd, runs=5, versions=(0,), flat=False, include_challenge=False):
        with redirect_stdout(io.StringIO()):
            return run_benchmark.run_benchmark(
                stitch_cmd, self.fake, self.dataset, runs, self.out,
                versions=versions, flat=flat, include_challenge=include_challenge
            )

    def add_challenge_inputs(self):
        for size in run_benchmark.SIZES:
            for path in run_benchmark.input_paths(self.dataset, run_benchmark.CHALLENGE_SITE, size):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"jpeg")

    def read_csv(self, path):
        with Path(path).open(newline="") as stream:
            return list(csv.DictReader(stream))

    def calls_made(self):
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_full_run_writes_handoff_layout_and_summaries(self):
        self.run_quiet(self.stitch_cmd())
        for site, size in run_benchmark.configurations():
            self.assertTrue((self.out / "v0" / site / f"{size}.csv").is_file())
            self.assertTrue((self.out / "v0" / site / f"{size}.log").is_file())
        self.assertEqual(len(run_benchmark.configurations()), 9)
        with (self.out / "v0" / "summary.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 18)
        self.assertTrue((self.out / "summary.csv").is_file())
        environment = json.loads((self.out / "environment.json").read_text())
        for key in ("gpu", "cpu", "time_utc", "runs", "stitch_sha256", "commands"):
            self.assertIn(key, environment)
        self.assertEqual(len(environment["commands"]), 9)
        self.assertIn("Hot stage", (self.out / "v0" / "summary.md").read_text(encoding="utf-8"))

    def test_flat_layout_for_legacy_compatibility(self):
        self.run_quiet(self.stitch_cmd(), flat=True)
        for site, size in run_benchmark.configurations():
            self.assertTrue((self.out / site / f"{size}.csv").is_file())
            self.assertTrue((self.out / site / f"{size}.log").is_file())
        self.assertTrue((self.out / "summary.csv").is_file())

    def test_multi_version_computes_speedup(self):
        self.run_quiet(self.stitch_cmd(), versions=[0, 1])
        self.assertTrue((self.out / "v0" / "summary.csv").is_file())
        self.assertTrue((self.out / "v1" / "summary.csv").is_file())
        self.assertTrue((self.out / "speedup.csv").is_file())
        self.assertTrue((self.out / "speedup.md").is_file())
        with (self.out / "speedup.csv").open(newline="") as stream:
            speedup_rows = list(csv.DictReader(stream))
        self.assertEqual(len(speedup_rows), 18)  # 9 config * 2 versions
        v1_rows = [r for r in speedup_rows if r["version"] == "V1"]
        self.assertEqual(len(v1_rows), 9)
        for r in v1_rows:
            self.assertGreater(float(r["speedup_vs_v0"]), 0.0)

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
        self.assertIn("Detect failed", (self.out / "v0" / "site1" / "small.log").read_text())

    def test_malformed_csv_is_rejected(self):
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, "Invalid CSV from site1/small"):
            self.run_quiet(self.stitch_cmd(mode="short"))

    def test_command_arguments(self):
        self.run_quiet(self.stitch_cmd(), runs=3)
        first = self.calls_made()[0]
        left, right = run_benchmark.input_paths(self.dataset, "site1", "small")
        self.assertEqual(first, [str(left), str(right), str(self.out / "v0" / "site1" / "small_panorama.jpg"),
                                 "--version", "0", "--runs", "3", "--debug"])

    def test_debug_config_is_read_from_log(self):
        version, config = run_benchmark.read_debug_config(
            "[debug] Reading images...\n[debug] version=0 seed=16 runs=5\n"
            "[debug] config: gaussian_sigma=2 seed=16\n")
        self.assertEqual(version, "[debug] version=0 seed=16 runs=5")
        self.assertEqual(config, "[debug] config: gaussian_sigma=2 seed=16")
        self.assertEqual(run_benchmark.read_debug_config("no debug"), ["", ""])
        self.run_quiet(self.stitch_cmd())
        self.assertIn("seed=16", (self.out / "v0" / "summary.md").read_text(encoding="utf-8"))

    def test_default_run_skips_challenge(self):
        self.run_quiet(self.stitch_cmd())
        self.assertFalse(any("challenge" in " ".join(call) for call in self.calls_made()))
        self.assertFalse((self.out / "v0" / "failures.csv").exists())
        self.assertFalse(json.loads((self.out / "environment.json").read_text())["include_challenge"])

    def test_include_challenge_needs_challenge_inputs(self):
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, "challenge"):
            self.run_quiet(self.stitch_cmd(), include_challenge=True)
        self.assertEqual(self.calls_made(), [])

    def test_include_challenge_runs_twelve_configurations(self):
        self.add_challenge_inputs()
        self.assertEqual(len(run_benchmark.configurations(include_challenge=True)), 12)
        self.run_quiet(self.stitch_cmd(), include_challenge=True)
        self.assertEqual(len(self.calls_made()), 12)
        self.assertEqual(len(self.read_csv(self.out / "v0" / "summary.csv")), 24)
        self.assertEqual((self.out / "v0" / "failures.csv").read_text().splitlines(),
                         [",".join(run_benchmark.FAILURE_COLUMNS)])
        self.assertTrue(json.loads((self.out / "environment.json").read_text())["include_challenge"])

    def test_challenge_failures_are_recorded_and_left_out_of_speedup(self):
        self.add_challenge_inputs()
        failing = [["challenge", "medium"], ["challenge", "large"]]
        self.run_quiet(self.stitch_cmd(fail_on=failing), versions=[0, 1], include_challenge=True)
        for version in (0, 1):
            failures = self.read_csv(self.out / f"v{version}" / "failures.csv")
            self.assertEqual([(row["site"], row["size"]) for row in failures],
                             [("challenge", "medium"), ("challenge", "large")])
            for row in failures:
                self.assertEqual((row["version"], row["exit_code"], row["error"]),
                                 (f"V{version}", "1", "NumericalFailure"))
            self.assertEqual(len(self.read_csv(self.out / f"v{version}" / "summary.csv")), 20)
            text = (self.out / f"v{version}" / "summary.md").read_text(encoding="utf-8")
            self.assertIn("Failed configurations", text)
            self.assertIn("NumericalFailure", text)
        speedups = self.read_csv(self.out / "speedup.csv")
        challenge = [(row["version"], row["size"]) for row in speedups if row["site"] == "challenge"]
        self.assertEqual(challenge, [("V0", "small"), ("V1", "small")])
        self.assertEqual(len(speedups), 20)
        self.assertIn("challenge/medium", (self.out / "speedup.md").read_text(encoding="utf-8"))

    def test_challenge_failing_only_in_v0_leaves_speedup_cells_empty(self):
        self.add_challenge_inputs()
        self.run_quiet(self.stitch_cmd(fail_on=[["challenge", "medium", 0]]), versions=[0, 1],
                       include_challenge=True)
        rows = {(row["version"], row["site"], row["size"]): row
                for row in self.read_csv(self.out / "speedup.csv")}
        self.assertNotIn(("V0", "challenge", "medium"), rows)
        v1 = rows[("V1", "challenge", "medium")]
        for column in ("speedup_vs_v0", "speedup_vs_prev", "kernel_speedup_vs_v0", "S1_speedup_vs_v0"):
            self.assertEqual(v1[column], "", column)
        self.assertGreater(float(v1["Total_ms"]), 0.0)
        self.assertEqual(self.read_csv(self.out / "v1" / "failures.csv"), [])

    def test_standard_site_failure_still_stops_with_challenge(self):
        self.add_challenge_inputs()
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, r"site2/small.*exit code 1"):
            self.run_quiet(self.stitch_cmd(fail_on=[["site2", "small"]]), include_challenge=True)

    def test_challenge_malformed_csv_is_rejected(self):
        self.add_challenge_inputs()
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, "Invalid CSV from challenge/small"):
            self.run_quiet(self.stitch_cmd(short_on=[["challenge", "small"]]), include_challenge=True)

    def test_read_error_code(self):
        self.assertEqual(run_benchmark.read_error_code(
            "[debug] Reading images...\nError: [NumericalFailure] S6 failed.\n"), "NumericalFailure")
        self.assertEqual(run_benchmark.read_error_code("Segmentation fault\n"), "unknown")

    def test_v1_scaffold_timings_are_rejected(self):
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, r"site1/small.*scaffold"):
            self.run_quiet(self.stitch_cmd(scaffold=True), versions=[0, 1])
        self.assertFalse((self.out / "speedup.csv").exists())

    def test_csv_header_must_match_version(self):
        stages = ",".join(f"S{index}_V1_ms" for index in range(1, 7))
        row = "1.0,1.0,1.0,1.0,1.0,1.0,7.0,0.5,0.5,6.0"
        text = "\n".join([f"Run_Index,{stages},Total_ms,H2D_ms,D2H_ms,Total_Kernel_ms",
                          f"1,{row}", f"Average,{row}", f"Minimum,{row}"])
        self.assertEqual(run_benchmark.parse_version_csv(text, 1, version=1)["average"]["S1_ms"], 1.0)
        for version in (0, 2):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, "header"):
                run_benchmark.parse_version_csv(text, 1, version=version)
        v0 = "\n".join(["Run_Index,S1_ms,S2_ms,S3_ms,S4_ms,S5_ms,S6_ms,Total",
                        "1,1,1,1,1,1,1,7", "Average,1,1,1,1,1,1,7", "Minimum,1,1,1,1,1,1,7"])
        with self.assertRaisesRegex(ValueError, "header"):
            run_benchmark.parse_version_csv(v0, 1, version=0)

    def test_total_smaller_than_stage_sum_is_rejected(self):
        with self.assertRaisesRegex(run_benchmark.BenchmarkError, "Invalid CSV from site1/small"):
            self.run_quiet(self.stitch_cmd(overhead=-1.0))

    def test_per_stage_speedup_against_v0_and_previous(self):
        v1 = [0.5, 1.0, 1.0, 1.0, 2.0, 5.0]
        v2 = [0.5, 1.0, 1.0, 0.5, 2.0, 5.0]
        self.run_quiet(self.stitch_cmd(stages_by_version={"1": v1, "2": v2}), versions=[0, 1, 2])
        rows = {(row["version"], row["site"], row["size"]): row
                for row in self.read_csv(self.out / "speedup.csv")}
        first = rows[("V1", "site1", "small")]  # V0 stages are 1, 2, 3, 4, 10, 5 ms.
        for index, expected in enumerate([2.0, 2.0, 3.0, 4.0, 5.0, 1.0], start=1):
            self.assertAlmostEqual(float(first[f"S{index}_speedup_vs_v0"]), expected)
            self.assertAlmostEqual(float(first[f"S{index}_speedup_vs_prev"]), expected)
        second = rows[("V2", "site1", "small")]
        self.assertAlmostEqual(float(second["S4_speedup_vs_prev"]), 2.0)
        self.assertAlmostEqual(float(second["S4_speedup_vs_v0"]), 8.0)
        self.assertAlmostEqual(float(second["S1_speedup_vs_prev"]), 1.0)
        self.assertAlmostEqual(float(rows[("V0", "site1", "small")]["S3_speedup_vs_v0"]), 1.0)
        self.assertIn("Per-stage speedup", (self.out / "speedup.md").read_text(encoding="utf-8"))

    def test_parse_args_include_challenge(self):
        base = ["--stitch", "s", "--dataset", "d", "--out", "o"]
        self.assertFalse(run_benchmark.parse_args(base).include_challenge)
        self.assertTrue(run_benchmark.parse_args([*base, "--include-challenge"]).include_challenge)

    def test_main_rejects_missing_binary(self):
        with redirect_stderr(io.StringIO()) as error:
            code = run_benchmark.main(["--stitch", str(self.root / "nope"), "--dataset", str(self.dataset),
                                       "--out", str(self.out)])
        self.assertEqual(code, 1)
        self.assertIn("not found", error.getvalue())


if __name__ == "__main__":
    unittest.main()
