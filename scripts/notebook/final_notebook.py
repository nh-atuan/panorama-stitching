#!/usr/bin/env python3
# Authors: Tran Huu Kim Thanh (23120166)
# External source: none

"""Data producer, loader, tables, charts and gallery for Group16_Final.ipynb (P9-T03).

The notebook calls these functions; it holds no copy of the code. The producer fetches the
final dataset, builds stitch and runs one benchmark session for every version the build
supports. The loader reads the files that run_benchmark.py writes (docs/report/
p9-final-notebook-handoff.md) and the views turn them into Markdown tables and PNG charts.
No timing is measured in Python: every number comes from the stitch CSV.
"""

import csv
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notebook.midterm_notebook import SIZES, preview_image, safe_extract, sha256, validate_dataset  # noqa: E402
from run_benchmark import (  # noqa: E402
    BASE_STAGE_COLUMNS, BENCHMARK_SITES, CHALLENGE_SITE, CUDA_EXTRA_COLUMNS, FAILURE_COLUMNS,
    PCT_COLUMNS, SPEEDUP_COLUMNS, SUMMARY_COLUMNS, input_paths,
)

DATASET_DRIVE_URL = "https://drive.google.com/drive/folders/1_J_q5q-K1g7ZNnczTWvXBzwpOsof9ghL?usp=sharing"
# manifest.csv of the final dataset chosen on 03/11 (docs/dataset.md, section 8.3).
DATASET_MANIFEST_SHA256 = "99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d"
CANDIDATE_VERSIONS = (0, 1, 2, 3, 4, 5)
STAGES = [column[:-3] for column in BASE_STAGE_COLUMNS]
TEXT_COLUMNS = {"version", "site", "size", "stat", "hot_stage", "error"}
MISSING = "—"


class NotebookDataError(RuntimeError):
    """The benchmark artifacts cannot back the report; the message says why."""


# ---------------------------------------------------------------- producer

def download_dataset_zip(work_dir, drive_url=DATASET_DRIVE_URL):
    """Download the Drive folder with gdown and return the path of its single dataset.zip."""
    from fetch_and_prepare_dataset import ensure_gdown

    ensure_gdown()
    import gdown

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    if not list(work_dir.rglob("dataset.zip")):
        gdown.download_folder(url=drive_url, output=str(work_dir) + "/", quiet=True, use_cookies=False)
    archives = list(work_dir.rglob("dataset.zip"))
    if len(archives) != 1:
        raise NotebookDataError(f"Expected one dataset.zip in {work_dir}, found {len(archives)}")
    return archives[0]


def fetch_dataset(dataset_dir, work_dir, drive_url=DATASET_DRIVE_URL):
    """Return a verified dataset folder, downloading and extracting it when it is not there yet."""
    dataset_dir = Path(dataset_dir)
    if not (dataset_dir / "manifest.csv").is_file():
        safe_extract(download_dataset_zip(work_dir, drive_url), dataset_dir)
    manifest_hash = sha256(dataset_dir / "manifest.csv")
    if manifest_hash != DATASET_MANIFEST_SHA256:
        raise NotebookDataError(f"manifest.csv SHA-256 {manifest_hash} is not the final dataset's")
    return dataset_dir, validate_dataset(dataset_dir)


def run_logged(command, cwd, log_path, tail=5):
    """Run `command`, keep its full output in `log_path` and print the last lines.

    A notebook cell does not show the output of a child process, so the log is the record;
    a failure raises with the end of the log.
    """
    result = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True, text=True)
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    last = "\n".join((result.stdout + result.stderr).strip().splitlines()[-tail:])
    if result.returncode != 0:
        raise NotebookDataError(f"{Path(command[1]).name} exited with {result.returncode}; "
                                f"see {log_path}\n{last}")
    print(last)
    return log_path


def build_stitch(repo_root, out_dir="build"):
    """Build stitch for the T4 with the repository script and return the binary path."""
    run_logged([sys.executable, "scripts/build.py", "--compiler", "nvcc", "--require-t4",
                "--out-dir", out_dir], repo_root, Path(repo_root) / out_dir / "build.log", tail=1)
    return Path(repo_root) / out_dir / "stitch"


