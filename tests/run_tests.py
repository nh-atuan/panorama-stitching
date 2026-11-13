#!/usr/bin/env python3
# Authors: Le Thuong De (23120232), Nguyen Ho Anh Tuan (23120185), Tran Huu Kim Thanh (23120166), Le Ha Thanh Chuong (23120195)
# External source: none

"""Unified test runner for C++/CUDA suites (V0 and future GPU stages) and Python script tests."""

import argparse
import json
import math
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

V1_ALL_SOURCES = [
    "src/v1/common/v1_gaussian_blur.cu",
    "src/v1/s1/v1_preprocess.cu",
    "src/v1/s2/v1_detect.cu",
    "src/v1/s3/v1_describe.cu",
    "src/v1/s4/v1_match.cu",
    "src/v1/s5/v1_homography.cu",
    "src/v1/v1_warp_blend.cu",
    "src/v1/v1_pipeline.cu",
]

V2_PIPELINE_SUITE = "gpu_v2_pipeline"
V2_PIPELINE_SOURCE = "src/v2/v2_pipeline.cu"
V2_PIPELINE_HEADER = "src/v2/v2_pipeline.h"
V3_PIPELINE_SUITE = "gpu_v3_pipeline"
V3_PIPELINE_SOURCE = "src/v3/v3_pipeline.cu"
V3_PIPELINE_HEADER = "src/v3/v3_pipeline.h"

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
    "reference_support": [*V0_ALL_SOURCES, "tests/v0/test_v0_reference_support.cpp"],
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
    "gpu_v2_s5": [*HOMOGRAPHY, "src/v1/s5/v1_homography.cu", "src/v2/s5/v2_homography.cu", "tests/gpu/test_gpu_v2_s5.cu"],
    "gpu_v3_s5": [
        *HOMOGRAPHY,
        "src/v1/s5/v1_homography.cu",
        "src/v2/s5/v2_homography.cu",
        "src/v3/s5/v3_homography.cu",
        "tests/gpu/test_gpu_v3_s5.cu",
    ],
    "gpu_s6": ["src/v0/v0_warp_blend.cpp", "src/v1/v1_warp_blend.cu", "tests/gpu/test_gpu_s6_warp_blend.cu"],
    "gpu_reference": [*V0_ALL_SOURCES, "tests/gpu/test_gpu_reference.cu"],
    "gpu_blur": [*COMMON_BLUR, "src/v1/common/v1_gaussian_blur.cu", "tests/gpu/test_gpu_gaussian_blur.cu"],
    "gpu_s1": [
        *COMMON_BLUR,
        "src/v0/v0_preprocess.cpp",
        "src/v1/common/v1_gaussian_blur.cu",
        "src/v1/s1/v1_preprocess.cu",
        "tests/gpu/test_gpu_s1_preprocess.cu",
    ],
    "gpu_s2": [
        *COMMON_BLUR,
        "src/common/fast_corner.cpp",
        "src/v0/v0_preprocess.cpp",
        "src/v0/v0_detect.cpp",
        "src/v1/common/v1_gaussian_blur.cu",
        "src/v1/s1/v1_preprocess.cu",
        "src/v1/s2/v1_detect.cu",
        "tests/gpu/test_gpu_s2_detect.cu",
    ],
    "gpu_s3": [
        *V0_ALL_SOURCES,
        "src/v1/common/v1_gaussian_blur.cu",
        "src/v1/s1/v1_preprocess.cu",
        "src/v1/s2/v1_detect.cu",
        "src/v1/s3/v1_describe.cu",
        "src/v1/s4/v1_match.cu",
        "tests/gpu/test_gpu_s3_describe.cu",
    ],
    "gpu_pipeline": [
        *V0_ALL_SOURCES,
        *V1_ALL_SOURCES,
        "tests/gpu/test_gpu_v1_pipeline.cu",
    ],
    V2_PIPELINE_SUITE: [
        *V0_ALL_SOURCES,
        *V1_ALL_SOURCES,
        "src/v2/s5/v2_homography.cu",
        "tests/gpu/test_gpu_v2_pipeline.cu",
    ],
    V3_PIPELINE_SUITE: [
        *V0_ALL_SOURCES,
        *V1_ALL_SOURCES,
        V2_PIPELINE_SOURCE,
        "src/v2/s5/v2_homography.cu",
        "tests/gpu/test_gpu_v3_pipeline.cu",
    ],
}
# Link options a suite needs in addition to its sources.
GPU_LINK_FLAGS = {"gpu_s6": ["-Xlinker=--wrap=cudaMalloc"]}
# Suites decoding images with stb; stb_impl.cpp is built once, without the strict warnings.
GPU_STB_SUITES = {"gpu_s6", "gpu_reference", "gpu_s1", "gpu_s2", "gpu_s3", "gpu_pipeline",
                  V2_PIPELINE_SUITE, V3_PIPELINE_SUITE}
