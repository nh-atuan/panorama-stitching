#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166), Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Charts, speedup plots and hot stage analysis for multi-version panorama benchmarks.

Supports single-version summary.csv (P3-T05) and multi-version speedup.csv (P5-T05).
No timing is measured here.

Outputs in --out:
    stage_timing.png   stacked average time of S1-S6 per size, one panel per site
    stage_share.png    the same as a share of Total_ms
    hot_stages.csv     hot stage, its share, p and 1/(1-p) for every site and size
    hot_stages.md      the same table, the mean share of every stage per size and a summary line
    speedup.png        speedup vs V0 across resolutions (when speedup.csv is provided)

Example:
    python scripts/plot_benchmark.py --summary results/benchmark/v0/summary.csv --out results/benchmark/v0/analysis
    python scripts/plot_benchmark.py --speedup results/benchmark/speedup.csv --out results/benchmark/analysis
"""

import argparse
import csv
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from midterm_notebook import SIZES  # noqa: E402
from run_benchmark import BENCHMARK_SITES, PCT_COLUMNS, BASE_STAGE_COLUMNS  # noqa: E402

STAGE_COLUMNS = BASE_STAGE_COLUMNS
STAGES = [column[:-3] for column in STAGE_COLUMNS]
# Same color palette as Group16_Midterm.ipynb.
COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]
HOT_COLUMNS = ["site", "size", "hot_stage", "hot_pct", "p_hot", "amdahl_limit"]


class AnalysisError(RuntimeError):
    """The summary cannot be analysed; the message says why."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Plot stage timing, speedups and hot stages.")
    parser.add_argument("--summary", type=Path, default=None, help="summary.csv from run_benchmark.py")
    parser.add_argument("--speedup", type=Path, default=None, help="speedup.csv from multi-version run_benchmark.py")
    parser.add_argument("--out", required=True, type=Path, help="folder for charts and tables")
    return parser.parse_args(argv)


def load_averages(path):
    """Return {(site, size): row} of the average rows, numbers converted to float."""
    averages = {}
    with Path(path).open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("stat") != "average":
                continue
            for column in [*STAGE_COLUMNS, "Total_ms", *PCT_COLUMNS, "p_hot", "amdahl_limit"]:
                if column in row and row[column]:
                    row[column] = float(row[column])
            averages[(row["site"], row["size"])] = row
    return averages


def check_complete(averages):
    missing = [f"{site}/{size}" for site in BENCHMARK_SITES for size in SIZES
               if (site, size) not in averages]
    if missing:
        raise AnalysisError("Missing average rows in summary.csv: " + ", ".join(missing))


def hot_stage_table(averages):
    rows = []
    for site in BENCHMARK_SITES:
        for size in SIZES:
            row = averages[(site, size)]
            hot_pct = row[PCT_COLUMNS[STAGES.index(row["hot_stage"])]]
            rows.append({"site": site, "size": size, "hot_stage": row["hot_stage"], "hot_pct": hot_pct,
                         "p_hot": row["p_hot"], "amdahl_limit": row["amdahl_limit"]})
    return rows


def mean_shares_by_size(averages):
    """Mean over the sites of each stage share, per size; ties go to the earlier stage."""
    result = {}
    for size in SIZES:
        shares = [sum(averages[(site, size)][column] for site in BENCHMARK_SITES) / len(BENCHMARK_SITES)
                  for column in PCT_COLUMNS]
        hot = max(range(len(shares)), key=lambda index: (shares[index], -index))
        result[size] = {"shares": shares, "hot_stage": STAGES[hot]}
    return result


def hot_stage_summary(table):
    """One sentence per size naming the hot stage of every site."""
    parts = []
    for size in SIZES:
        by_stage = {}
        for row in table:
            if row["size"] == size:
                by_stage.setdefault(row["hot_stage"], []).append(row["site"])
        parts.append(f"{size}: " + "; ".join(f"{stage} ({', '.join(sites)})"
                                             for stage, sites in by_stage.items()))
    return "Hot stage by size - " + " | ".join(parts) + "."


