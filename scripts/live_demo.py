#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166)
# External source: none

"""One-command live demo of the panorama pipeline for the P12 video (P11-T03).

The demo prints the GPU, the toolkit and the source SHA, builds stitch when needed, then runs
the selected versions on one dataset pair (site2/small by default). Each version gets the CLI
warm-up and --runs timed runs. The script prints the average stage times, Total_ms and the
speedup against the first version, saves every panorama in --out, and finally runs the
challenge pair at medium size to show how the pipeline reports a failure.

Timings come only from the stitch CSV; Python measures nothing. The official benchmark is
run_benchmark.py; this script only shows the program running.

Example (from the repository root on a Colab T4 runtime):
    python scripts/live_demo.py --dataset dataset
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_benchmark import (  # noqa: E402
    BASE_STAGE_COLUMNS, CHALLENGE_SITE, input_paths, parse_version_csv, positive_int, query_gpu,
    read_error_code,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSIONS = (0, 4, 5)
VERSION_NAMES = {0: "V0 sequential CPU", 1: "V1 basic CUDA", 2: "V2 parallel RANSAC",
                 3: "V3 RANSAC scheduling", 4: "V4 canvas fusion", 5: "V5 two streams"}
STAGE_LABELS = ("S1 pre", "S2 det", "S3 desc", "S4 match", "S5 H", "S6 warp")


class DemoError(RuntimeError):
    """The demo cannot continue; the message says why."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Live demo: run a few versions on one image pair.")
    parser.add_argument("--dataset", default="dataset", help="dataset folder (default: dataset)")
    parser.add_argument("--site", default="site2", help="site of the demo pair (default: site2)")
    parser.add_argument("--size", default="small", choices=("small", "medium", "large"))
    parser.add_argument("--versions", type=int, nargs="+", default=list(DEFAULT_VERSIONS),
                        help="versions to run, first one is the speedup baseline (default: 0 4 5)")
    parser.add_argument("--runs", type=positive_int, default=3, help="timed runs per version (default: 3)")
    parser.add_argument("--stitch", default="build/stitch", help="stitch binary (default: build/stitch)")
    parser.add_argument("--out", default="results/demo", help="output folder (default: results/demo)")
    parser.add_argument("--skip-build", action="store_true", help="never build, fail if --stitch is missing")
    parser.add_argument("--skip-challenge", action="store_true", help="do not run the challenge pair")
    args = parser.parse_args(argv)
    unknown = [v for v in args.versions if v not in VERSION_NAMES]
    if unknown:
        parser.error(f"unknown versions: {unknown}")
    if len(set(args.versions)) != len(args.versions):
        parser.error("versions must not repeat")
    return args


def banner(title):
    print(f"\n=== {title} ===", flush=True)


def tool_line(command):
    """First non-empty output line of a tool, or 'unavailable'."""
    if shutil.which(command[0]) is None:
        return "unavailable"
    result = subprocess.run(command, capture_output=True, text=True)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[-1] if result.returncode == 0 and lines else "unavailable"


def environment_lines(repo_root=REPO_ROOT):
    sha = tool_line(["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"])
    return [f"GPU: {query_gpu()}", f"nvcc: {tool_line(['nvcc', '--version'])}", f"Source SHA: {sha}"]


def ensure_stitch(stitch, skip_build, repo_root=REPO_ROOT):
    """Return the stitch path, building it with scripts/build.py when it is missing."""
    stitch = Path(stitch)
    if not stitch.is_absolute():
        stitch = repo_root / stitch
    if stitch.is_file():
        print(f"Using {stitch}")
        return stitch
    if skip_build:
        raise DemoError(f"{stitch} does not exist and --skip-build was given")
    command = [sys.executable, "scripts/build.py", "--compiler", "nvcc", "--require-t4",
               "--out-dir", str(stitch.parent)]
    print("$ " + " ".join(command), flush=True)
    if subprocess.run(command, cwd=repo_root).returncode != 0 or not stitch.is_file():
        raise DemoError("build failed; see the output above")
    return stitch


def demo_command(stitch, left, right, panorama, version, runs):
    command = [str(stitch), str(left), str(right), str(panorama), "--version", str(version),
               "--runs", str(runs)]
    if version == 5:
        command += ["--v5-schedule", "dual"]
    return command


