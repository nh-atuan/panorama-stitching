#!/usr/bin/env python3
# Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Unified test runner for C++/CUDA suites (V0 and future GPU stages) and Python script tests."""

import argparse
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

COMMON_BLUR = [
    "src/common/image_layout.cpp",
    "src/common/gaussian_kernel.cpp",
    "src/common/gaussian_blur.cpp",
]
HOMOGRAPHY = [
    "src/common/feature_support.cpp",
    "src/v0/v0_homography.cpp",
]
ESTIMATOR = [
    *HOMOGRAPHY,
    "src/v0/v0_match.cpp",
]
V0_ALL_SOURCES = [
    *COMMON_BLUR,
    "src/common/fast_corner.cpp",
    "src/common/brief_pattern.cpp",
    "src/common/feature_support.cpp",
    "src/common/v0_config.cpp",
    "src/v0/v0_preprocess.cpp",
    "src/v0/v0_detect.cpp",
    "src/v0/v0_describe.cpp",
    "src/v0/v0_match.cpp",
    "src/v0/v0_homography.cpp",
    "src/v0/v0_warp_blend.cpp",
    "src/v0/v0_pipeline.cpp",
]

V0_SUITES = {
    "preprocess": [*COMMON_BLUR, "src/v0/v0_preprocess.cpp", "tests/v0/test_v0_preprocess.cpp"],
    "detect": [
        "src/common/image_layout.cpp",
        "src/common/fast_corner.cpp",
        "src/v0/v0_detect.cpp",
        "tests/v0/test_v0_detect.cpp",
    ],
    "describe": [
        *COMMON_BLUR,
        "src/common/brief_pattern.cpp",
        "src/v0/v0_describe.cpp",
        "tests/v0/test_v0_describe.cpp",
    ],
    "detect_describe": [
        *COMMON_BLUR,
        "src/common/fast_corner.cpp",
        "src/common/brief_pattern.cpp",
        *ESTIMATOR,
        "src/v0/v0_preprocess.cpp",
        "src/v0/v0_detect.cpp",
        "src/v0/v0_describe.cpp",
        "tests/v0/test_v0_detect_describe.cpp",
    ],
    "matching": ["src/common/feature_support.cpp", "src/v0/v0_match.cpp", "tests/v0/test_v0_match.cpp"],
    "dlt": [*HOMOGRAPHY, "tests/v0/test_homography_dlt.cpp"],
    "sampling": [*HOMOGRAPHY, "tests/v0/test_homography_sampling.cpp"],
    "msac": [*HOMOGRAPHY, "tests/v0/test_homography_scoring.cpp"],
    "homography": [*ESTIMATOR, "src/v0/v0_warp_blend.cpp", "tests/v0/test_v0_homography.cpp"],
    "allocation": [*ESTIMATOR, "tests/v0/test_v0_feature_allocation.cpp"],
    "warp": ["src/v0/v0_warp_blend.cpp", "tests/v0/test_v0_warp_blend.cpp"],
    "config": [
        "src/common/feature_support.cpp",
        "src/common/gaussian_kernel.cpp",
        "src/common/v0_config.cpp",
        "tests/v0/test_v0_config.cpp",
    ],
    "pipeline": [*V0_ALL_SOURCES, "tests/v0/test_v0_pipeline.cpp"],
}

# Suites defining custom global operator new/new[] for OOM fault injection;
# Windows ASan exports its own operator new and clashes at link time.
WINDOWS_CUSTOM_NEW_SUITES = {
    "preprocess",
    "detect",
    "describe",
    "detect_describe",
    "allocation",
    "warp",
    "config",
    "pipeline",
}

GPU_SUITES = {
    "gpu_s4": ["src/common/feature_support.cpp", "src/v0/v0_match.cpp", "src/v1/s4/v1_match.cu", "tests/gpu/test_gpu_s4_match.cu"],
    "gpu_s5": [*HOMOGRAPHY, "src/v1/s5/v1_homography.cu", "tests/gpu/test_gpu_s5_homography.cu"],
}