def plot_stacked(averages, columns, ylabel, path):
    figure, axes = plt.subplots(1, len(BENCHMARK_SITES), figsize=(15, 4), sharey=True)
    positions = range(len(SIZES))
    for axis, site in zip(axes, BENCHMARK_SITES):
        bottom = [0.0] * len(SIZES)
        for stage, column, color in zip(STAGES, columns, COLORS):
            values = [averages[(site, size)][column] for size in SIZES]
            axis.bar(positions, values, bottom=bottom, color=color, label=stage)
            bottom = [low + value for low, value in zip(bottom, values)]
        axis.set_xticks(list(positions), list(SIZES))
        axis.set(title=site, xlabel="Resolution", ylabel=ylabel)
        axis.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=len(STAGES), frameon=False)
    figure.tight_layout(rect=(0, 0, 1, 0.9))
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def plot_speedup(speedup_path, out_path):
    """Plot speedup vs V0 grouped bar chart by site and resolution."""
    rows = []
    with Path(speedup_path).open(encoding="utf-8", newline="") as stream:
        for r in csv.DictReader(stream):
            if r.get("version") == "V0":
                continue
            rows.append(r)
    if not rows:
        return

    versions = sorted(list({r["version"] for r in rows}))
    figure, axes = plt.subplots(1, len(BENCHMARK_SITES), figsize=(15, 4), sharey=True)
    if len(BENCHMARK_SITES) == 1:
        axes = [axes]

    x = np.arange(len(SIZES))
    width = 0.8 / max(1, len(versions))

    for axis, site in zip(axes, BENCHMARK_SITES):
        for idx, ver in enumerate(versions):
            vals = []
            for sz in SIZES:
                match = next((float(r["speedup_vs_v0"]) for r in rows
                              if r["site"] == site and r["size"] == sz and r["version"] == ver), 1.0)
                vals.append(match)
            offset = (idx - (len(versions) - 1) / 2) * width
            axis.bar(x + offset, vals, width, label=ver)
        axis.set_xticks(x, list(SIZES))
        axis.set(title=site, xlabel="Resolution", ylabel="Speedup vs V0 (x)")
        axis.axhline(1.0, color="gray", linestyle="--", linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=len(versions), frameon=False)
    figure.tight_layout(rect=(0, 0, 1, 0.9))
    figure.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def write_hot_stages_csv(path, table):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HOT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in table:
            writer.writerow({key: f"{value:.6f}" if isinstance(value, float) else value
                             for key, value in row.items()})


def write_hot_stages_md(path, table, means):
    hot_rows = ["| " + " | ".join([row["site"], row["size"], row["hot_stage"], f"{row['hot_pct']:.1f}%",
                                   f"{row['p_hot']:.3f}", f"{row['amdahl_limit']:.3f}"]) + " |"
                for row in table]
    mean_rows = ["| " + " | ".join([size, *(f"{share:.1f}%" for share in mean["shares"]),
                                     mean["hot_stage"]]) + " |" for size, mean in means.items()]
    text = "\n".join([
        "# Hot stages", "",
        "## Per site and size", "",
        "| Site | Size | Hot stage | Share of Total | p | 1/(1-p) |", "|---|---|---|---|---|---|",
        *hot_rows, "",
        "## Mean share of each stage over the sites", "",
        "| Size | " + " | ".join(STAGES) + " | Hot stage |", "|" + "---|" * (len(STAGES) + 2),
        *mean_rows, "",
        hot_stage_summary(table), "",
    ])
    Path(path).write_text(text, encoding="utf-8", newline="")


def analyse(summary, out):
    averages = load_averages(summary)
    check_complete(averages)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    table = hot_stage_table(averages)
    means = mean_shares_by_size(averages)
    plot_stacked(averages, STAGE_COLUMNS, "Average time (ms)", out / "stage_timing.png")
    plot_stacked(averages, PCT_COLUMNS, "Share of Total_ms (%)", out / "stage_share.png")
    write_hot_stages_csv(out / "hot_stages.csv", table)
    write_hot_stages_md(out / "hot_stages.md", table, means)
    return table, means


def main(argv=None):
    args = parse_args(argv)
    if not args.summary and not args.speedup:
        print("error: at least one of --summary or --speedup must be provided", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.summary:
        if not args.summary.is_file():
            print(f"error: summary not found: {args.summary}", file=sys.stderr)
            return 1
        try:
            table, _ = analyse(args.summary, out)
            print(hot_stage_summary(table))
            print(f"Wrote charts and tables to {out}")
        except AnalysisError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1

    if args.speedup:
        if not args.speedup.is_file():
            print(f"error: speedup file not found: {args.speedup}", file=sys.stderr)
            return 1
        plot_speedup(args.speedup, out / "speedup.png")
        print(f"Wrote speedup chart to {out / 'speedup.png'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