def run_version(stitch, left, right, out_dir, version, runs):
    """Run one version; return its average timings or the error of a failed run."""
    panorama = Path(out_dir) / f"v{version}_panorama.jpg"
    command = demo_command(stitch, left, right, panorama, version, runs)
    print("$ " + " ".join(command), flush=True)
    result = subprocess.run(command, capture_output=True, text=True)
    outcome = {"version": version, "exit_code": result.returncode, "panorama": panorama}
    if result.returncode != 0:
        outcome["error"] = read_error_code(result.stderr)
        outcome["stderr"] = result.stderr.strip()
        return outcome
    outcome["average"] = parse_version_csv(result.stdout, runs, version)["average"]
    return outcome


def timing_table(outcomes):
    """Text table: average stage times, Total_ms and speedup against the first version."""
    header = f"{'Version':22s}" + "".join(f"{label:>10s}" for label in STAGE_LABELS)
    header += f"{'Total':>11s}{'Speedup':>9s}"
    lines = [header, "-" * len(header)]
    baseline = next((o["average"]["Total_ms"] for o in outcomes[:1] if "average" in o), None)
    for outcome in outcomes:
        name = VERSION_NAMES[outcome["version"]]
        if "average" not in outcome:
            lines.append(f"{name:22s} failed: {outcome['error']} (exit {outcome['exit_code']})")
            continue
        average = outcome["average"]
        cells = "".join(f"{average[column]:10.2f}" for column in BASE_STAGE_COLUMNS)
        speedup = f"{baseline / average['Total_ms']:8.2f}x" if baseline else f"{'—':>9s}"
        lines.append(f"{name:22s}{cells}{average['Total_ms']:11.2f}{speedup}")
    lines.append("Times in ms, averaged over the timed runs after one warm-up. "
                 "V5 adds the S1-S3 intervals of both streams, so its stage sum can exceed Total.")
    return "\n".join(lines)


def error_lines(stderr, limit=3):
    lines = [line for line in stderr.splitlines() if line.strip()]
    return lines[-limit:]


def run_challenge(stitch, dataset, out_dir, version):
    """Run the challenge pair at medium size once and print how it ends."""
    left, right = input_paths(dataset, CHALLENGE_SITE, "medium")
    outcome = run_version(stitch, left, right, Path(out_dir) / "challenge", version, 1)
    if "average" in outcome:
        print(f"challenge/medium finished, Total {outcome['average']['Total_ms']:.2f} ms, "
              f"panorama {outcome['panorama']}")
    else:
        print(f"challenge/medium stopped with exit code {outcome['exit_code']}: {outcome['error']}")
        for line in error_lines(outcome["stderr"]):
            print("  " + line)
    return outcome


def check_pair(dataset, site, size):
    left, right = input_paths(dataset, site, size)
    missing = [str(path) for path in (left, right) if not path.is_file()]
    if missing:
        raise DemoError("missing input images: " + ", ".join(missing)
                        + " (prepare the dataset as in docs/dataset.md)")
    return left, right


def main(argv=None):
    args = parse_args(argv)
    try:
        banner("Environment")
        for line in environment_lines():
            print(line)
        stitch = ensure_stitch(args.stitch, args.skip_build)

        dataset = Path(args.dataset)
        left, right = check_pair(dataset, args.site, args.size)
        out_dir = Path(args.out) / f"{args.site}_{args.size}"
        out_dir.mkdir(parents=True, exist_ok=True)

        banner(f"Stitching {args.site}/{args.size}: {left.name} + {right.name}")
        outcomes = [run_version(stitch, left, right, out_dir, version, args.runs)
                    for version in args.versions]
        banner("Average timing")
        print(timing_table(outcomes))
        banner("Panoramas")
        for outcome in outcomes:
            state = "written" if outcome["panorama"].is_file() else "not written"
            print(f"{VERSION_NAMES[outcome['version']]}: {outcome['panorama']} ({state})")

        if not args.skip_challenge:
            banner("Challenge pair, medium size")
            check_pair(dataset, CHALLENGE_SITE, "medium")
            run_challenge(stitch, dataset, Path(args.out), args.versions[-1])
    except DemoError as error:
        print(f"Demo stopped: {error}", file=sys.stderr)
        return 1
    failed = [o for o in outcomes if "average" not in o]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