STB_SOURCE = "src/common/stb_impl.cpp"

GPU_COMPILE_FLAGS = [
    "-arch=sm_75",
    "-std=c++11",
    "-O2",
    "--fmad=false",
]
GPU_HOST_FLAGS = "-ffp-contract=off,-fno-tree-vectorize,-fno-tree-slp-vectorize"

PASS_PATTERN = re.compile(r"^PASS(?: [^:\n]+)?: (\d+) (?:checks|assertions)", re.MULTILINE)

PYTHON_SUITES = [
    "test_dataset_scripts.py",
    "test_synthetic_scripts.py",
    "test_run_benchmark.py",
    "test_plot_benchmark.py",
    "test_midterm_notebook.py",
    "test_profiling_scripts.py",
    "test_run_tests.py",
    "test_v1_cli.py",
    "test_verify_v2_dataset.py",
    "test_verify_v3_cli.py",
]


def parse_pass_count(output):
    """Return the check count of a suite's PASS line, or None if the suite reported no PASS."""
    match = PASS_PATTERN.search(output)
    return int(match.group(1)) if match else None


def is_nvcc(compiler_name):
    located = shutil.which(compiler_name)
    return Path(located or compiler_name).stem.lower() == "nvcc"


def gpu_stb_command(compiler, stb_object):
    return [compiler, *GPU_COMPILE_FLAGS, f"-Xcompiler={GPU_HOST_FLAGS}", "-Isrc", "-c", STB_SOURCE,
            "-o", str(stb_object)]


def v3_pipeline_available():
    return all((ROOT / path).is_file() for path in (V3_PIPELINE_SOURCE, V3_PIPELINE_HEADER))


def gpu_suite_command(compiler, name, binary, stb_object, platform_name=sys.platform):
    """Compile line of one GPU suite; V0 sources get the same host flags as the official build."""
    pipeline = []
    if name == V2_PIPELINE_SUITE and all((ROOT / path).is_file() for path in (V2_PIPELINE_SOURCE, V2_PIPELINE_HEADER)):
        pipeline = ["-DV2_PIPELINE_AVAILABLE", V2_PIPELINE_SOURCE]
    if name == V3_PIPELINE_SUITE:
        if not v3_pipeline_available():
            raise RuntimeError("Production V3 pipeline source and header are required (P8-T02)")
        sources = sorted((ROOT / "src/v3").rglob("*"))
        pipeline = ["-DV3_PIPELINE_AVAILABLE", *(path.relative_to(ROOT).as_posix() for path in sources
                                                if path.is_file() and path.suffix in {".cu", ".cpp"})]
    return [
        compiler,
        *GPU_COMPILE_FLAGS,
        f"-Xcompiler=-Wall,-Wextra,-Werror,{GPU_HOST_FLAGS}",
        "-Isrc",
        "-Itests",
        *pipeline,
        *GPU_SUITES[name],
        *([str(stb_object)] if name in GPU_STB_SUITES else []),
        *GPU_LINK_FLAGS.get(name, []),
        *(["-ldl"] if platform_name != "win32" else []),
        "-o",
        str(binary),
    ]


def list_suites():
    lines = ["v0:", *(f"  {name}" for name in V0_SUITES), "gpu:", *(f"  {name}" for name in GPU_SUITES),
             "python:", *(f"  {name}" for name in PYTHON_SUITES)]
    return "\n".join(lines)


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
        count = parse_pass_count(output)
        if count is None:
            raise RuntimeError(f"Suite {name} did not report a PASS count")
        total_checks += count

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


def synthetic_arguments(folder):
    """Pass the existing generator's six B->A matrices to the C++ integration test."""
    arguments = []
    for case in ("translation", "projective"):
        for size in ("small", "medium", "large"):
            prefix = folder.resolve() / case / size
            truth_path = prefix.with_name(f"{size}_truth.json")
            try:
                truth = json.loads(truth_path.read_text(encoding="utf-8"))
                matrix = truth["H_gt"]
                if (truth["direction"] != "B->A" or truth["case"] != case or truth["size"] != size or
                        not isinstance(matrix, list) or len(matrix) != 9 or
                        not all(type(value) in (float, int) and math.isfinite(value) for value in matrix)):
                    raise ValueError("expected nine finite coefficients for this B->A fixture")
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise RuntimeError(f"Invalid synthetic truth {truth_path}: {error}") from error
            arguments.extend(["--synthetic-pair", f"{case}/{size}", str(prefix.with_name(f"{size}_left.png")),
                              str(prefix.with_name(f"{size}_right.png")), *(str(value) for value in matrix)])
    return arguments


