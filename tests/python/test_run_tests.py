#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166), Le Ha Thanh Chuong (23120195)
# External source: none

"""Tests for tests/run_tests.py; compile lines are only inspected, so no GPU or nvcc is needed."""

import contextlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import run_tests  # noqa: E402


class PassLineTest(unittest.TestCase):
    def test_every_suite_format_is_counted(self):
        self.assertEqual(run_tests.parse_pass_count("PASS: 19524 assertions for S2 FAST-9 detection\n"), 19524)
        self.assertEqual(run_tests.parse_pass_count("GPU: Tesla T4\nPASS GPU S4: 2387 checks\n"), 2387)
        self.assertEqual(run_tests.parse_pass_count("PASS reference support: 41 checks\n"), 41)
        line = "PASS: 709 checks, 66 V0/V1 comparisons; max RGB error=0, threshold=1\n"
        self.assertEqual(run_tests.parse_pass_count(line), 709)

    def test_output_without_pass_is_rejected(self):
        self.assertIsNone(run_tests.parse_pass_count("FAIL: gray differs\n"))
        self.assertIsNone(run_tests.parse_pass_count("no PASS: here 3 checks\n"))
        self.assertIsNone(run_tests.parse_pass_count(""))


class GpuCommandTest(unittest.TestCase):
    def command(self, name, platform_name="linux"):
        return run_tests.gpu_suite_command("nvcc", name, "build/bin", "build/stb_impl.o", platform_name)

    def test_official_flags(self):
        command = self.command("gpu_s4")
        self.assertIn("-arch=sm_75", command)
        self.assertIn("--fmad=false", command)
        host_flags = next(flag for flag in command if flag.startswith("-Xcompiler="))
        for flag in ("-Werror", "-ffp-contract=off", "-fno-tree-vectorize"):
            self.assertIn(flag, host_flags)

    def test_s6_gets_the_allocator_wrap_and_stb(self):
        command = self.command("gpu_s6")
        self.assertIn("-Xlinker=--wrap=cudaMalloc", command)
        self.assertIn("build/stb_impl.o", command)

    def test_other_suites_do_not(self):
        command = self.command("gpu_s5")
        self.assertNotIn("-Xlinker=--wrap=cudaMalloc", command)
        self.assertNotIn("build/stb_impl.o", command)

    def test_v2_links_real_s5_in_both_modes_and_requires_both_integration_files(self):
        for files in (set(), {run_tests.V2_PIPELINE_HEADER},
                      {run_tests.V2_PIPELINE_HEADER, run_tests.V2_PIPELINE_SOURCE}):
            with mock.patch.object(Path, "is_file", autospec=True,
                                   side_effect=lambda path: path.relative_to(ROOT).as_posix() in files):
                command = self.command(run_tests.V2_PIPELINE_SUITE)
            self.assertIn("src/v2/s5/v2_homography.cu", command)
            self.assertIn("build/stb_impl.o", command)
            self.assertEqual("-DV2_PIPELINE_AVAILABLE" in command, len(files) == 2)
            self.assertEqual(run_tests.V2_PIPELINE_SOURCE in command, len(files) == 2)

    def test_v3_requires_both_integration_files_and_links_real_sources(self):
        with TemporaryDirectory() as directory, mock.patch.object(run_tests, "ROOT", Path(directory)):
            root = Path(directory)
            for name in (run_tests.V3_PIPELINE_HEADER, run_tests.V3_PIPELINE_SOURCE,
                         "src/v3/s5/v3_homography.cu"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
                if name == run_tests.V3_PIPELINE_HEADER:
                    with self.assertRaisesRegex(RuntimeError, "Production V3 pipeline"):
                        self.command(run_tests.V3_PIPELINE_SUITE)
            command = self.command(run_tests.V3_PIPELINE_SUITE)
            for value in ("-arch=sm_75", "-DV3_PIPELINE_AVAILABLE", run_tests.V3_PIPELINE_SOURCE,
                          run_tests.V2_PIPELINE_SOURCE, "src/v3/s5/v3_homography.cu", "build/stb_impl.o"):
                self.assertIn(value, command)

    def test_explicit_v3_fails_before_build_if_production_is_absent(self):
        args = SimpleNamespace(suite=[run_tests.V3_PIPELINE_SUITE])
        with mock.patch.object(run_tests, "v3_pipeline_available", return_value=False), \
                mock.patch.object(run_tests, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "P8-T02"):
                run_tests.run_gpu_group(args, {})
        run.assert_not_called()

    def test_stb_is_not_built_with_strict_warnings(self):
        command = run_tests.gpu_stb_command("nvcc", "build/stb_impl.o")
        self.assertIn(run_tests.STB_SOURCE, command)
        self.assertFalse(any("-Werror" in flag for flag in command))

    def test_ldl_only_on_linux(self):
        self.assertIn("-ldl", self.command("gpu_s4"))
        self.assertNotIn("-ldl", self.command("gpu_s4", "win32"))

    def test_registered_sources_exist(self):
        suites = {**run_tests.V0_SUITES, **run_tests.GPU_SUITES}
        for name, sources in suites.items():
            for source in sources:
                self.assertTrue((ROOT / source).is_file(), f"{name}: {source}")

    def test_options_name_known_suites(self):
        known = set(run_tests.GPU_SUITES)
        self.assertLessEqual(set(run_tests.GPU_LINK_FLAGS), known)
        self.assertLessEqual(run_tests.GPU_STB_SUITES, known)


class MainTest(unittest.TestCase):
    def run_main(self, argv):
        output = io.StringIO()
        with mock.patch.object(run_tests, "run_v0_group") as v0, \
                mock.patch.object(run_tests, "run_gpu_group") as gpu, \
                mock.patch.object(run_tests, "run_python_group") as python, \
                contextlib.redirect_stdout(output):
            run_tests.main(argv)
        return output.getvalue(), v0, gpu, python

    def test_list_names_every_group_and_runs_nothing(self):
        text, v0, gpu, python = self.run_main(["--list"])
        for name in ("preprocess", "gpu_s6", "gpu_reference", "gpu_v3_pipeline", "test_run_tests.py"):
            self.assertIn(name, text)
        for group in (v0, gpu, python):
            group.assert_not_called()

    def test_group_all_without_nvcc_skips_gpu_and_says_so(self):
        with mock.patch.object(run_tests, "is_nvcc", return_value=False):
            text, v0, gpu, python = self.run_main(["--compiler", "g++"])
        gpu.assert_not_called()
        v0.assert_called_once()
        python.assert_called_once()
        self.assertIn("Skip gpu suites", text)

    def test_group_all_with_nvcc_runs_gpu(self):
        with mock.patch.object(run_tests, "is_nvcc", return_value=True):
            _, _, gpu, _ = self.run_main([])
        gpu.assert_called_once()

    def test_explicit_gpu_group_is_never_skipped(self):
        with mock.patch.object(run_tests, "is_nvcc", return_value=False):
            _, _, gpu, _ = self.run_main(["--group", "gpu", "--compiler", "g++"])
        gpu.assert_called_once()

    def test_explicit_gpu_suite_is_never_skipped(self):
        with mock.patch.object(run_tests, "is_nvcc", return_value=False):
            _, _, gpu, _ = self.run_main(["--suite", "gpu_s6", "--compiler", "g++"])
        gpu.assert_called_once()

    def test_gpu_suite_outside_its_group_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.run_main(["--group", "v0", "--suite", "gpu_s6"])

    def test_v2_options_cannot_silently_target_another_suite(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_main(["--group", "gpu", "--suite", "gpu_s6", "--require-v2-pipeline"])

    def test_v3_acceptance_requires_both_fixture_directories(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_main(["--group", "gpu", "--suite", "gpu_v3_pipeline", "--v3-dataset-dir", "dataset"])


class SyntheticArgumentsTest(unittest.TestCase):
    def test_all_six_truth_matrices_are_forwarded_and_direction_is_enforced(self):
        matrix = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for case in ("translation", "projective"):
                (root / case).mkdir()
                for size in ("small", "medium", "large"):
                    truth_path = root / case / f"{size}_truth.json"
                    truth = {"case": case, "size": size, "direction": "B->A", "H_gt": matrix}
                    truth_path.write_text(json.dumps(truth), encoding="utf-8")
            arguments = run_tests.synthetic_arguments(root)
            self.assertEqual(arguments.count("--synthetic-pair"), 6)
            self.assertEqual(arguments[1], "translation/small")
            self.assertEqual(arguments[-9:], [str(value) for value in matrix])
            truth["direction"] = "A->B"
            truth_path.write_text(json.dumps(truth), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Invalid synthetic truth"):
                run_tests.synthetic_arguments(root)


if __name__ == "__main__":
    unittest.main()