def supported_versions(stitch, candidates=CANDIDATE_VERSIONS):
    """Versions the binary accepts; the CLI rejects the others before it reads any image."""
    accepted = []
    for version in candidates:
        result = subprocess.run([str(stitch), "missing_a.jpg", "missing_b.jpg", "unused.png",
                                 "--version", str(version)], capture_output=True, text=True)
        if "[UnsupportedVersion]" not in result.stderr:
            accepted.append(version)
    return accepted


def run_benchmark_session(repo_root, stitch, dataset_dir, benchmark_dir, versions, runs=5):
    """Run every version in one session into a fresh folder, challenge included.

    The runner log goes next to the folder (<benchmark_dir>.log), so the folder holds only
    what run_benchmark.py writes.
    """
    benchmark_dir = Path(benchmark_dir)
    if benchmark_dir.exists() and any(benchmark_dir.iterdir()):
        raise NotebookDataError(f"{benchmark_dir} is not empty; use a fresh folder for one session")
    run_logged([sys.executable, "scripts/run_benchmark.py", "--stitch", stitch, "--dataset", dataset_dir,
                "--runs", runs, "--out", benchmark_dir, "--versions", *versions, "--include-challenge"],
               repo_root, benchmark_dir.with_name(benchmark_dir.name + ".log"))
    return benchmark_dir


# ---------------------------------------------------------------- loader

def to_number(text):
    return float(text) if text not in ("", None) else None


def read_rows(path, columns):
    """Rows of a CSV whose header must be exactly `columns`; numeric cells become float or None."""
    path = Path(path)
    if not path.is_file():
        raise NotebookDataError(f"Missing benchmark file: {path}")
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(columns):
            raise NotebookDataError(f"Unexpected header in {path}: {reader.fieldnames}")
        return [{key: value if key in TEXT_COLUMNS else to_number(value) for key, value in row.items()}
                for row in reader]


def version_label(version):
    return f"V{version}"


class BenchmarkData:
    """The four objects of the handoff contract, read once from one benchmark folder."""

    def __init__(self, root, environment, summary, speedup, failures):
        self.root = Path(root)
        self.environment = environment
        self.summary = summary
        self.speedup = speedup
        self.failures = failures

    @property
    def versions(self):
        return [version_label(version) for version in sorted(self.environment["versions"])]

    def averages(self, version):
        return {(row["site"], row["size"]): row for row in self.summary
                if row["version"] == version and row["stat"] == "average"}

    def failure(self, version, site, size):
        return next((row for row in self.failures
                     if (row["version"], row["site"], row["size"]) == (version, site, size)), None)


def check_coverage(summary, failures, versions, include_challenge):
    """Every standard configuration is measured; every challenge one is measured or failed."""
    for version in versions:
        measured = {(row["site"], row["size"]) for row in summary
                    if row["version"] == version and row["stat"] == "average"}
        missing = [f"{site}/{size}" for site in BENCHMARK_SITES for size in SIZES
                   if (site, size) not in measured]
        if missing:
            raise NotebookDataError(f"{version} has no timing for " + ", ".join(missing))
        if not include_challenge:
            continue
        failed = {(row["site"], row["size"]) for row in failures if row["version"] == version}
        unknown = [size for size in SIZES
                   if (CHALLENGE_SITE, size) not in measured | failed]
        if unknown:
            raise NotebookDataError(f"{version} challenge has neither timing nor failure for "
                                    + ", ".join(unknown))


def load_benchmark(benchmark_dir, versions):
    """Load summary, speedup, failures and environment for `versions` (integers)."""
    root = Path(benchmark_dir)
    environment_path = root / "environment.json"
    if not environment_path.is_file():
        raise NotebookDataError(f"Missing benchmark file: {environment_path}")
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    if sorted(environment.get("versions", [])) != sorted(versions):
        raise NotebookDataError(f"environment.json lists versions {environment.get('versions')}, "
                                f"the notebook expects {sorted(versions)}")
    include_challenge = bool(environment.get("include_challenge"))
    summary, failures = [], []
    for version in sorted(versions):
        rows = read_rows(root / f"v{version}" / "summary.csv", SUMMARY_COLUMNS)
        if any(row["version"] != version_label(version) for row in rows):
            raise NotebookDataError(f"v{version}/summary.csv holds rows of another version")
        summary.extend(rows)
        if include_challenge:
            failures.extend(read_rows(root / f"v{version}" / "failures.csv", FAILURE_COLUMNS))
    speedup = read_rows(root / "speedup.csv", SPEEDUP_COLUMNS) if len(versions) > 1 else []
    check_coverage(summary, failures, [version_label(v) for v in sorted(versions)], include_challenge)
    return BenchmarkData(root, environment, summary, speedup, failures)


