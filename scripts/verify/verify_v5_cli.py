#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# Adapted from: scripts/verify_v4_cli.py by Nguyen Ho Anh Tuan (23120185)
# Changes: Adapted to verify V5 dual-stream and sequential production CLI, sidecar CSV, and compare against V4 baseline.
"""Run production V5 CLI smoke checks on the official input pairs."""

import argparse
import csv
import io
from pathlib import Path
import re
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notebook.package_s6_verification import git_output  # noqa: E402
from profiling.profiling_common import BatchError, capture, inspect_environment, reject_stub, write_json  # noqa: E402
from run_benchmark import input_paths, parse_version_csv, read_debug_config, read_error_code, version_columns  # noqa: E402
from verify.verify_v2_dataset import CANVAS, RGB_TOLERANCE, rgb_delta, stitch_command  # noqa: E402


RUNS = 2  # Exercise distinct Average and Minimum rows with more than one measured run.
VERSION_TRACE = re.compile(r"^\[debug\] GPU=.+ version=(\d+) seed=(\d+) runs=(\d+)$", re.MULTILINE)
SIDECAR_HEADER = [
    "Run_Index", "Mode", "H2D_A_ms", "H2D_B_ms", "S1_A_ms", "S1_B_ms", "S2_A_ms", "S2_B_ms",
    "S3_A_ms", "S3_B_ms", "PreS4_ms", "Host_PreS4_ms", "CountWait_A_ms", "CountWait_B_ms"
]


def verify_csv(stdout, runs, version):
    rows = csv.reader(io.StringIO(stdout))
    header = next(rows, [])
    if len(header) != 11 or header != version_columns(version):
        raise ValueError(f"V{version} stdout header disagrees with the benchmark parser: {header}")
    return parse_version_csv(stdout, runs, version)


