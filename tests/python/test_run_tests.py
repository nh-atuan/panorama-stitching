#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166)
# External source: none

"""Tests for tests/run_tests.py; compile lines are only inspected, so no GPU or nvcc is needed."""

import contextlib
import io
from pathlib import Path
import sys
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
        for name in ("preprocess", "gpu_s6", "gpu_reference", "test_run_tests.py"):
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


if __name__ == "__main__":
    unittest.main()
