# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Read-only review of returned T4 artifacts; preserve the original controller verdict."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

from PIL import Image

from accept_final_notebook import inspect_outputs
from audit_final_notebook import compare_freeze
from export_notebook_pdf import inspect_pdf
from notebook import final_notebook as fn
from notebook_preflight import MANIFEST_SHA256
from run_benchmark import parse_version_csv, read_error_code
from synthetic.homography_error import parse_estimate
from v5_report import analyze, geomean
from verify.verify_v2_dataset import CANVAS, DRIFT_PX, projection_drift, rgb_delta

VERSIONS = tuple(range(6))
SIZES = {"small": (1280, 720), "medium": (1920, 1080), "large": (3840, 2160)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def checksums(run):
    """Never rewrite original files while validating their inventory."""
    run = Path(run).resolve()
    expected = read_json(run / "evidence_checksums.json")
    if not expected:
        raise ValueError("Empty evidence checksum inventory")
    for name, value in expected.items():
        path = (run / name).resolve()
        if not path.is_relative_to(run) or not path.is_file() or digest(path) != value:
            raise ValueError(f"Evidence checksum mismatch or missing file: {name}")
    return len(expected)


def recovery_scope(summary):
    if summary.get("status") == "executed_review_pending":
        return "no recovery required"
    if (summary.get("status") != "failed" or
            summary.get("error") != "PDF automatic QA failed; see pdf/pdf_export.json" or
            summary.get("outputs", {}).get("status") != "passed" or
            summary.get("benchmark", {}).get("status") != "passed" or
            summary.get("pdf", {}).get("status") != "qa_failed"):
        raise ValueError("Not an isolated post-execution PDF QA failure; do not recover as a completed run")
    return "original PDF QA failure retained; independent revalidation required"


def aggregates(averages):
    cases = [(f"site{i}", size) for i in (1, 2, 3) for size in SIZES]
    result = {}
    for version in VERSIONS[1:]:
        baseline = [averages[(0, *case)] / averages[(version, *case)] for case in cases]
        previous = [averages[(version - 1, *case)] / averages[(version, *case)] for case in cases]
        result[f"V{version}"] = dict(vs_v0=geomean(baseline), vs_previous=geomean(previous))
    return result


def review(run, repo, tooling_ref, pdf_copy):
    run, repo = Path(run).resolve(), Path(repo).resolve()
    checked = checksums(run)
    summary = read_json(run / "execution_summary.json")
    scope = recovery_scope(summary)
    notebook = run / "Group16_Final.ipynb"
    if digest(notebook) != summary["notebook_sha256"] or read_json(run / "cell_errors.json"):
        raise ValueError("Executed notebook hash or cell errors disagree with summary")
    outputs = inspect_outputs(notebook)
    if outputs["source_sha"] != summary["source_sha"] or (run / "source_sha.txt").read_text().strip() != summary["source_sha"]:
        raise ValueError("Source SHA differs between output, metadata and source_sha.txt")
    overlay = read_json(run / "runtime_overlay.json")
    if digest(run / "Group16_Final.input.ipynb") != overlay["input_sha256"]:
        raise ValueError("Input notebook differs from the prepared input")
    blob = lambda name: subprocess.check_output(["git", "show", f"{tooling_ref}:{name}"], cwd=repo)
    if hashlib.sha256(blob("Group16_Final.ipynb")).hexdigest() != overlay["input_sha256"]:
        raise ValueError("Input notebook does not match the declared tooling revision")
    for name, value in overlay["tooling_files"].items():
        if hashlib.sha256(blob(f"scripts/{name}")).hexdigest() != value:
            raise ValueError(f"Tooling revision mismatch: {name}")
    for name, value in overlay["local_reference_hashes"].items():
        source_blob = subprocess.check_output(["git", "show", f"{summary['source_sha']}:{name}"], cwd=repo)
        if hashlib.sha256(source_blob).hexdigest() != value:
            raise ValueError(f"Source reference differs from execution metadata: {name}")

    env, data = read_json(run / "environment.json"), read_json(run / "dataset.json")
    gpu = env["gpu"]
    if env["status"] != "passed" or gpu["name"] not in ("Tesla T4", "NVIDIA T4") or gpu["compute_capability"] != "7.5":
        raise ValueError("Environment is not a passed T4 preflight")
    if digest(run / "dataset_manifest.csv") != MANIFEST_SHA256 or data["manifest_sha256"] != MANIFEST_SHA256:
        raise ValueError("Official dataset manifest identity differs")
    manifest = list(csv.DictReader(io.StringIO((run / "dataset_manifest.csv").read_text(encoding="utf-8"))))
    if len(manifest) != 24 or {r["file"]: r["sha256"] for r in manifest} != {r["file"]: r["sha256"] for r in data["images"]}:
        raise ValueError("Dataset manifest/image preflight differs")
    build = (run / "build.log").read_text(encoding="utf-8")
    for flag in ("-arch=sm_75", "-O2", "--fmad=false", "PANORAMA_V5_IMAGE_API_AVAILABLE", "Built: build/stitch"):
        if flag not in build:
            raise ValueError(f"Build does not record required flag/result: {flag}")

    benchmark = fn.load_benchmark(run / "benchmark", VERSIONS)
    if benchmark.environment["runs"] != 5 or benchmark.environment["gpu"] != f"{gpu['name']}, {gpu['driver']}":
        raise ValueError("Benchmark session differs from T4 environment")
    if benchmark.environment["stitch_sha256"] != summary["benchmark"]["environment"]["stitch_sha256"]:
        raise ValueError("Binary identity differs between benchmark and summary")
    averages, records, diagnostics, panoramas = {}, [], {}, {}
    for site in ("site1", "site2", "site3", "challenge"):
        for size, dimensions in SIZES.items():
            for version in VERSIONS:
                prefix = run / f"benchmark/v{version}/{site}/{size}"
                log = prefix.with_suffix(".log").read_text(encoding="utf-8")
                failure = benchmark.failure(f"V{version}", site, size)
                expected = "NumericalFailure" if site == "challenge" and size != "small" else "Success"
                actual = failure["error"] if failure else "Success"
                if actual != expected:
                    raise ValueError(f"Status V{version}/{site}/{size}: {actual}, expected {expected}")
                record = dict(version=version, site=site, size=size, status=actual)
                if failure:
                    if failure["exit_code"] != 1 or read_error_code(log) != expected or prefix.with_name(f"{size}_panorama.jpg").exists():
                        raise ValueError(f"Invalid failure routing: {prefix}")
                    records.append(record)
                    continue
                parsed = parse_version_csv(prefix.with_suffix(".csv").read_text(encoding="utf-8"), 5, version)
                reported = benchmark.averages(f"V{version}")[(site, size)]
                for key, value in parsed["average"].items():
                    if not math.isclose(value, reported[key], rel_tol=1e-7, abs_tol=1e-6):
                        raise ValueError(f"Summary differs from raw CSV: {prefix}/{key}")
                averages[(version, site, size)] = parsed["average"]["Total_ms"]
                geometry = CANVAS.findall(log)
                if len(geometry) != 1:
                    raise ValueError(f"Missing/duplicated canvas: {prefix}")
                canvas = tuple(map(int, geometry[0]))
                config = next(line for line in log.splitlines() if line.startswith("[debug] config: "))
                h = parse_estimate(log).ravel().tolist()
                image_path = prefix.with_name(f"{size}_panorama.jpg")
                with Image.open(image_path) as image:
                    if image.mode != "RGB" or image.size != canvas[:2]:
                        raise ValueError(f"D2H artifact differs from canvas: {image_path}")
                    image.verify()
                key = (site, size)
                if key not in diagnostics:
                    diagnostics[key] = (config, h, canvas)
                    panoramas[key] = image_path
                ref_config, ref_h, ref_canvas = diagnostics[key]
                drift = projection_drift(ref_h, h, *dimensions)
                if config != ref_config or canvas != ref_canvas or drift >= DRIFT_PX:
                    raise ValueError(f"H/config/canvas regression at {prefix}")
                identical = digest(image_path) == digest(panoramas[key])
                delta = 0 if identical else rgb_delta(panoramas[key], image_path)
                if delta > 1:
                    raise ValueError(f"Decoded JPEG RGB differs at {prefix}: {delta}")
                record.update(total_ms=averages[(version, site, size)], canvas=canvas,
                              drift_px=drift, decoded_jpeg_max_rgb=delta, jpeg_bytes_identical=identical)
                records.append(record)

    historical = analyze(repo / "docs/report/p10-t05-v5-apod.md", repo)
    n = read_json(notebook)
    cell = next(c for c in n["cells"] if c.get("id") == "v5-p10-results")
    saved = json.dumps(cell["outputs"], ensure_ascii=False)
    for key in ("geomean_nine", "geomean_v5_v0", "geomean_dual_seq", "geomean_pres4", "paired_median"):
        if f"{historical['metrics'][key]:.6f}" not in saved:
            raise ValueError(f"Historical metric not present in saved V5 output: {key}")
    # Copy must be byte-identical; inspect_pdf writes only beside this review copy.
    if digest(pdf_copy) != digest(run / "pdf/Group16_Final.pdf"):
        raise ValueError("Review PDF is not the original Colab PDF")
    pdf = inspect_pdf(pdf_copy, expect_raster=True)
    if pdf["problems"]:
        raise ValueError(f"PDF review failed: {pdf['problems']}")
    return dict(status="automatic_review_passed_manual_review_required", original_status=summary["status"],
                recovery_scope=scope, checked_files=checked, source_sha=summary["source_sha"],
                tooling_ref=tooling_ref, notebook_sha256=digest(notebook),
                input_sha256=overlay["input_sha256"], dataset_manifest_sha256=MANIFEST_SHA256,
                environment=env, benchmark_environment={k: v for k, v in benchmark.environment.items() if k != "commands"},
                outputs=outputs, configurations=records, current_session=aggregates(averages),
                historical_metrics=historical["metrics"], pdf=pdf,
                freeze_comparison=compare_freeze(repo, summary["source_sha"]),
                limits=["No GPU regression/memcheck rerun is present in these artifacts",
                        "JPEG parity is exported-artifact consistency, not a raw S6 pixel/ground-truth test",
                        "Original P10-T05 CSV/SQLite archive was not independently inspected",
                        "Course-provided sample pair and Colab UI Mermaid rendering need explicit review"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tooling-ref", required=True)
    parser.add_argument("--pdf-copy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = review(args.run, args.repo, args.tooling_ref, args.pdf_copy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{result['status']}: {result['checked_files']} checksums, {len(result['configurations'])} configurations, {result['pdf']['pages']} PDF pages")


if __name__ == "__main__":
    main()
