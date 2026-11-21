# Authors: Le Ha Thanh Chuong (23120195)
# External source: none
"""Evidence processing for the isolated P10-T01 V4 baseline experiment."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SITES = ("site1", "site2", "site3")
MANIFEST_SHA256 = "99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d"
PROBE_COLUMNS = [
    "PreS4_ms", "Host_PreS4_ms", "H2D_A_ms", "H2D_B_ms", "S1_A_ms", "S1_B_ms",
    "S2_A_ms", "S2_B_ms", "S3_A_ms", "S3_B_ms", "CountD2H_A_ms", "CountD2H_B_ms",
    "CountWait_A_ms", "CountWait_B_ms", "WorkspaceFree_bytes", "AfterD2HFree_bytes",
    "TotalVRAM_bytes", "Scratch_bytes", "Total_ms",
]


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def recorded(command, root, label, cwd, *, env=None, required=True, timeout=1800):
    prefix = Path(root) / "logs" / label
    prefix.parent.mkdir(parents=True, exist_ok=True)
    args = list(map(str, command))
    try:
        run = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        code, stdout, stderr = run.returncode, run.stdout, run.stderr
    except subprocess.TimeoutExpired as error:
        code = -1
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        stdout = stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode(errors="replace") if isinstance(stderr, bytes) else stderr
        stderr += "\nTIMEOUT"
    except OSError as error:
        code, stdout, stderr = -1, "", str(error)
    prefix.with_suffix(".stdout").write_text(stdout, encoding="utf-8")
    prefix.with_suffix(".stderr").write_text(stderr, encoding="utf-8")
    dump(prefix.with_suffix(".command.json"), {"command": args, "returncode": code})
    print(f"{label}: exit {code}")
    if required and code:
        raise RuntimeError(f"{label} failed. See {prefix}.stderr and export partial evidence.")
    return code, stdout, stderr


def dataset_manifest(dataset):
    from notebook.midterm_notebook import validate_dataset
    dataset = Path(dataset)
    if sha256(dataset / "manifest.csv") != MANIFEST_SHA256:
        raise ValueError("Official dataset manifest hash differs from P7-P9.")
    rows = validate_dataset(dataset)
    return [row for row in rows if row["file"].startswith(SITES)
            and "/large_" in row["file"]]


def read_probe(path, runs):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != PROBE_COLUMNS:
            raise ValueError(f"Unexpected probe schema: {path}")
        rows = [{key: float(value) for key, value in row.items()} for row in reader]
    if len(rows) != runs:
        raise ValueError(f"Expected {runs} measured runs in {path}, found {len(rows)}")
    for row in rows:
        if any(not math.isfinite(v) or v < 0 for v in row.values()):
            raise ValueError("Non-finite or negative measurement")
        if row["Total_ms"] <= 0 or not 0 < row["PreS4_ms"] <= row["Total_ms"] + 0.1:
            raise ValueError("Invalid pre-S4/total interval")
    return rows


def summarize(rows):
    return {key: {"mean": statistics.mean(row[key] for row in rows),
                  "median": statistics.median(row[key] for row in rows),
                  "minimum": min(row[key] for row in rows),
                  "maximum": max(row[key] for row in rows),
                  "stdev": statistics.stdev(row[key] for row in rows)}
            for key in PROBE_COLUMNS}


def write_csv(path, rows):
    if not rows:
        raise ValueError("No records to export")
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(root, runs):
    from run_benchmark import parse_version_csv
    root = Path(root)
    summary = []
    raw = []
    for site in SITES:
        rows = read_probe(root / f"{site}_probe.csv", runs)
        production = parse_version_csv(
            (root / "logs" / f"{site}_production.stdout").read_text(encoding="utf-8"), runs, 4)
        probe_stdout = parse_version_csv(
            (root / "logs" / f"{site}_probe.stdout").read_text(encoding="utf-8"), runs, 4)
        if sha256(root / f"{site}_production.png") != sha256(root / f"{site}_probe.png"):
            raise ValueError(f"{site}: probe panorama differs from production")
        stats = summarize(rows)
        dump(root / f"{site}_statistics.json", stats)
        gpu = json.loads((root / f"{site}_gpu.json").read_text())
        minimum_free = min(
            gpu["before_workspace_free_bytes"],
            *(row[key] for row in rows for key in ("WorkspaceFree_bytes", "AfterD2HFree_bytes")),
        )
        scratch_extra = gpu["branch_scratch_A_bytes"] + gpu["branch_scratch_B_bytes"]
        summary.append({
            "case": f"{site}/large",
            "PreS4_median_ms": stats["PreS4_ms"]["median"],
            "PreS4_mean_ms": stats["PreS4_ms"]["mean"],
            "PreS4_stdev_ms": stats["PreS4_ms"]["stdev"],
            "H2D_mean_ms": sum(stats[f"H2D_{b}_ms"]["mean"] for b in "AB"),
            "S1_mean_ms": sum(stats[f"S1_{b}_ms"]["mean"] for b in "AB"),
            "S2_mean_ms": sum(stats[f"S2_{b}_ms"]["mean"] for b in "AB"),
            "S3_mean_ms": sum(stats[f"S3_{b}_ms"]["mean"] for b in "AB"),
            "S2_host_wait_mean_ms": sum(stats[f"CountWait_{b}_ms"]["mean"] for b in "AB"),
            "Production_Total_mean_ms": production["average"]["Total_ms"],
            "Probe_Total_mean_ms": probe_stdout["average"]["Total_ms"],
            "Probe_PreS4_share": statistics.mean(row["PreS4_ms"] / row["Total_ms"] for row in rows),
            "Sampled_min_free_bytes": minimum_free,
            "Sampled_max_device_used_bytes": gpu["total_bytes"] - minimum_free,
            "Additional_branch_scratch_bytes": scratch_extra,
            "Scratch_headroom_check": minimum_free > scratch_extra,
        })
        raw.extend({"case": site + "/large", "run": i, **row} for i, row in enumerate(rows, 1))
    write_csv(root / "raw_timing.csv", raw)
    write_csv(root / "summary.csv", summary)
    write_csv(root / "memory.csv", [
        {k: v for k, v in row.items() if k == "case" or "bytes" in k or "headroom" in k}
        for row in summary
    ])
    return summary


def plot_summary(rows, path):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
    labels = [row["case"] for row in rows]
    axes[0].bar(labels, [row["PreS4_mean_ms"] for row in rows],
                yerr=[row["PreS4_stdev_ms"] for row in rows], capsize=4)
    axes[0].set(title="V4 probe pre-S4", ylabel="Mean time ± sample SD (ms)")
    axes[1].bar(labels, [100 * row["Probe_PreS4_share"] for row in rows])
    axes[1].set(title="Pre-S4 share of probe latency", ylabel="Percent")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def assessment(rows):
    ranked = sorted(rows, key=lambda r: r["Probe_PreS4_share"], reverse=True)
    candidate = ranked[0]
    current = next(r for r in rows if r["case"] == "site2/large")
    return {
        "frozen_primary": "site2/large",
        "largest_observed_preS4_share": candidate["case"],
        "recommendation": (
            "Retain site2/large" if candidate["case"] == current["case"] else
            f"Review {candidate['case']} before observing V5 results; keep site2/large frozen until documented approval"
        ),
        "limitations": [
            "Probe events and the explicit readiness wait add overhead.",
            "Host wait includes GPU work awaiting completion.",
            "Sampled VRAM is whole-device usage, not an exact process allocation peak.",
            "Overlap and exact GPU idle gaps require a trace.",
            "VRAM scratch comparison excludes future V5 metadata and event resources.",
        ],
        "rows": rows,
    }


def package(root):
    root = Path(root).resolve()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    dump(root / "checksums.json", {str(p.relative_to(root)): sha256(p) for p in files
                                   if p.name != "checksums.json"})
    archive = root.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zipped.write(path, str(path.relative_to(root.parent)))
    return archive