PYTHON_SUITES = [
    "test_dataset_scripts.py",
    "test_synthetic_scripts.py",
    "test_run_benchmark.py",
    "test_plot_benchmark.py",
    "test_midterm_notebook.py",
    "test_profiling_scripts.py",
]


def run(command, environment):
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(str(x) for x in command)}")
    return result.stdout + result.stderr


def run_v0_group(args, base_env):
    located = shutil.which(args.compiler)
    compiler = Path(located or args.compiler).resolve()
    if not compiler.is_file():
        raise RuntimeError(f"Compiler not found: {args.compiler}")
    is_nvcc = compiler.stem.lower() == "nvcc"
    is_clang = "clang" in compiler.stem.lower()
    if args.sanitizers and is_nvcc:
        raise RuntimeError("Use a local host compiler for --sanitizers; official nvcc suites run separately")

    environment = dict(base_env)
    # Only child-process DLL lookup changes; no persistent system PATH modification.
    environment["PATH"] = str(compiler.parent) + os.pathsep + environment.get("PATH", "")

    if args.require_t4:
        gpu = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], environment)
        if not re.search(r"\bT4\b", gpu):
            raise RuntimeError("Official verification requires Tesla T4")
        if not is_nvcc:
            raise RuntimeError("Official verification requires nvcc -arch=sm_75")

    run([str(compiler), "--version"], environment)

    if not args.suite:
        print("Check: brief_pattern generator", flush=True)
        run([sys.executable, "tests/tools/tool_gen_brief_pattern.py", "--check"], environment)

    build_rel = Path("build") / "tests_v0"
    (ROOT / build_rel).mkdir(parents=True, exist_ok=True)
    selected = [name for name in (args.suite or V0_SUITES) if name in V0_SUITES]
    total_checks = 0

    for name in selected:
        print(f"Build/run [v0]: {name}", flush=True)
        if is_nvcc:
            flags = [
                "-arch=sm_75",
                "-std=c++11",
                "-O2",
                "--fmad=false",
                "-Xcompiler=-Wall,-Wextra,-Wpedantic,-Werror,-ffp-contract=off,-fno-tree-vectorize,-fno-tree-slp-vectorize",
            ]
        else:
            flags = [
                "-std=c++11",
                "-O1" if args.sanitizers else "-O2",
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                "-Werror",
                "-ffp-contract=off",
            ]
            flags += (
                ["-fno-vectorize", "-fno-slp-vectorize"]
                if is_clang
                else ["-fno-tree-vectorize", "-fno-tree-slp-vectorize"]
            )
            if args.sanitizers:
                use_ubsan_only = sys.platform == "win32" and name in WINDOWS_CUSTOM_NEW_SUITES
                sanitizer = "undefined" if use_ubsan_only else "address,undefined"
                flags += ["-g", f"-fsanitize={sanitizer}", "-fno-sanitize-recover=all"]
                print(f"Sanitizers: {sanitizer}", flush=True)
            if sys.platform == "win32" and (not args.sanitizers or name in WINDOWS_CUSTOM_NEW_SUITES):
                flags += ["-static"]

        suffix = ".exe" if sys.platform == "win32" else ""
        binary_rel = build_rel / (name + ("_sanitized" if args.sanitizers else "") + suffix)
        binary_abs = ROOT / binary_rel
        run(
            [str(compiler), *flags, "-Isrc", "-Itests", *V0_SUITES[name], "-o", binary_rel.as_posix()],
            environment,
        )
        output = run([str(binary_abs)], environment)
        match = re.search(r"^PASS(?: [^:\n]+)?: (\d+) (?:checks|assertions)", output, re.MULTILINE)
        if not match:
            raise RuntimeError(f"Suite {name} did not report a PASS count")
        total_checks += int(match.group(1))

    print(f"PASS v0 suites: {len(selected)}, total checks: {total_checks}", flush=True)


