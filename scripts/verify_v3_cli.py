#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none
"""Run production V3 CLI smoke checks on the official P7/P8 input pairs."""

import argparse
import csv
import io
from pathlib import Path
import re
import sys

from PIL import Image

from package_s6_verification import git_output
from profiling_common import BatchError, capture, inspect_environment, reject_stub, write_json
from run_benchmark import input_paths, parse_version_csv, read_debug_config, read_error_code, version_columns
from verify_v2_dataset import CANVAS, RGB_TOLERANCE, rgb_delta, stitch_command


RUNS = 2  # Exercise distinct Average and Minimum rows with more than one measured run.
VERSION_TRACE = re.compile(r"^\[debug\] GPU=.+ version=(\d+) seed=(\d+) runs=(\d+)$", re.MULTILINE)


def verify_csv(stdout, runs, version):
    rows = csv.reader(io.StringIO(stdout))
    header = next(rows, [])
    if len(header) != 11 or header != version_columns(version):
        raise ValueError(f"V{version} stdout header disagrees with the benchmark parser: {header}")
    return parse_version_csv(stdout, runs, version)


def check_panorama(stderr, output, left, version):
    trace = VERSION_TRACE.findall(stderr)
    if len(trace) != 1 or int(trace[0][0]) != version or int(trace[0][2]) != RUNS or reject_stub(stderr):
        raise ValueError(f"Expected production debug version={version} and runs={RUNS}, got {trace}")
    geometry = CANVAS.findall(stderr)
    if len(geometry) != 1:
        raise ValueError(f"V{version} must report one S6 canvas")
    width, height, ox, oy = map(int, geometry[0])
    with Image.open(left) as image:
        aw, ah = image.size
    if not (0 <= ox <= width - aw and 0 <= oy <= height - ah and (width > aw or height > ah)):
        raise ValueError(f"V{version} canvas {geometry[0]} does not expand and contain image A")
    with Image.open(output) as image:
        if image.format != "PNG" or image.mode != "RGB" or image.size != (width, height):
            raise ValueError(f"V{version} PNG does not match S6 canvas {geometry[0]}")
        image.load()
        if len(image.tobytes()) != width * height * 3:
            raise ValueError(f"V{version} PNG does not contain the complete RGB canvas")
    return (width, height, ox, oy), int(trace[0][1])


def check_failure(record, stdout, stderr, output, expected, stage=None):
    status = read_error_code(stderr)
    if record["returncode"] != 1 or status != expected or stdout.strip() or output.exists():
        raise ValueError(f"Expected {expected} with exit 1 and no CSV/PNG; "
                         f"got exit={record['returncode']} status={status}; see captured stderr")
    if stage and not any(line.startswith(f"Error: [{expected}]") and stage in line
                         for line in stderr.splitlines()):
        raise ValueError(f"Expected {expected} from {stage}; see captured stderr")


def smoke(stitch, dataset, out, require_t4=False):
    standard = input_paths(dataset, "site1", "small")
    challenge = input_paths(dataset, "challenge", "medium")
    missing = [str(path) for path in (*standard, *challenge) if not path.is_file()]
    if missing:
        raise ValueError("Missing required smoke inputs: " + ", ".join(missing))
    environment = inspect_environment(stitch, require_t4=require_t4)
    out.mkdir(parents=True, exist_ok=False)

    canvases, timings, configs = {}, {}, {}
    for version in (2, 3):
        output = out / f"site1-small-v{version}.png"
        record, stdout, stderr = capture(stitch_command(stitch, *standard, output, version, RUNS, True),
                                         out / f"site1-small-v{version}")
        if record["returncode"] != 0:
            raise ValueError(f"site1/small V{version}: exit={record['returncode']}, "
                             f"status={read_error_code(stderr)}; see captured stderr")
        timings[version] = verify_csv(stdout, RUNS, version)
        canvases[version] = check_panorama(stderr, output, standard[0], version)
        _, configs[version] = read_debug_config(stderr)
    if canvases[2] != canvases[3]:
        raise ValueError(f"site1/small canvas/offset or seed differs: {canvases}")
    if not configs[2] or configs[2] != configs[3]:
        raise ValueError(f"site1/small V2/V3 debug Config missing or different: {configs}")
    delta = rgb_delta(out / "site1-small-v2.png", out / "site1-small-v3.png")
    if delta > RGB_TOLERANCE:
        raise ValueError(f"site1/small V2/V3 Max RGB={delta}, expected <= {RGB_TOLERANCE}")

    failures = (
        ("challenge-medium-v2", challenge, 2, 1, "NumericalFailure", "S6 warp_blend"),
        ("challenge-medium-v3", challenge, 3, 1, "NumericalFailure", "S6 warp_blend"),
        ("missing-v3", (out / "missing.jpg", standard[1]), 3, 1, "InputNotFound", None),
        ("runs-zero-v3", standard, 3, 0, "InvalidArgument", None),
    )
    for label, inputs, version, runs, expected, stage in failures:
        output = out / f"{label}.png"
        record, stdout, stderr = capture(stitch_command(stitch, *inputs, output, version, runs), out / label)
        try:
            check_failure(record, stdout, stderr, output, expected, stage)
        except ValueError as error:
            raise ValueError(f"{label}: {error}") from error

    write_json(out / "summary.json", {
        "verification_checkout": git_output("rev-parse", "HEAD"),
        "source_status": git_output("status", "--porcelain", "--", "src", "scripts", "tests"),
        "environment": environment,
        "site1/small": {"status": "Success", "canvas": canvases[3][0], "seed": canvases[3][1],
                        "config": configs[3], "max_rgb": delta, "v3_header": version_columns(3), "timing": timings},
        "challenge/medium": {"V2": "NumericalFailure", "V3": "NumericalFailure",
                             "stage": "S6", "panorama_quality": "unavailable"},
        "negative_cli": {"missing": "InputNotFound", "runs_zero": "InvalidArgument"},
    })
    print(f"PASS V3 CLI: site1/small canvas={canvases[3][0]} Max RGB={delta}; "
          "challenge/medium expected S6 NumericalFailure; negative CLI checks passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stitch", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="new directory for captured evidence")
    parser.add_argument("--require-t4", action="store_true")
    args = parser.parse_args()
    smoke(args.stitch.resolve(), args.dataset.resolve(), args.out.resolve(), args.require_t4)


if __name__ == "__main__":
    try:
        main()
    except (BatchError, OSError, ValueError) as error:
        print(f"FAIL V3 CLI: {error}", file=sys.stderr)
        sys.exit(1)