def verify_sidecar(path, runs, expected_mode):
    if not path.is_file():
        raise ValueError(f"Missing expected V5 sidecar CSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.reader(handle) if row]
    if not rows or rows[0] != SIDECAR_HEADER:
        raise ValueError(f"V5 sidecar header mismatch: {rows[0] if rows else 'empty'}")
    if len(rows) != runs + 1:
        raise ValueError(f"Expected {runs} run rows + 1 header in sidecar, got {len(rows)}")
    for index, row in enumerate(rows[1:], 1):
        if len(row) != len(SIDECAR_HEADER):
            raise ValueError(f"Sidecar row {index} column count mismatch: {len(row)}")
        if row[0] != str(index) or row[1] != expected_mode:
            raise ValueError(f"Sidecar row {index} metadata mismatch: {row[:2]}")
        for col_idx in range(2, len(row)):
            val = float(row[col_idx])
            if val < 0 or not (val == val):  # Non-negative and not NaN
                raise ValueError(f"Sidecar row {index} col {SIDECAR_HEADER[col_idx]} invalid: {val}")


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

    # 1. Run V4 reference
    out_v4 = out / "site1-small-v4.png"
    rec_v4, out_v4_text, err_v4 = capture(stitch_command(stitch, *standard, out_v4, 4, RUNS, True),
                                          out / "site1-small-v4")
    if rec_v4["returncode"] != 0:
        raise ValueError(f"site1/small V4: exit={rec_v4['returncode']}, status={read_error_code(err_v4)}")
    verify_csv(out_v4_text, RUNS, 4)
    canvas_v4, seed_v4 = check_panorama(err_v4, out_v4, standard[0], 4)

    # 2. Run V5 Sequential
    out_v5_seq = out / "site1-small-v5-seq.png"
    sidecar_seq = out / "site1-small-v5-seq-detail.csv"
    cmd_v5_seq = [
        str(stitch), str(standard[0]), str(standard[1]), str(out_v5_seq),
        "--version", "5", "--runs", str(RUNS), "--v5-schedule", "sequential",
        "--v5-detail-csv", str(sidecar_seq), "--debug"
    ]
    rec_seq, out_seq_text, err_seq = capture(cmd_v5_seq, out / "site1-small-v5-seq")
    if rec_seq["returncode"] != 0:
        raise ValueError(f"site1/small V5 sequential: exit={rec_seq['returncode']}, status={read_error_code(err_seq)}")
    verify_csv(out_seq_text, RUNS, 5)
    verify_sidecar(sidecar_seq, RUNS, "sequential")
    canvas_seq, seed_seq = check_panorama(err_seq, out_v5_seq, standard[0], 5)

    # 3. Run V5 DualStream
    out_v5_dual = out / "site1-small-v5-dual.png"
    sidecar_dual = out / "site1-small-v5-dual-detail.csv"
    cmd_v5_dual = [
        str(stitch), str(standard[0]), str(standard[1]), str(out_v5_dual),
        "--version", "5", "--runs", str(RUNS), "--v5-schedule", "dual",
        "--v5-detail-csv", str(sidecar_dual), "--debug"
    ]
    rec_dual, out_dual_text, err_dual = capture(cmd_v5_dual, out / "site1-small-v5-dual")
    if rec_dual["returncode"] != 0:
        raise ValueError(f"site1/small V5 dual: exit={rec_dual['returncode']}, status={read_error_code(err_dual)}")
    verify_csv(out_dual_text, RUNS, 5)
    verify_sidecar(sidecar_dual, RUNS, "dual")
    canvas_dual, seed_dual = check_panorama(err_dual, out_v5_dual, standard[0], 5)

    # Check parity across V4, V5-seq, and V5-dual
    if canvas_v4 != canvas_seq or canvas_seq != canvas_dual:
        raise ValueError(f"Canvas geometry mismatch: V4={canvas_v4}, V5_seq={canvas_seq}, V5_dual={canvas_dual}")
    if seed_v4 != seed_seq or seed_seq != seed_dual:
        raise ValueError(f"Seed mismatch: V4={seed_v4}, V5_seq={seed_seq}, V5_dual={seed_dual}")

    delta_v4_dual = rgb_delta(out_v4, out_v5_dual)
    if delta_v4_dual > RGB_TOLERANCE:
        raise ValueError(f"V4 vs V5-dual Max RGB={delta_v4_dual}, expected <= {RGB_TOLERANCE}")

    delta_seq_dual = rgb_delta(out_v5_seq, out_v5_dual)
    if delta_seq_dual != 0:
        raise ValueError(f"V5-seq vs V5-dual Max RGB={delta_seq_dual}, expected exact 0 bit-for-bit")

    # 4. Error injections
    failures = (
        ("challenge-medium-v5-seq", challenge, "sequential", "NumericalFailure", "S6 warp_blend"),
        ("challenge-medium-v5-dual", challenge, "dual", "NumericalFailure", "S6 warp_blend"),
        ("missing-v5", (out / "missing.jpg", standard[1]), "dual", "InputNotFound", None),
        ("runs-zero-v5", standard, "dual", "InvalidArgument", None),
    )
    for label, inputs, mode, expected, stage in failures:
        output = out / f"{label}.png"
        runs_arg = 0 if label.startswith("runs-zero") else 1
        cmd = [str(stitch), str(inputs[0]), str(inputs[1]), str(output),
               "--version", "5", "--runs", str(runs_arg), "--v5-schedule", mode]
        rec, sout, serr = capture(cmd, out / label)
        check_failure(rec, sout, serr, output, expected, stage)

    print("PASS V5 CLI smoke verification")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stitch", type=Path, default=Path("build/stitch"), help="path to stitch binary")
    parser.add_argument("--dataset", type=Path, default=Path("dataset"), help="path to official dataset")
    parser.add_argument("--out", type=Path, required=True, help="output directory for smoke artifacts")
    parser.add_argument("--require-t4", action="store_true", help="require Tesla T4 GPU")
    args = parser.parse_args()
    smoke(args.stitch, args.dataset, args.out, require_t4=args.require_t4)


if __name__ == "__main__":
    main()