def run_python_group(base_env):
    total_tests = 0
    for file_name in PYTHON_SUITES:
        print(f"Run [python]: {file_name}", flush=True)
        output = run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests/python", "-p", file_name],
            base_env,
        )
        count = re.search(r"Ran (\d+) tests?", output)
        if not count or not re.search(r"^OK\b", output, re.MULTILINE):
            raise RuntimeError(f"Python test suite failed: {file_name}")
        total_tests += int(count.group(1))
    print(f"PASS python suites: {len(PYTHON_SUITES)}, total tests: {total_tests}", flush=True)


def run_gpu_group(args, environment):
    compiler = shutil.which(args.compiler)
    if not compiler or Path(compiler).stem.lower() != "nvcc":
        raise RuntimeError("GPU suites require nvcc -arch=sm_75")
    if args.sanitizers:
        raise RuntimeError("Use compute-sanitizer for GPU suites")
    gpu = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], environment)
    if args.require_t4 and not re.search(r"\bT4\b", gpu):
        raise RuntimeError("Official verification requires Tesla T4")
    build = ROOT / "build/tests_gpu"
    build.mkdir(parents=True, exist_ok=True)
    selected = [name for name in (args.suite or GPU_SUITES) if name in GPU_SUITES]
    for name in selected:
        binary = build / name
        print(f"Build/run [gpu]: {name}", flush=True)
        run([compiler, "-arch=sm_75", "-std=c++11", "-O2", "--fmad=false",
             "-Xcompiler=-Wall,-Wextra,-Werror,-ffp-contract=off", "-Isrc", "-Itests",
             *GPU_SUITES[name], *(["-ldl"] if sys.platform != "win32" else []), "-o", str(binary)], environment)
        output = run([str(binary)], environment)
        if not re.search(r"^PASS GPU S[45]: \d+ checks", output, re.MULTILINE):
            raise RuntimeError(f"GPU suite {name} did not report PASS")
    print(f"PASS gpu suites: {len(selected)}", flush=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="nvcc", help="nvcc, g++, or clang++ path")
    parser.add_argument(
        "--group",
        choices=("all", "v0", "gpu", "python"),
        default="all",
        help="select test group to run (default: all)",
    )
    parser.add_argument("--suite", choices=tuple(V0_SUITES)+tuple(GPU_SUITES), action="append", help="run selected C++/CUDA suites")
    parser.add_argument("--require-t4", action="store_true", help="verify Tesla T4 before official build")
    parser.add_argument("--sanitizers", action="store_true", help="local clang/g++ ASan+UBSan")
    args = parser.parse_args()

    if args.suite and (args.group == "python" or (args.group == "v0" and any(n in GPU_SUITES for n in args.suite)) or (args.group == "gpu" and any(n in V0_SUITES for n in args.suite))):
        raise RuntimeError("Selected --suite does not belong to --group")

    print("Validation: Colab T4 required" if args.require_t4 else "Validation: local, not official Colab T4")
    print(f"Host: {platform.platform()}, CPU: {platform.processor() or 'unknown'}", flush=True)
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        model = re.search(r"^model name\s*:\s*(.+)$", cpuinfo.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
        if model:
            print(f"CPU model: {model.group(1)}", flush=True)

    base_env = dict(os.environ)
    base_env["PYTHONUTF8"] = "1"
    run_v0 = args.group in {"all", "v0"} and (not args.suite or any(n in V0_SUITES for n in args.suite))
    run_gpu = args.group in {"all", "gpu"} and (not args.suite or any(n in GPU_SUITES for n in args.suite))
    run_py = args.group in {"all", "python"} and not args.suite

    if run_v0:
        run_v0_group(args, base_env)
    if run_gpu:
        run_gpu_group(args, base_env)
    if run_py:
        run_python_group(base_env)

    print("No benchmark timing or dataset panorama quality was measured.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