# ---------------------------------------------------------------- tables

def fmt(value, digits=2, suffix=""):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return MISSING
    return f"{value:.{digits}f}{suffix}"


def markdown_table(header, body):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cells) + " |" for cells in body]
    return "\n".join(lines)


def configurations(data):
    """Standard configurations, then the challenge ones the session ran, in report order."""
    sites = [*BENCHMARK_SITES]
    if data.environment.get("include_challenge"):
        sites.append(CHALLENGE_SITE)
    return [(site, size) for site in sites for size in SIZES]


def stage_table(data, version):
    """Average per-stage time in ms, with transfer and kernel totals for GPU versions."""
    gpu = version != "V0"
    header = ["Site", "Size", *STAGES, "Total", *(["H2D", "D2H", "Kernel"] if gpu else []), "Hot stage"]
    averages = data.averages(version)
    body = []
    for site, size in configurations(data):
        row = averages.get((site, size))
        if row is None:
            failure = data.failure(version, site, size)
            status = f"failed: {failure['error']}" if failure else "not run"
            body.append([site, size, *[MISSING] * (len(header) - 3), status])
            continue
        hot_share = row[PCT_COLUMNS[STAGES.index(row["hot_stage"])]]
        body.append([site, size, *(fmt(row[column]) for column in BASE_STAGE_COLUMNS), fmt(row["Total_ms"]),
                     *([fmt(row[column]) for column in CUDA_EXTRA_COLUMNS] if gpu else []),
                     f"{row['hot_stage']} ({fmt(hot_share, 1)}%)"])
    return markdown_table(header, body)


def dominant_stages(data, version):
    """Per size, the mean share of every stage over the three standard sites and the largest one."""
    averages = data.averages(version)
    result = {}
    for size in SIZES:
        shares = [sum(averages[(site, size)][column] for site in BENCHMARK_SITES) / len(BENCHMARK_SITES)
                  for column in PCT_COLUMNS]
        hot = max(range(len(shares)), key=lambda index: (shares[index], -index))
        result[size] = {"shares": dict(zip(STAGES, shares)), "hot_stage": STAGES[hot]}
    return result


def dominant_stage_table(data, version):
    shares = dominant_stages(data, version)
    body = [[size, *(fmt(shares[size]["shares"][stage], 1) for stage in STAGES), shares[size]["hot_stage"]]
            for size in SIZES]
    return markdown_table(["Size", *(f"{stage} %" for stage in STAGES), "Dominant"], body)


SITE_ORDER = (*BENCHMARK_SITES, CHALLENGE_SITE)


def speedup_rows(data, version=None):
    """Rows in report order: standard sites, then challenge; sizes small to large; versions."""
    rows = [row for row in data.speedup if version is None or row["version"] == version]
    return sorted(rows, key=lambda row: (SITE_ORDER.index(row["site"]), list(SIZES).index(row["size"]),
                                         int(row["version"].lstrip("V"))))


def speedup_table(data, version=None):
    """Total time, speedup vs V0 and vs the previous version, kernel time; failures as status."""
    header = ["Site", "Size", "Version", "Total ms", "vs V0", "vs prev", "Kernel ms", "Kernel vs V0"]
    body = [[row["site"], row["size"], row["version"], fmt(row["Total_ms"]),
             fmt(row["speedup_vs_v0"], suffix="x"), fmt(row["speedup_vs_prev"], suffix="x"),
             fmt(row["Total_Kernel_ms"]) if row["version"] != "V0" else MISSING,
             fmt(row["kernel_speedup_vs_v0"], suffix="x") if row["version"] != "V0" else MISSING]
            for row in speedup_rows(data, version)]
    body += [[row["site"], row["size"], row["version"], f"failed: {row['error']}", *[MISSING] * 4]
             for row in data.failures if version is None or row["version"] == version]
    return markdown_table(header, body)


def geomean(values):
    values = [value for value in values if value]
    return math.exp(sum(math.log(value) for value in values) / len(values)) if values else None


def geomean_speedups(data):
    """Per version, the geometric mean of speedup vs V0 over the nine standard configurations."""
    return {version: geomean(row["speedup_vs_v0"] for row in data.speedup
                             if row["version"] == version and row["site"] in BENCHMARK_SITES)
            for version in data.versions}


