#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166)
# External source: none

"""Run the official V0 benchmark: 3 sites x 3 sizes (docs/archive/midterm-plan.md, section 12).

Each configuration calls stitch once with --runs N. stitch does its own untimed warm-up
and prints one CSV block (N runs, Average, Minimum); this script never times anything
in Python. --debug only writes to stderr before the warm-up and after the timed runs,
so it does not change the timing; the log keeps the seed and the Config of every run.

Output layout in --out (the handoff layout of docs/notebook-guide.md):
    <site>/<size>.csv            raw stdout of stitch
    <site>/<size>.log            stderr of stitch ([debug] diagnostics)
    <site>/<size>_panorama.jpg   panorama written by stitch
    summary.csv                  average and minimum of every configuration, stage
                                 percentages, hot stage and the Amdahl limit 1/(1-p)
    summary.md                   the same tables in Markdown, with GPU, CPU and Config
    environment.json             GPU, CPU, time, commands and stitch SHA-256

Do not run any other heavy cell in the same Colab session while this script runs
(docs/archive/midterm-plan.md, section 12.6).

Example:
    python scripts/run_benchmark.py --stitch build/stitch --dataset dataset --runs 5 --out results/benchmark
"""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from midterm_notebook import SITES, SIZES, TIMING_COLUMNS, parse_stitch_csv, sha256  # noqa: E402

BENCHMARK_SITES = SITES[:3]  # The challenge pair is for quality analysis only (section 12.4).
STAGE_COLUMNS = TIMING_COLUMNS[:6]
PCT_COLUMNS = [column.replace("_ms", "_pct") for column in STAGE_COLUMNS]
SUMMARY_COLUMNS = (["site", "size", "stat", *TIMING_COLUMNS, *PCT_COLUMNS,
                    "other_pct", "hot_stage", "p_hot", "amdahl_limit"])
DEBUG_PREFIXES = ("[debug] version=", "[debug] config: ")


class BenchmarkError(RuntimeError):
    """A configuration could not be benchmarked; the message says why."""


def positive_int(text):
    if not text.isdigit() or int(text) <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer: '{text}'")
    return int(text)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the V0 benchmark on 3 sites x 3 sizes.")
    parser.add_argument("--stitch", required=True, type=Path, help="stitch binary built with nvcc -arch=sm_75")
    parser.add_argument("--dataset", required=True, type=Path, help="dataset/ folder from prepare_dataset.py")
    parser.add_argument("--runs", default=5, type=positive_int, help="timed runs per configuration (default 5)")
    parser.add_argument("--out", required=True, type=Path, help="folder for CSV, logs and summaries")
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


def build_command(stitch_cmd, left, right, panorama, runs):
    return [*map(str, stitch_cmd), str(left), str(right), str(panorama),
            "--version", "0", "--runs", str(runs), "--debug"]


def run_config(stitch_cmd, dataset, out, site, size, runs):
    """Run stitch for one configuration; save stdout and stderr verbatim."""
    left, right = input_paths(dataset, site, size)
    folder = Path(out) / site
    folder.mkdir(parents=True, exist_ok=True)
    command = build_command(stitch_cmd, left, right, folder / f"{size}_panorama.jpg", runs)
    result = subprocess.run(command, capture_output=True, text=True)
    csv_path, log_path = folder / f"{size}.csv", folder / f"{size}.log"
    csv_path.write_text(result.stdout, encoding="utf-8", newline="")
    log_path.write_text(result.stderr, encoding="utf-8", newline="")
    if result.returncode != 0:
        raise BenchmarkError(f"stitch failed on {site}/{size} with exit code {result.returncode}; "
                             f"see {log_path}")
    return command, result.stdout, result.stderr


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


def collect_environment(stitch_path, runs, commands):
    return {"gpu": query_gpu(), "cpu": query_cpu(),
            "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "runs": runs, "stitch_sha256": sha256(stitch_path),
            "python": platform.python_version(), "commands": commands}


def read_debug_config(log_text):
    """Return the version/seed line and the Config line printed by stitch --debug."""
    lines = [line.strip() for line in log_text.splitlines()]
    return [next((line for line in lines if line.startswith(prefix)), "") for prefix in DEBUG_PREFIXES]


def stage_percentages(row):
    """Share of each stage in the end-to-end time Total_ms, in percent."""
    total = row["Total_ms"]
    if total <= 0:
        raise BenchmarkError("Total_ms must be positive to compute stage percentages")
    return [100.0 * row[column] / total for column in STAGE_COLUMNS]


