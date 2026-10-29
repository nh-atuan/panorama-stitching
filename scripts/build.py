#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Cross-platform builder for the stitch binary and developer tools in tests/tools/."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
STB_SOURCE = "src/common/stb_impl.cpp"

TOOL_TARGETS = {
    "tool_export_gray": [
        "src/common/image_layout.cpp",
        "src/common/gaussian_kernel.cpp",
        "src/common/gaussian_blur.cpp",
        "src/v0/v0_preprocess.cpp",
        "tests/tools/tool_export_gray.cpp",
    ],
    "tool_export_keypoints": [
        "src/common/image_layout.cpp",
        "src/common/gaussian_kernel.cpp",
        "src/common/gaussian_blur.cpp",
        "src/common/fast_corner.cpp",
        "src/common/brief_pattern.cpp",
        "src/common/feature_support.cpp",
        "src/v0/v0_preprocess.cpp",
        "src/v0/v0_detect.cpp",
        "src/v0/v0_describe.cpp",
        "src/v0/v0_match.cpp",
        "src/v0/v0_homography.cpp",
        "tests/tools/tool_export_keypoints.cpp",
    ],
    "tool_pipeline_trace": [
        "src/common/image_layout.cpp",
        "src/common/gaussian_kernel.cpp",
        "src/common/gaussian_blur.cpp",
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
        "tests/tools/tool_pipeline_trace.cpp",
    ],
}


def discover_stitch_sources():
    """Return ordered relative paths of all translation units for stitch (excluding stb_impl.cpp)."""
    sources = ["src/main.cu"]
    src_dir = ROOT / "src"
    subdirs = [src_dir / "common"]
    version_dirs = sorted(
        (d for d in src_dir.iterdir() if d.is_dir() and re.match(r"^v\d+$", d.name)),
        key=lambda d: int(d.name[1:]),
    )
    subdirs.extend(version_dirs)
    for folder in subdirs:
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix in {".cpp", ".cu"}:
                rel = path.relative_to(ROOT).as_posix()
                if rel != STB_SOURCE:
                    sources.append(rel)
    return sources


def run(command, environment):
    print("+", " ".join(str(x) for x in command), flush=True)
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
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]}")
    return result.stdout


def compiler_flags(is_nvcc, is_clang, strict_warnings):
    if is_nvcc:
        host_flags = ["-ffp-contract=off", "-fno-tree-vectorize", "-fno-tree-slp-vectorize"]
        if strict_warnings:
            host_flags = ["-Wall", "-Wextra", "-Werror", *host_flags]
        return [
            "-arch=sm_75",
            "-std=c++11",
            "-O2",
            "--fmad=false",
            "-Xcompiler=" + ",".join(host_flags),
        ]
    flags = ["-std=c++11", "-O2", "-ffp-contract=off"]
    if strict_warnings:
        flags += ["-Wall", "-Wextra", "-Wpedantic", "-Werror"]
    flags += (
        ["-fno-vectorize", "-fno-slp-vectorize"]
        if is_clang
        else ["-fno-tree-vectorize", "-fno-tree-slp-vectorize"]
    )
    return flags


def format_sources_for_host_compiler(sources):
    extra_cu = [s for s in sources if s.endswith(".cu") and s != "src/main.cu"]
    if extra_cu:
        raise RuntimeError(
            f"CUDA kernel sources present ({', '.join(extra_cu)}); build requires nvcc -arch=sm_75"
        )
    formatted = []
    for src in sources:
        if src.endswith(".cu"):
            formatted += ["-x", "c++", src, "-x", "none"]
        else:
            formatted.append(src)
    return formatted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="nvcc", help="nvcc, g++, or clang++ path")
    parser.add_argument(
        "--target",
        choices=("stitch", "tools", "all"),
        default="stitch",
        help="what to build (default: stitch)",
    )
    parser.add_argument("--tool", choices=tuple(TOOL_TARGETS.keys()), action="append", help="build specific tool(s)")
    parser.add_argument("--out-dir", default="build", help="output directory (default: build)")
    parser.add_argument("--require-t4", action="store_true", help="verify Tesla T4 before official build")
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="print the standalone one-line nvcc command for stitch and exit",
    )
    args = parser.parse_args()

    stitch_sources = discover_stitch_sources()
    out_dir = Path(args.out_dir)

    if args.print_command:
        one_liner = [
            "nvcc",
            *compiler_flags(is_nvcc=True, is_clang=False, strict_warnings=False),
            "-Isrc",
            *stitch_sources,
            STB_SOURCE,
            "-o",
            (out_dir / "stitch").as_posix(),
        ]
        print(" ".join(one_liner))
        return 0

    located = shutil.which(args.compiler)
    compiler = Path(located or args.compiler).resolve()
    if not compiler.is_file():
        raise RuntimeError(f"Compiler not found: {args.compiler}")
    is_nvcc = compiler.stem.lower() == "nvcc"
    is_clang = "clang" in compiler.stem.lower()

    environment = dict(os.environ)
    environment["PATH"] = str(compiler.parent) + os.pathsep + environment.get("PATH", "")

    if args.require_t4:
        gpu = run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], environment)
        if not re.search(r"\bT4\b", gpu):
            raise RuntimeError("Official verification requires Tesla T4")
        if not is_nvcc:
            raise RuntimeError("Official verification requires nvcc -arch=sm_75")

    out_abs = out_dir if out_dir.is_absolute() else (ROOT / out_dir)
    out_abs.mkdir(parents=True, exist_ok=True)
    # Prefer relative ASCII path for compiler -o flags when inside Unicode workspace paths on Windows.
    out_arg = out_abs.relative_to(ROOT) if out_abs.resolve().is_relative_to(ROOT) else out_abs
    obj_ext = ".obj" if (is_nvcc and sys.platform == "win32") else ".o"
    bin_ext = ".exe" if sys.platform == "win32" else ""
    link_extra = ["-static"] if (not is_nvcc and sys.platform == "win32") else []

    stb_obj = (out_arg / f"stb_impl{obj_ext}").as_posix()
    run(
        [
            str(compiler),
            *compiler_flags(is_nvcc, is_clang, strict_warnings=False),
            "-Isrc",
            "-c",
            STB_SOURCE,
            "-o",
            stb_obj,
        ],
        environment,
    )

    strict_flags = compiler_flags(is_nvcc, is_clang, strict_warnings=True)
    build_stitch = args.target in {"stitch", "all"} and not args.tool
    selected_tools = args.tool or (list(TOOL_TARGETS.keys()) if args.target in {"tools", "all"} else [])

    if build_stitch:
        srcs = stitch_sources if is_nvcc else format_sources_for_host_compiler(stitch_sources)
        stitch_bin = (out_arg / f"stitch{bin_ext}").as_posix()
        run(
            [str(compiler), *strict_flags, *link_extra, "-Isrc", *srcs, stb_obj, "-o", stitch_bin],
            environment,
        )
        print(f"Built: {stitch_bin}", flush=True)

    for tool_name in selected_tools:
        tool_bin = (out_arg / f"{tool_name}{bin_ext}").as_posix()
        run(
            [
                str(compiler),
                *strict_flags,
                *link_extra,
                "-Isrc",
                *TOOL_TARGETS[tool_name],
                stb_obj,
                "-o",
                tool_bin,
            ],
            environment,
        )
        print(f"Built: {tool_bin}", flush=True)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