def best_version(data):
    """The version with the highest geometric-mean speedup vs V0 on the standard sites."""
    means = geomean_speedups(data)
    return max((version for version in means if means[version]), key=lambda version: means[version])


def geomean_table(data):
    means = geomean_speedups(data)
    return markdown_table(["Version", "Geomean speedup vs V0 (9 standard configs)"],
                          [[version, fmt(means[version], suffix="x")] for version in data.versions])


def failure_table(data):
    if not data.failures:
        return "No configuration failed."
    return markdown_table(["Version", "Site", "Size", "Exit code", "Error"],
                          [[row["version"], row["site"], row["size"], fmt(row["exit_code"], 0), row["error"]]
                           for row in data.failures])


# ---------------------------------------------------------------- charts

def plot_speedup_charts(data, out_dir):
    """speedup.png and stage_speedup_v<k>.png from the session's speedup.csv."""
    import plot_benchmark

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "speedup.png"
    plot_benchmark.plot_speedup(data.root / "speedup.csv", path)
    return [path, *plot_benchmark.plot_stage_speedups(data.root / "speedup.csv", out_dir)]


def plot_stage_breakdown(data, version, out_dir):
    """Stacked per-stage average time of `version`, one panel per site."""
    import plot_benchmark

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"stage_timing_{version.lower()}.png"
    plot_benchmark.plot_stacked(data.averages(version), BASE_STAGE_COLUMNS, "Average time (ms)", path)
    return path


# ---------------------------------------------------------------- gallery

def panorama_preview(data, version, site, size):
    """A bounded JPEG of one benchmark panorama, for IPython.display.Image(data=...)."""
    path = data.root / f"v{version[1:]}" / site / f"{size}_panorama.jpg"
    if not path.is_file():
        raise NotebookDataError(f"Missing panorama: {path}")
    return preview_image(path)


def gallery_entries(data, dataset_dir, version, size, sites=(*BENCHMARK_SITES, CHALLENGE_SITE)):
    """Inputs and panorama of each site; a failed configuration carries its status and log."""
    entries = []
    for site in sites:
        left, right = input_paths(dataset_dir, site, size)
        panorama = data.root / f"v{version[1:]}" / site / f"{size}_panorama.jpg"
        failure = data.failure(version, site, size)
        log = data.root / f"v{version[1:]}" / site / f"{size}.log"
        entries.append({
            "site": site, "size": size, "version": version, "left": left, "right": right,
            "panorama": panorama if failure is None and panorama.is_file() else None,
            "status": f"failed: {failure['error']}" if failure else ("ok" if panorama.is_file() else "missing"),
            "log": log if log.is_file() else None,
        })
    return entries


def log_tail(path, lines=3):
    return "\n".join(Path(path).read_text(encoding="utf-8").strip().splitlines()[-lines:]) if path else ""


def thumbnail(path, width=900):
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((width, width))
        return image.copy()


def plot_gallery(entries, out_path):
    """One row per entry: image A, image B and the panorama, or the failure status and log."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(len(entries), 3, figsize=(15, 3.4 * len(entries)), squeeze=False,
                                gridspec_kw={"width_ratios": [1, 1, 2]})
    for row, entry in zip(axes, entries):
        name = f"{entry['site']}/{entry['size']} {entry['version']}"
        for axis, key, title in zip(row, ("left", "right"), ("A (left)", "B (right)")):
            axis.imshow(thumbnail(entry[key]))
            axis.set_title(f"{name} · {title}", fontsize=9)
        if entry["panorama"] is not None:
            row[2].imshow(thumbnail(entry["panorama"], 1600))
            row[2].set_title(f"{name} · panorama", fontsize=9)
        else:
            row[2].text(0.5, 0.5, f"{entry['status']}\n\n{log_tail(entry['log'])}", ha="center",
                        va="center", wrap=True, fontsize=9, family="monospace")
            row[2].set_title(f"{name} · no panorama", fontsize=9)
        for axis in row:
            axis.axis("off")
    figure.tight_layout()
    # JPEG keeps the embedded photos small in the saved notebook and its PDF export.
    out_path = Path(out_path).with_suffix(".jpg")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out_path, dpi=90, bbox_inches="tight", pil_kwargs={"quality": 85})
    plt.close(figure)
    return out_path