def hot_stage(percentages):
    """Index of the largest share; a tie goes to the earlier stage."""
    return max(range(len(percentages)), key=lambda index: (percentages[index], -index))


def summary_rows(site, size, parsed):
    """One average row with percentages and Amdahl, one minimum row with times only.

    Minimum takes each column from a possibly different run, so it gets no percentages.
    """
    average = {"site": site, "size": size, "stat": "average", **parsed["average"]}
    percentages = stage_percentages(parsed["average"])
    hot = hot_stage(percentages)
    p_hot = percentages[hot] / 100.0
    average.update(zip(PCT_COLUMNS, percentages))
    average.update(other_pct=100.0 - sum(percentages), hot_stage=f"S{hot + 1}",
                   p_hot=p_hot, amdahl_limit=1.0 / (1.0 - p_hot))
    minimum = {"site": site, "size": size, "stat": "minimum", **parsed["minimum"]}
    return [average, minimum]


def format_value(value):
    return f"{value:.6f}" if isinstance(value, float) else str(value)


def write_summary_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_COLUMNS, restval="", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_value(value) for key, value in row.items()})


def markdown_table(header, body):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cells) + " |" for cells in body]
    return "\n".join(lines)


def write_summary_md(path, rows, environment, debug_configs):
    averages = [row for row in rows if row["stat"] == "average"]
    minima = [row for row in rows if row["stat"] == "minimum"]
    stages = [column[:-3] for column in STAGE_COLUMNS]
    average_body = [[row["site"], row["size"],
                     *(f"{row[ms]:.3f} ({row[pct]:.1f}%)" for ms, pct in zip(STAGE_COLUMNS, PCT_COLUMNS)),
                     f"{row['Total_ms']:.3f}", row["hot_stage"], f"{row['p_hot']:.3f}",
                     f"{row['amdahl_limit']:.3f}"] for row in averages]
    minimum_body = [[row["site"], row["size"], *(f"{row[column]:.3f}" for column in TIMING_COLUMNS)]
                    for row in minima]
    config_body = [[site, size, version or "(missing)", config or "(missing)"]
                   for (site, size), (version, config) in debug_configs.items()]
    text = "\n\n".join([
        "# V0 benchmark",
        f"GPU: {environment['gpu']}. CPU: {environment['cpu']}. Time (UTC): {environment['time_utc']}. "
        f"Runs per configuration: {environment['runs']}, after one untimed warm-up.",
        "## Average (ms, share of Total_ms)",
        markdown_table(["Site", "Size", *stages, "Total", "Hot stage", "p", "1/(1-p)"], average_body),
        "## Minimum (ms)",
        markdown_table(["Site", "Size", *stages, "Total"], minimum_body),
        "## Config",
        markdown_table(["Site", "Size", "Version and seed", "Config"], config_body),
    ])
    Path(path).write_text(text + "\n", encoding="utf-8", newline="")


def run_benchmark(stitch_cmd, stitch_path, dataset, runs, out):
    """Run every configuration, then write summary.csv, summary.md and environment.json."""
    check_inputs(dataset)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    environment = collect_environment(stitch_path, runs, [])
    print(f"GPU: {environment['gpu']}\nCPU: {environment['cpu']}", flush=True)
    rows, debug_configs = [], {}
    for site, size in configurations():
        print(f"Running {site}/{size} ...", flush=True)
        command, stdout, stderr = run_config(stitch_cmd, dataset, out, site, size, runs)
        environment["commands"].append(command)
        try:
            parsed = parse_stitch_csv(stdout, runs)
        except ValueError as error:
            raise BenchmarkError(f"Invalid CSV from {site}/{size}: {error}") from error
        rows.extend(summary_rows(site, size, parsed))
        debug_configs[(site, size)] = read_debug_config(stderr)
    write_summary_csv(out / "summary.csv", rows)
    write_summary_md(out / "summary.md", rows, environment, debug_configs)
    (out / "environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out / 'summary.csv'}, {out / 'summary.md'} and {out / 'environment.json'}")
    return rows


def main(argv=None):
    args = parse_args(argv)
    if not args.stitch.is_file():
        print(f"error: stitch binary not found: {args.stitch}", file=sys.stderr)
        return 1
    try:
        run_benchmark([args.stitch], args.stitch, args.dataset, args.runs, args.out)
    except BenchmarkError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
