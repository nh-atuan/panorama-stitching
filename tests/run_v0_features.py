#!/usr/bin/env python3
# Authors: Le Thuong De (23120232)
# External source: none

"""Build isolated V0 feature suites with a local compiler or nvcc on Colab T4."""

import argparse
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MATH = ["src/homography_math.cpp", "src/homography_svd.cpp", "src/homography_dlt.cpp"]
ESTIMATOR = ["src/feature_config.cpp", "src/v0_match.cpp", *MATH,
             "src/homography_sampling.cpp", "src/homography_scoring.cpp", "src/v0_homography.cpp"]
SUITES = {
    "matching": ["src/feature_config.cpp", "src/v0_match.cpp", "tests/test_v0_match.cpp"],
    "dlt": [*MATH, "tests/test_homography_dlt.cpp"],
    "sampling": ["src/homography_sampling.cpp", "tests/test_homography_sampling.cpp"],
    "msac": ["src/homography_math.cpp", "src/homography_scoring.cpp", "tests/test_homography_scoring.cpp"],
    "homography": [*ESTIMATOR, "src/v0_warp_blend.cpp", "tests/test_v0_homography.cpp"],
    "allocation": [*ESTIMATOR, "tests/test_v0_feature_allocation.cpp"],
    "warp": ["src/v0_warp_blend.cpp", "tests/test_v0_warp_blend.cpp"],
}


def run(command, environment):
    result = subprocess.run(command, cwd=ROOT, env=environment, text=True,
                            encoding="utf-8", errors="replace", capture_output=True)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="nvcc", help="nvcc, g++, or clang++ path")
    parser.add_argument("--require-t4", action="store_true", help="verify Tesla T4 before official build")
    parser.add_argument("--sanitizers", action="store_true", help="local clang/g++ ASan+UBSan")
    parser.add_argument("--suite", choices=SUITES, action="append", help="run selected suites")
    args = parser.parse_args()
    located = shutil.which(args.compiler)
    compiler = Path(located or args.compiler).resolve()
    if not compiler.is_file():
        raise RuntimeError(f"Compiler not found: {args.compiler}")
    is_nvcc = compiler.stem.lower() == "nvcc"
    is_clang = "clang" in compiler.stem.lower()
    if args.sanitizers and is_nvcc:
        raise RuntimeError("Use a local host compiler for --sanitizers; official nvcc suites run separately")
    environment = dict(os.environ)
    # Only child-process DLL lookup changes; no persistent system PATH modification.
    environment["PATH"] = str(compiler.parent) + os.pathsep + environment.get("PATH", "")
    print("Validation: Colab T4 required" if args.require_t4 else "Validation: local, not official Colab T4")
    print(f"Host: {platform.platform()}, CPU: {platform.processor() or 'unknown'}", flush=True)
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        model = re.search(r"^model name\s*:\s*(.+)$", cpuinfo.read_text(), re.MULTILINE)
        if model:
            print(f"CPU model: {model.group(1)}", flush=True)
    if args.require_t4:
        gpu = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], environment)
        if not re.search(r"\bT4\b", gpu):
            raise RuntimeError("Official verification requires Tesla T4")
        if not is_nvcc:
            raise RuntimeError("Official verification requires nvcc -arch=sm_75")
    run([str(compiler), "--version"], environment)
    build = ROOT / "build" / "v0_feature_tests"
    build.mkdir(parents=True, exist_ok=True)
    total = 0
    for name in args.suite or SUITES:
        print(f"Build/run: {name}", flush=True)
        if is_nvcc:
            flags = ["-arch=sm_75", "-std=c++11", "-O2", "--fmad=false",
                     "-Xcompiler=-Wall,-Wextra,-Wpedantic,-Werror,-ffp-contract=off,-fno-tree-vectorize,-fno-tree-slp-vectorize"]
        else:
            flags = ["-std=c++11", "-O1" if args.sanitizers else "-O2", "-Wall", "-Wextra",
                     "-Wpedantic", "-Werror", "-ffp-contract=off"]
            flags += (["-fno-vectorize", "-fno-slp-vectorize"] if is_clang else
                      ["-fno-tree-vectorize", "-fno-tree-slp-vectorize"])
            if args.sanitizers:
                # Fault-injection suites own allocation operators that Windows ASan also owns.
                # Run all their assertions with UBSan; the integration suite covers S6 under ASan.
                sanitizer = "undefined" if name in {"allocation", "warp"} else "address,undefined"
                flags += ["-g", f"-fsanitize={sanitizer}", "-fno-sanitize-recover=all"]
                print(f"Sanitizers: {sanitizer}", flush=True)
            if sys.platform == "win32" and (not args.sanitizers or name in {"allocation", "warp"}):
                flags += ["-static"]
        suffix = ".exe" if sys.platform == "win32" else ""
        binary = build / (name + ("_sanitized" if args.sanitizers else "") + suffix)
        run([str(compiler), *flags, "-Isrc", *SUITES[name], "-o", str(binary)], environment)
        output = run([str(binary)], environment)
        match = re.search(r"^PASS(?: [^:\n]+)?: (\d+) (?:checks|assertions)", output, re.MULTILINE)
        if not match:
            raise RuntimeError(f"Suite {name} did not report a PASS count")
        total += int(match.group(1))
    print(f"PASS suites: {len(args.suite or SUITES)}, total checks: {total}")
    print("No benchmark timing or dataset panorama quality was measured.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
