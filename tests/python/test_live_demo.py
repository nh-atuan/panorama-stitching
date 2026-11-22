#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166)
# External source: none

"""Tests for scripts/live_demo.py with a fake stitch; no GPU or binary is needed."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import live_demo  # noqa: E402
from run_benchmark import version_columns  # noqa: E402


def make_csv(version, runs, stages, total):
    """stitch stdout for `version` with identical runs, so Average and Minimum equal one run."""
    extra = [] if version == 0 else [0.5, 1.0, sum(stages)]
    values = [*stages, total, *extra] if version != 2 else [*stages, *extra, total]
    row = ",".join(f"{value:.6f}" for value in values)
    lines = [",".join(version_columns(version))]
    lines += [f"{index},{row}" for index in range(1, runs + 1)]
    lines += [f"Average,{row}", f"Minimum,{row}"]
    return "\n".join(lines) + "\n"


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def fake_stitch(totals, failures=()):
    """subprocess.run stand-in: success CSV per version, or an Error line for `failures`."""
    def run(command, **_):
        version = int(command[command.index("--version") + 1])
        runs = int(command[command.index("--runs") + 1])
        Path(command[3]).parent.mkdir(parents=True, exist_ok=True)
        if version in failures or "challenge" in command[1]:
            return Result(1, "", "[debug] S6 warp_blend\nError: [NumericalFailure] S6 warp_blend failed\n")
        Path(command[3]).write_bytes(b"jpg")
        total = totals[version]
        return Result(0, make_csv(version, runs, [total / 10] * 6, total))
    return run


def make_dataset(root, sites=("site2", "challenge"), sizes=("small", "medium")):
    for site in sites:
        for size in sizes:
            folder = Path(root) / site
            folder.mkdir(parents=True, exist_ok=True)
            for side in ("left", "right"):
                (folder / f"{size}_{side}.jpg").write_bytes(b"jpg")


class ArgumentTests(unittest.TestCase):
    def test_defaults_follow_the_video_outline(self):
        args = live_demo.parse_args([])
        self.assertEqual((args.site, args.size, args.versions), ("site2", "small", [0, 4, 5]))

    def test_unknown_or_repeated_versions_are_rejected(self):
        for versions in (["7"], ["4", "4"]):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                live_demo.parse_args(["--versions", *versions])

    def test_v5_runs_the_dual_schedule(self):
        command = live_demo.demo_command("stitch", "a.jpg", "b.jpg", "p.jpg", 5, 3)
        self.assertEqual(command[-2:], ["--v5-schedule", "dual"])
        self.assertNotIn("--v5-schedule", live_demo.demo_command("stitch", "a", "b", "p", 4, 3))


class RunTests(unittest.TestCase):
    def test_run_version_returns_the_csv_average(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(live_demo.subprocess, "run", side_effect=fake_stitch({4: 20.0})):
            outcome = live_demo.run_version("stitch", "a.jpg", "b.jpg", temp, 4, 3)
        self.assertEqual(outcome["exit_code"], 0)
        self.assertAlmostEqual(outcome["average"]["Total_ms"], 20.0)

    def test_failed_run_keeps_the_error_code(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(live_demo.subprocess, "run", side_effect=fake_stitch({}, failures=(4,))):
            outcome = live_demo.run_version("stitch", "a.jpg", "b.jpg", temp, 4, 1)
        self.assertEqual((outcome["exit_code"], outcome["error"]), (1, "NumericalFailure"))

    def test_timing_table_speedup_uses_the_first_version(self):
        outcomes = [{"version": 0, "average": {**{c: 100.0 for c in live_demo.BASE_STAGE_COLUMNS},
                                                 "Total_ms": 1000.0}},
                    {"version": 4, "average": {**{c: 2.0 for c in live_demo.BASE_STAGE_COLUMNS},
                                                 "Total_ms": 20.0}},
                    {"version": 5, "exit_code": 1, "error": "CudaFailure"}]
        table = live_demo.timing_table(outcomes)
        self.assertIn("50.00x", table)
        self.assertIn("1.00x", table)
        self.assertIn("failed: CudaFailure (exit 1)", table)

    def test_missing_pair_is_a_demo_error(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(live_demo.DemoError):
            live_demo.check_pair(temp, "site2", "small")


class MainTests(unittest.TestCase):
    def run_main(self, temp, extra=(), failures=()):
        stitch = Path(temp) / "stitch"
        stitch.write_bytes(b"")
        make_dataset(Path(temp) / "dataset")
        argv = ["--dataset", str(Path(temp) / "dataset"), "--stitch", str(stitch),
                "--out", str(Path(temp) / "out"), "--skip-build", "--runs", "2", *extra]
        out = io.StringIO()
        with patch.object(live_demo.subprocess, "run",
                          side_effect=fake_stitch({0: 1000.0, 4: 20.0, 5: 19.0}, failures)), \
                patch.object(live_demo, "environment_lines", return_value=["GPU: test"]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = live_demo.main(argv)
        return code, out.getvalue()

    def test_full_demo_writes_panoramas_and_reports_the_challenge(self):
        with tempfile.TemporaryDirectory() as temp:
            code, text = self.run_main(temp)
            self.assertEqual(code, 0)
            for version in (0, 4, 5):
                self.assertTrue((Path(temp) / "out" / "site2_small" / f"v{version}_panorama.jpg").is_file())
        self.assertIn("52.63x", text)
        self.assertIn("challenge/medium stopped with exit code 1: NumericalFailure", text)

    def test_a_failing_version_gives_exit_code_one(self):
        with tempfile.TemporaryDirectory() as temp:
            code, text = self.run_main(temp, ("--skip-challenge",), failures=(5,))
        self.assertEqual(code, 1)
        self.assertNotIn("Challenge pair", text)

    def test_missing_binary_with_skip_build_stops(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()), \
                patch.object(live_demo, "environment_lines", return_value=[]):
            code = live_demo.main(["--stitch", str(Path(temp) / "none"), "--skip-build"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
