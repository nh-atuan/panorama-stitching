#!/usr/bin/env python3
# Authors: Le Thuong De (23120232)
# External source: none
"""Failure handling, retained evidence, and independent synthetic accuracy fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import profiler_batch
import profiling_common
import run_profiling
import synthetic_batch


class CaptureTests(unittest.TestCase):
    def test_captures_argv_output_and_failure_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "run"
            argv = [sys.executable, "-c", "import sys;print('value; $(literal)');print('bad',file=sys.stderr);sys.exit(7)"]
            result, out, err = profiling_common.capture(argv, prefix)
            self.assertEqual(result["returncode"], 7)
            self.assertIn("$(literal)", out)
            self.assertIn("bad", err)
            self.assertEqual(json.loads(prefix.with_suffix(".command.json").read_text())["command"], argv)
            self.assertEqual(prefix.with_suffix(".stdout").read_text(), out)

    def test_timeout_is_retained(self):
        with tempfile.TemporaryDirectory() as directory, patch("profiling_common.subprocess.run", side_effect=
                subprocess.TimeoutExpired(["fake"], 1, output=b"partial", stderr=b"waiting")):
            record, out, err = profiling_common.capture(["fake"], Path(directory) / "run", 1)
            self.assertTrue(record["timeout"])
            self.assertIsNone(record["returncode"])
            self.assertEqual((out, err), ("partial", "waiting"))

    def test_missing_executable_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            record, _, err = profiling_common.capture([str(Path(directory) / "absent")], Path(directory) / "run")
            self.assertIsNone(record["returncode"])
            self.assertTrue(err)

    def test_stub_detection(self):
        self.assertTrue(profiling_common.reject_stub("Warning: V1 is an infrastructure scaffold"))
        self.assertFalse(profiling_common.reject_stub("real kernel launch"))

    @patch("profiling_common.shutil.which", return_value=None)
    def test_t4_guard_rejects_missing_gpu(self, _):
        with self.assertRaises(profiling_common.BatchError):
            profiling_common.inspect_environment(require_t4=True)


class ProfilerTests(unittest.TestCase):
    @patch("profiler_batch.shutil.which", return_value=None)
    def test_missing_profiler_is_not_success(self, _):
        with tempfile.TemporaryDirectory() as directory:
            result = profiler_batch.collect("ncu", ["binary"], directory)
            self.assertEqual(result["status"], "unavailable")

    @patch("profiler_batch.shutil.which", return_value="ncu")
    @patch("profiler_batch.capture", return_value=({"returncode": 0}, "ERR_NVGPUCTRPERM", ""))
    def test_counter_permission_denial_even_when_exit_zero(self, *_):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(profiler_batch.collect("ncu", ["binary"], directory)["status"], "unavailable")

    @patch("profiler_batch.shutil.which", return_value="nsys")
    @patch("profiler_batch.capture", return_value=({"returncode": 0}, "", ""))
    def test_missing_report_rejected(self, *_):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(profiler_batch.collect("nsys", ["binary"], directory)["status"], "failed")

    @patch("profiler_batch.shutil.which", return_value="ncu")
    def test_exports_actual_report_and_keeps_filter(self, _):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def capture(argv, prefix):
                calls.append(argv)
                if "--export" in argv:
                    Path(argv[argv.index("--export") + 1] + ".ncu-rep").write_bytes(b"fixture")
                return {"returncode": 0}, "metrics", ""
            with patch("profiler_batch.capture", side_effect=capture):
                result = profiler_batch.collect("ncu", ["binary", "a b.png"], directory, "nearest_two", 2)
            self.assertEqual(result["status"], "ok")
            self.assertIn("regex:nearest_two", calls[0])
            self.assertEqual(calls[0][-1], "a b.png")
            self.assertIn("--import", calls[1])

    @patch("profiler_batch.shutil.which", return_value="ncu")
    @patch("profiler_batch.capture", return_value=({"returncode": 0}, "No kernels were profiled", ""))
    def test_empty_kernel_capture_rejected(self, *_):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(profiler_batch.collect("ncu", ["binary"], directory)["status"], "failed")

    @patch("profiler_batch.shutil.which", return_value="nsys")
    @patch("profiler_batch.capture", return_value=({"returncode": 0}, "", "Verification scope: S4-S5 only"))
    def test_profile_rejects_stage_driver_in_pipeline_scope(self, *_):
        with tempfile.TemporaryDirectory() as directory:
            result = profiler_batch.collect("nsys", ["binary"], directory)
            self.assertEqual(result["reason"], "stage driver is not a full CUDA pipeline")


class SyntheticTests(unittest.TestCase):
    def test_preflight_requires_all_six_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(profiling_common.BatchError):
                synthetic_batch.inputs(directory)

    def check(self, log, scope="pipeline", returncode=0):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        folder = Path(directory.name)
        truth = folder / "truth.json"
        truth.write_text(json.dumps({"width": 64, "height": 36, "H_gt": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}))
        pair = ("translation", "small", folder / "left.png", folder / "right.png", truth)
        def capture(argv, prefix):
            Path(argv[3]).write_bytes(b"fixture panorama")
            return {"returncode": returncode}, "", log
        with patch("synthetic_batch.capture", side_effect=capture):
            return synthetic_batch.check_case("binary", 1, pair, folder / "output", scope)

    def test_identity_has_zero_error(self):
        result = self.check("[debug] H(B->A)=1 0 0 0 1 0 0 0 1")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["rmse_px"], 0)
        self.assertEqual(result["points"], 400)

    def test_known_translation_exceeds_bound(self):
        result = self.check("[debug] H(B->A)=1 0 2 0 1 0 0 0 1")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["rmse_px"], 2)

    def test_missing_h_and_failed_process(self):
        self.assertEqual(self.check("no H")["status"], "failed")
        self.assertEqual(self.check("no H", returncode=3)["reason"], "executable failed")

    def test_stub_rejected(self):
        self.assertEqual(self.check("infrastructure scaffold\n[debug] H(B->A)=1 0 0 0 1 0 0 0 1")["status"], "failed")

    def test_stage_scope_is_explicit(self):
        log = "Verification scope: S4-S5 only; CPU S1-S3/S6.\n[debug] H(B->A)=1 0 0 0 1 0 0 0 1"
        self.assertEqual(self.check(log)["status"], "failed")
        self.assertEqual(self.check(log, "s45")["status"], "ok")


class BatchTests(unittest.TestCase):
    def test_standalone_command_preserves_option_arguments(self):
        args = run_profiling.parse_args(["--out", "output", "--profile-command", "binary", "--version", "1", "--runs", "1"])
        self.assertEqual(args.profile_command, ["binary", "--version", "1", "--runs", "1"])

    def test_failed_profile_makes_batch_fail_and_saves_summary(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch("run_profiling.inspect_environment", return_value={"gpu": "fixture"}), \
                patch("run_profiling.collect", return_value={"status": "failed", "reason": "fixture"}):
            out = Path(directory) / "batch"
            status = run_profiling.main(["--out", str(out), "--profilers", "ncu", "--profile-command", sys.executable])
            self.assertEqual(status, 1)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["scope"], "standalone")
            self.assertEqual(summary["profiling"][0]["status"], "failed")
            self.assertTrue((out / "environment.json").is_file())

    def test_preserves_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch("run_profiling.inspect_environment", return_value={}):
            sentinel = Path(directory) / "keep.log"
            sentinel.write_text("existing evidence")
            with self.assertRaises(profiling_common.BatchError):
                run_profiling.main(["--out", directory, "--profile-command", sys.executable])
            self.assertEqual(sentinel.read_text(), "existing evidence")


if __name__ == "__main__":
    unittest.main()