def run_gpu_group(args, environment):
    selected = [name for name in (args.suite or GPU_SUITES) if name in GPU_SUITES]
    if V3_PIPELINE_SUITE in selected and not v3_pipeline_available():
        missing = "Production V3 pipeline source and header are required (P8-T02)"
        if args.suite or args.v3_dataset_dir:
            raise RuntimeError(missing)
        print(f"SKIP {V3_PIPELINE_SUITE}: {missing}", flush=True)
        selected.remove(V3_PIPELINE_SUITE)
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
    v2_arguments = []
    if V2_PIPELINE_SUITE in selected:
        if args.require_v2_pipeline:
            v2_arguments.append("--require-v2-pipeline")
        if args.v2_dataset_dir:
            v2_arguments.extend(["--dataset", str(args.v2_dataset_dir.resolve())])
        if args.v2_synthetic_dir:
            v2_arguments.extend(synthetic_arguments(args.v2_synthetic_dir))
    v3_arguments = []
    if V3_PIPELINE_SUITE in selected and args.v3_dataset_dir:
        v3_arguments = ["--require-v3-pipeline", "--dataset", str(args.v3_dataset_dir.resolve()),
                        *synthetic_arguments(args.v3_synthetic_dir)]
    suite_arguments = {V2_PIPELINE_SUITE: v2_arguments, V3_PIPELINE_SUITE: v3_arguments}
    stb_object = build / "stb_impl.o"
    if GPU_STB_SUITES.intersection(selected):
        run(gpu_stb_command(compiler, stb_object), environment)
    total_checks = 0
    for name in selected:
        binary = build / name
        print(f"Build/run [gpu]: {name}", flush=True)
        command = gpu_suite_command(compiler, name, binary, stb_object)
        if name == V2_PIPELINE_SUITE and args.require_v2_pipeline and "-DV2_PIPELINE_AVAILABLE" not in command:
            raise RuntimeError("Production V2 pipeline source and header are required")
        run(command, environment)
        output = run([str(binary), *suite_arguments.get(name, [])], environment)
        count = parse_pass_count(output)
        if count is None:
            raise RuntimeError(f"GPU suite {name} did not report a PASS count")
        total_checks += count
    print(f"PASS gpu suites: {len(selected)}, total checks: {total_checks}", flush=True)


def main(argv=None):
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
    parser.add_argument("--require-v2-pipeline", action="store_true", help="reject the test-only V2 dispatcher")
    parser.add_argument("--v2-synthetic-dir", type=Path, help="six translation/projective pairs from make_synthetic_pair.py")
    parser.add_argument("--v2-dataset-dir", type=Path, help="official 4-pair dataset at all 3 resolutions")
    parser.add_argument("--v3-synthetic-dir", type=Path, help="six P7 translation/projective fixtures for V3")
    parser.add_argument("--v3-dataset-dir", type=Path, help="official 4-pair dataset for V3 at all 3 resolutions")
    parser.add_argument("--sanitizers", action="store_true", help="local clang/g++ ASan+UBSan")
    parser.add_argument("--list", action="store_true", help="list the available suites and exit")
    args = parser.parse_args(argv)

    if args.list:
        print(list_suites())
        return

    if args.suite and (args.group == "python" or (args.group == "v0" and any(n in GPU_SUITES for n in args.suite)) or (args.group == "gpu" and any(n in V0_SUITES for n in args.suite))):
        raise RuntimeError("Selected --suite does not belong to --group")
    if args.require_v2_pipeline or args.v2_synthetic_dir or args.v2_dataset_dir:
        if (args.group not in {"all", "gpu"} or (args.suite and V2_PIPELINE_SUITE not in args.suite) or
                not is_nvcc(args.compiler)):
            parser.error("V2 options require the gpu_v2_pipeline suite and nvcc")
    if args.v3_synthetic_dir or args.v3_dataset_dir:
        if not args.v3_synthetic_dir or not args.v3_dataset_dir:
            parser.error("V3 acceptance requires both --v3-synthetic-dir and --v3-dataset-dir")
        if (args.group not in {"all", "gpu"} or (args.suite and V3_PIPELINE_SUITE not in args.suite) or
                not is_nvcc(args.compiler)):
            parser.error("V3 options require the gpu_v3_pipeline suite and nvcc")

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
    if run_gpu and args.group == "all" and not args.suite and not is_nvcc(args.compiler):
        # An explicit --group gpu or --suite gpu_* still fails without nvcc.
        print(f"Skip gpu suites: they need nvcc, got {args.compiler}. GPU code was not tested.", flush=True)
    elif run_gpu:
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
