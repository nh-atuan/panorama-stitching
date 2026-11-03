#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166), Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Run multi-version panorama benchmark: 3 sites x 3 sizes (docs/final-plan.md).

Supports V0 Sequential and GPU versions (V1 Basic CUDA, V2, V3 Optimized).
Reads both the 8-column V0 CSV schema and the 11-column CUDA CSV schema.

Output layout in --out:
    v<k>/<site>/<size>.csv            raw stdout of stitch
    v<k>/<site>/<size>.log            stderr of stitch ([debug] diagnostics)
    v<k>/<site>/<size>_panorama.jpg   panorama written by stitch
    v<k>/summary.csv                  stage timing and shares for version k
    v<k>/summary.md                   Markdown summary for version k
    speedup.csv                       speedup comparisons across versions
    speedup.md                        speedup Markdown table
    environment.json                  GPU, CPU, time, commands and binary SHA-256

Example:
    python scripts/run_benchmark.py --stitch build/stitch --dataset dataset --runs 5 --out results/benchmark --versions 0 1
"""

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from midterm_notebook import SITES, SIZES, sha256  # noqa: E402

BENCHMARK_SITES = SITES[:3]  # The challenge pair is for quality analysis only.
BASE_STAGE_COLUMNS = [f"S{i}_ms" for i in range(1, 7)]
CUDA_EXTRA_COLUMNS = ["H2D_ms", "D2H_ms", "Total_Kernel_ms"]
TIMING_COLUMNS = [*BASE_STAGE_COLUMNS, "Total_ms", *CUDA_EXTRA_COLUMNS]
PCT_COLUMNS = [col.replace("_ms", "_pct") for col in BASE_STAGE_COLUMNS]
SUMMARY_COLUMNS = [
    "version", "site", "size", "stat", *TIMING_COLUMNS, *PCT_COLUMNS,
    "other_pct", "hot_stage", "p_hot", "amdahl_limit"
]
SPEEDUP_COLUMNS = [
    "site", "size", "version", "Total_ms", "Total_Kernel_ms",
    "speedup_vs_v0", "speedup_vs_prev", "kernel_speedup_vs_v0"
]
DEBUG_PREFIXES = ("[debug] version=", "[debug] config: ", "[debug] GPU=")


class BenchmarkError(RuntimeError):
    """A configuration could not be benchmarked; the message says why."""


def positive_int(text):
    if not text.isdigit() or int(text) <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer: '{text}'")
    return int(text)


def parse_versions(raw_values):
    """Parse list of versions from strings, integers or comma-separated lists."""
    versions = []
    for item in raw_values:
        for part in str(item).split(","):
            part = part.strip()
            if part.lower().startswith("v"):
                part = part[1:]
            if not part.isdigit() or int(part) < 0:
                raise argparse.ArgumentTypeError(f"version must be a non-negative integer: '{part}'")
            val = int(part)
            if val not in versions:
                versions.append(val)
    return versions or [0]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run multi-version benchmark on 3 sites x 3 sizes.")
    parser.add_argument("--stitch", required=True, type=Path, help="stitch binary built with nvcc -arch=sm_75")
    parser.add_argument("--dataset", required=True, type=Path, help="dataset/ folder from prepare_dataset.py")
    parser.add_argument("--runs", default=5, type=positive_int, help="timed runs per configuration (default 5)")
    parser.add_argument("--out", required=True, type=Path, help="folder for CSV, logs, speedups and summaries")
    parser.add_argument("--versions", "--version", dest="versions", nargs="+", default=["0"],
                        help="versions to benchmark (e.g. 0 1, or 0,1; default 0)")
    parser.add_argument("--flat", action="store_true", help="use flat output layout for single version compatibility")
    return parser.parse_args(argv)


def configurations():
    return [(site, size) for site in BENCHMARK_SITES for size in SIZES]


def input_paths(dataset, site, size):
    folder = Path(dataset) / site
    return folder / f"{size}_left.jpg", folder / f"{size}_right.jpg"


def check_inputs(dataset):
    """Fail before any run if one of the 18 input images is missing."""
    missing = [str(path) for site, size in configurations()
               for path in input_paths(dataset, site, size) if not path.is_file()]
    if missing:
        raise BenchmarkError("Missing input images:\n  " + "\n  ".join(missing))


def build_command(stitch_cmd, left, right, panorama, runs, version=0):
    return [*map(str, stitch_cmd), str(left), str(right), str(panorama),
            "--version", str(version), "--runs", str(runs), "--debug"]


def run_config(stitch_cmd, dataset, out, site, size, runs, version=0, flat=False):
    """Run stitch for one configuration; save stdout and stderr verbatim."""
    left, right = input_paths(dataset, site, size)
    version_dir = Path(out) if flat else Path(out) / f"v{version}"
    folder = version_dir / site
    folder.mkdir(parents=True, exist_ok=True)
    command = build_command(stitch_cmd, left, right, folder / f"{size}_panorama.jpg", runs, version)
    result = subprocess.run(command, capture_output=True, text=True)
    csv_path, log_path = folder / f"{size}.csv", folder / f"{size}.log"
    csv_path.write_text(result.stdout, encoding="utf-8", newline="")
    log_path.write_text(result.stderr, encoding="utf-8", newline="")
    if result.returncode != 0:
        raise BenchmarkError(f"stitch failed on {site}/{size} (version {version}) with exit code {result.returncode}; "
                             f"see {log_path}")
    return command, result.stdout, result.stderr


def parse_version_csv(text, runs=5):
    """Validate numbered runs and the average/minimum rows for both V0 (8 cols) and CUDA (11 cols)."""
    if runs <= 0:
        raise ValueError("runs must be positive")
    reader = csv.reader(io.StringIO(text.strip()))
    rows = [row for row in reader if row]
    if not rows:
        raise ValueError("Empty CSV output")

    header = [col.strip() for col in rows[0]]
    expected_labels = [str(index) for index in range(1, runs + 1)] + ["Average", "Minimum"]
    if len(rows) != runs + 3 or [row[0] for row in rows[1:]] != expected_labels:
        raise ValueError("Missing, duplicated, or unordered timing rows")

    # Detect schema: V0 (8 columns) vs CUDA V1+ (11 columns)
    if len(header) == 8:
        if header[0] != "Run_Index" or header[1:7] != BASE_STAGE_COLUMNS or header[7] != "Total_ms":
            raise ValueError(f"Unexpected V0 CSV header: {header}")
        is_gpu = False
    elif len(header) == 11:
        if header[0] != "Run_Index" or header[7] != "Total_ms" or header[8:] != CUDA_EXTRA_COLUMNS:
            raise ValueError(f"Unexpected GPU CSV header: {header}")
        is_gpu = True
    else:
        raise ValueError(f"Unexpected timing column count: {len(header)}")

    measurements = []
    for row in rows[1:runs + 1]:
        numbers = [float(val) for val in row[1:]]
        if any(not math.isfinite(val) or val < 0 for val in numbers):
            raise ValueError("Non-finite or negative timing")
        item = {
            "S1_ms": numbers[0], "S2_ms": numbers[1], "S3_ms": numbers[2],
            "S4_ms": numbers[3], "S5_ms": numbers[4], "S6_ms": numbers[5],
            "Total_ms": numbers[6],
            "H2D_ms": numbers[7] if is_gpu else 0.0,
            "D2H_ms": numbers[8] if is_gpu else 0.0,
            "Total_Kernel_ms": numbers[9] if is_gpu else numbers[6],
        }
        measurements.append(item)

    avg_row = [float(val) for val in rows[runs + 1][1:]]
    min_row = [float(val) for val in rows[runs + 2][1:]]

    all_keys = [*BASE_STAGE_COLUMNS, "Total_ms"]
    if is_gpu:
        all_keys.extend(CUDA_EXTRA_COLUMNS)

    calculated_avg = {key: sum(m[key] for m in measurements) / runs for key in all_keys}
    calculated_min = {key: min(m[key] for m in measurements) for key in all_keys}
    if not is_gpu:
        calculated_avg.update(H2D_ms=0.0, D2H_ms=0.0, Total_Kernel_ms=calculated_avg["Total_ms"])
        calculated_min.update(H2D_ms=0.0, D2H_ms=0.0, Total_Kernel_ms=calculated_min["Total_ms"])

    for idx, key in enumerate(all_keys):
        if not math.isclose(avg_row[idx], calculated_avg[key], rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError(f"Reported average disagrees with measured runs for {key}")
        if not math.isclose(min_row[idx], calculated_min[key], rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError(f"Reported minimum disagrees with measured runs for {key}")

    return {
        "runs": measurements,
        "average": calculated_avg,
        "minimum": calculated_min,
        "is_gpu": is_gpu,
    }


def query_gpu():
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                                capture_output=True, text=True)
    except OSError:
        return "unavailable"
    lines = result.stdout.strip().splitlines()
    return lines[0].strip() if result.returncode == 0 and lines else "unavailable"


def query_cpu():
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(errors="replace").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unavailable"


def collect_environment(stitch_path, runs, versions, commands):
    return {
        "gpu": query_gpu(), "cpu": query_cpu(),
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs": runs, "versions": versions,
        "stitch_sha256": sha256(stitch_path) if Path(stitch_path).is_file() else "unavailable",
        "python": platform.python_version(), "commands": commands
    }


def read_debug_config(log_text):
    """Return the debug version/seed lines and Config lines printed by stitch --debug."""
    lines = [line.strip() for line in log_text.splitlines()]
    return [next((line for line in lines if line.startswith(prefix)), "") for prefix in DEBUG_PREFIXES]


def stage_percentages(row):
    """Share of each stage in Total_ms, in percent."""
    total = row["Total_ms"]
    if total <= 0:
        raise BenchmarkError("Total_ms must be positive to compute stage percentages")
    return [100.0 * row[column] / total for column in BASE_STAGE_COLUMNS]


def hot_stage(percentages):
    """Index of the largest share; a tie goes to the earlier stage."""
    return max(range(len(percentages)), key=lambda index: (percentages[index], -index))


def summary_rows(site, size, parsed, version=0):
    """One average row with percentages and Amdahl, one minimum row with times only."""
    average = {
        "version": f"V{version}", "site": site, "size": size, "stat": "average",
        **parsed["average"]
    }
    percentages = stage_percentages(parsed["average"])
    hot = hot_stage(percentages)
    p_hot = percentages[hot] / 100.0
    average.update(zip(PCT_COLUMNS, percentages))
    average.update(
        other_pct=max(0.0, 100.0 - sum(percentages)),
        hot_stage=f"S{hot + 1}",
        p_hot=p_hot,
        amdahl_limit=1.0 / max(1e-9, 1.0 - p_hot)
    )
    minimum = {
        "version": f"V{version}", "site": site, "size": size, "stat": "minimum",
        **parsed["minimum"]
    }
    return [average, minimum]


def format_value(value):
    return f"{value:.6f}" if isinstance(value, float) else str(value)


def write_summary_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_COLUMNS, restval="", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_value(value) for key, value in row.items() if key in SUMMARY_COLUMNS})


def markdown_table(header, body):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cells) + " |" for cells in body]
    return "\n".join(lines)


def write_summary_md(path, rows, environment, debug_configs, version=0):
    averages = [row for row in rows if row["stat"] == "average"]
    minima = [row for row in rows if row["stat"] == "minimum"]
    stages = [column[:-3] for column in BASE_STAGE_COLUMNS]

    has_gpu_transfers = any(row.get("H2D_ms", 0.0) > 0 for row in averages)
    extra_headers = ["H2D", "D2H", "Total_Kernel"] if has_gpu_transfers else []

    average_body = []
    for row in averages:
        cells = [
            row["site"], row["size"],
            *(f"{row[ms]:.3f} ({row[pct]:.1f}%)" for ms, pct in zip(BASE_STAGE_COLUMNS, PCT_COLUMNS)),
            f"{row['Total_ms']:.3f}"
        ]
        if has_gpu_transfers:
            cells.extend([f"{row['H2D_ms']:.3f}", f"{row['D2H_ms']:.3f}", f"{row['Total_Kernel_ms']:.3f}"])
        cells.extend([row["hot_stage"], f"{row['p_hot']:.3f}", f"{row['amdahl_limit']:.3f}"])
        average_body.append(cells)

    minimum_body = []
    for row in minima:
        cells = [row["site"], row["size"], *(f"{row[col]:.3f}" for col in BASE_STAGE_COLUMNS), f"{row['Total_ms']:.3f}"]
        if has_gpu_transfers:
            cells.extend([f"{row['H2D_ms']:.3f}", f"{row['D2H_ms']:.3f}", f"{row['Total_Kernel_ms']:.3f}"])
        minimum_body.append(cells)

    config_body = [[site, size, " | ".join(filter(None, debug_info))]
                   for (site, size), debug_info in debug_configs.items()]

    headers_avg = ["Site", "Size", *stages, "Total", *extra_headers, "Hot stage", "p", "1/(1-p)"]
    headers_min = ["Site", "Size", *stages, "Total", *extra_headers]

    text = "\n\n".join([
        f"# V{version} benchmark",
        f"GPU: {environment['gpu']}. CPU: {environment['cpu']}. Time (UTC): {environment['time_utc']}. "
        f"Runs per configuration: {environment['runs']}, after one untimed warm-up.",
        "## Average (ms, share of Total_ms)",
        markdown_table(headers_avg, average_body),
        "## Minimum (ms)",
        markdown_table(headers_min, minimum_body),
        "## Config diagnostics",
        markdown_table(["Site", "Size", "Diagnostics"], config_body),
    ])
    Path(path).write_text(text + "\n", encoding="utf-8", newline="")


def compute_speedups(all_averages, versions):
    """Calculate speedup vs V0 and vs previous version across sizes and sites."""
    rows = []
    sorted_v = sorted(versions)
    v0_data = all_averages.get(0, {})

    for idx, v in enumerate(sorted_v):
        prev_v = sorted_v[idx - 1] if idx > 0 else None
        prev_data = all_averages.get(prev_v, {}) if prev_v is not None else {}
        for site, size in configurations():
            curr = all_averages[v][(site, size)]
            total_ms = curr["Total_ms"]
            kernel_ms = curr.get("Total_Kernel_ms", total_ms)

            # speedup vs V0
            if v0_data and (site, size) in v0_data:
                v0_total = v0_data[(site, size)]["Total_ms"]
                speedup_v0 = v0_total / total_ms if total_ms > 0 else 0.0
                kernel_speedup_v0 = v0_total / kernel_ms if kernel_ms > 0 else 0.0
            else:
                speedup_v0 = 1.0 if v == 0 else 0.0
                kernel_speedup_v0 = 1.0 if v == 0 else 0.0

            # speedup vs previous version
            if prev_data and (site, size) in prev_data:
                prev_total = prev_data[(site, size)]["Total_ms"]
                speedup_prev = prev_total / total_ms if total_ms > 0 else 0.0
            else:
                speedup_prev = 1.0

            rows.append({
                "site": site, "size": size, "version": f"V{v}",
                "Total_ms": total_ms, "Total_Kernel_ms": kernel_ms,
                "speedup_vs_v0": speedup_v0, "speedup_vs_prev": speedup_prev,
                "kernel_speedup_vs_v0": kernel_speedup_v0
            })
    return rows


def write_speedup_csv(path, speedup_rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SPEEDUP_COLUMNS, restval="", lineterminator="\n")
        writer.writeheader()
        for row in speedup_rows:
            writer.writerow({key: format_value(value) for key, value in row.items()})


def write_speedup_md(path, speedup_rows):
    header = ["Site", "Size", "Version", "Total (ms)", "Kernel (ms)", "Speedup vs V0", "Speedup vs Prev"]
    body = [[
        row["site"], row["size"], row["version"],
        f"{row['Total_ms']:.3f}", f"{row['Total_Kernel_ms']:.3f}",
        f"{row['speedup_vs_v0']:.2f}x", f"{row['speedup_vs_prev']:.2f}x"
    ] for row in speedup_rows]
    text = "\n\n".join([
        "# Multi-Version Speedup Summary",
        markdown_table(header, body),
    ])
    Path(path).write_text(text + "\n", encoding="utf-8", newline="")


def run_benchmark(stitch_cmd, stitch_path, dataset, runs, out, versions=(0,), flat=False):
    """Run benchmark for all requested versions and generate summaries & speedups."""
    check_inputs(dataset)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    all_commands = []
    all_averages = {}
    last_version_rows = []

    print(f"Beginning benchmark for version(s): {list(versions)}", flush=True)
    env = collect_environment(stitch_path, runs, list(versions), all_commands)
    print(f"GPU: {env['gpu']}\nCPU: {env['cpu']}", flush=True)

    for v in versions:
        v_out = out if flat else out / f"v{v}"
        v_out.mkdir(parents=True, exist_ok=True)
        v_rows = []
        debug_configs = {}

        print(f"\n--- Benchmarking V{v} ---", flush=True)
        for site, size in configurations():
            print(f"[{site}/{size}] Running V{v} ({runs} runs) ...", flush=True)
            cmd, stdout, stderr = run_config(stitch_cmd, dataset, out, site, size, runs, version=v, flat=flat)
            all_commands.append(cmd)
            try:
                parsed = parse_version_csv(stdout, runs)
            except ValueError as error:
                raise BenchmarkError(f"Invalid CSV from {site}/{size} (version {v}): {error}") from error
            v_rows.extend(summary_rows(site, size, parsed, version=v))
            debug_configs[(site, size)] = read_debug_config(stderr)

        write_summary_csv(v_out / "summary.csv", v_rows)
        write_summary_md(v_out / "summary.md", v_rows, env, debug_configs, version=v)
        all_averages[v] = {(r["site"], r["size"]): r for r in v_rows if r["stat"] == "average"}
        last_version_rows = v_rows

    # Write root summary.csv / summary.md when V0 is included or in flat mode
    if 0 in all_averages and not flat:
        v0_csv = out / "v0" / "summary.csv"
        v0_md = out / "v0" / "summary.md"
        if v0_csv.is_file():
            shutil.copy2(v0_csv, out / "summary.csv")
        if v0_md.is_file():
            shutil.copy2(v0_md, out / "summary.md")
    elif flat and versions:
        write_summary_csv(out / "summary.csv", last_version_rows)
        write_summary_md(out / "summary.md", last_version_rows, env, debug_configs, version=versions[0])

    # If multiple versions, or if both V0 and another version exist, generate speedup tables
    if len(versions) > 1 or (not flat and 0 in all_averages and len(all_averages) > 1):
        speedup_rows = compute_speedups(all_averages, versions)
        write_speedup_csv(out / "speedup.csv", speedup_rows)
        write_speedup_md(out / "speedup.md", speedup_rows)
        print(f"Wrote speedup tables to {out / 'speedup.csv'} and {out / 'speedup.md'}")

    env["commands"] = all_commands
    (out / "environment.json").write_text(json.dumps(env, indent=2) + "\n", encoding="utf-8")
    print(f"Saved benchmark environment to {out / 'environment.json'}")
    return last_version_rows


def main(argv=None):
    args = parse_args(argv)
    if not args.stitch.is_file():
        print(f"error: stitch binary not found: {args.stitch}", file=sys.stderr)
        return 1
    versions = parse_versions(args.versions)
    try:
        run_benchmark(
            [args.stitch], args.stitch, args.dataset, args.runs, args.out,
            versions=versions, flat=args.flat
        )
    except BenchmarkError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
