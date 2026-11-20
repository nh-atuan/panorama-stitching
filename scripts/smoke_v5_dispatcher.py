# Authors: Le Ha Thanh Chuong (23120195)
# External source: none
"""Local V4/V5 CLI smoke check. Full T4 acceptance belongs to P10-T04."""
import argparse
import csv
import math
from pathlib import Path
import re
import subprocess

from run_benchmark import parse_version_csv

DETAIL_COLUMNS = [
    "Run_Index", "Mode", "H2D_A_ms", "H2D_B_ms", "S1_A_ms", "S1_B_ms",
    "S2_A_ms", "S2_B_ms", "S3_A_ms", "S3_B_ms", "PreS4_ms", "Host_PreS4_ms",
    "CountWait_A_ms", "CountWait_B_ms",
]


def check_detail(text, mode, primary):
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames != DETAIL_COLUMNS:
        raise ValueError("Unexpected V5 sidecar header")
    rows = list(reader)
    if len(rows) != len(primary["runs"]):
        raise ValueError("Missing V5 sidecar runs")
    for index, (row, run) in enumerate(zip(rows, primary["runs"]), 1):
        if row["Run_Index"] != str(index) or row["Mode"] != mode:
            raise ValueError("Incorrect sidecar run or mode")
        values = {key: float(row[key]) for key in DETAIL_COLUMNS[2:]}
        if any(not math.isfinite(v) or v < 0 for v in values.values()):
            raise ValueError("Invalid sidecar timing")
        for metric in ("H2D", "S1", "S2", "S3"):
            combined = values[f"{metric}_A_ms"] + values[f"{metric}_B_ms"]
            if abs(combined - run[f"{metric}_ms"]) > 0.005:
                raise ValueError(f"Primary and sidecar disagree for {metric}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stitch", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    from PIL import Image, ImageChops
    executable = args.stitch.resolve()
    left, right = [args.dataset / "site1" / f"small_{side}.jpg" for side in ("left", "right")]
    if not left.is_file() or not right.is_file():
        raise FileNotFoundError("Official site1/small input pair is required")
    args.out.mkdir(parents=True, exist_ok=True)
    outputs = []
    diagnostics = []
    for version, mode in ((4, None), (5, "sequential"), (5, "dual")):
        label = mode or "v4"
        image = args.out / f"{label}.png"
        command = [str(executable), str(left), str(right), str(image),
                   "--version", str(version), "--runs", "2", "--debug"]
        detail = args.out / f"{label}_detail.csv"
        if mode:
            command += ["--v5-schedule", mode, "--v5-detail-csv", str(detail)]
        result = subprocess.run(command, capture_output=True, text=True)
        (args.out / f"{label}.stdout").write_text(result.stdout, encoding="utf-8")
        (args.out / f"{label}.stderr").write_text(result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"{label} failed: {result.stderr}")
        parsed = parse_version_csv(result.stdout, 2, version)
        if mode:
            check_detail(detail.read_text(), mode, parsed)
        with Image.open(image) as opened:
            outputs.append(opened.convert("RGB"))
        diagnostics.append(re.findall(r"\[debug\] (?:H\(B->A\)=|S6 canvas=).+", result.stderr))
    for i in (1, 2):
        if outputs[i].size != outputs[0].size:
            raise AssertionError("V5 canvas dimensions differ from V4")
        difference = ImageChops.difference(outputs[0], outputs[i])
        maximum = max(pair[1] for pair in difference.getextrema())
        if maximum > 1:
            raise AssertionError(f"RGB max difference {maximum} exceeds 1")
        if len(diagnostics[i]) != 2 or diagnostics[i] != diagnostics[0]:
            raise AssertionError("V5 H or canvas debug diagnostics differ from V4")
    print("PASS: repeated V5 runs, both schedules, primary/sidecar timing, H/canvas and RGB smoke parity")


if __name__ == "__main__":
    main()
