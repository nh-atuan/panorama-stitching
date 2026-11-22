#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Execute a provenance-recorded copy on T4; archive successes and failures without publishing."""

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import traceback
import uuid
import zipfile

from audit_final_notebook import SECTIONS, local_links, reconcile_apod, section_structure, compare_freeze, FREEZE_SHA
from export_notebook_pdf import executed_notebook, export
from notebook.midterm_notebook import sha256
from notebook_preflight import dataset, environment, VERSIONS
from package_notebook_acceptance import published, verify_archive, verify_tree
from profiling.profiling_common import write_json
from run_benchmark import parse_version_csv

VISIBLE_CELLS = ("thanh-v0-tables", "thanh-v1-tables", "thanh-v4-tables",
                 "thanh-comparison-tables", "thanh-charts", "thanh-gallery")


def new_run(root):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(root) / f"{stamp}-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path.resolve()


def prepare_notebook(original, source, source_sha, run, tools, candidate=True):
    """Record a minimal runtime overlay; never alter authored prose, methods or output values."""
    import nbformat as nbf
    raw = json.loads(Path(original).read_text(encoding="utf-8"))
    changed = []
    for i, cell in enumerate(raw["cells"], 1):
        cell["source"] = "".join(cell.get("source", ""))
        if not cell.get("id"):
            cell["id"] = f"acceptance-cell-{i}"
            changed.append(dict(cell=i, change="stable missing cell ID"))
    notebook = nbf.from_dict(raw)
    source, run, tools = Path(source).resolve(), Path(run).resolve(), Path(tools).resolve()
    references = {}
    for cell in notebook.cells:
        if cell.cell_type != "markdown":
            continue
        for relative in local_links(cell.source):
            target = (source / relative).resolve()
            if not target.is_relative_to(source) or not target.is_file():
                raise ValueError(f"Missing or unsafe notebook reference in verified source: {relative}")
            references[relative] = sha256(target)
    # Runtime paths are literal, with source paths taking precedence over harness helpers.
    bootstrap = f'''import os, sys
from pathlib import Path
SOURCE_REF = {source_sha!r}
REPO_URL = "https://github.com/nh-atuan/panorama-stitching.git"
REPO_ROOT = Path({str(source)!r})
WORK_DIR = Path({str(run)!r})
sys.path.insert(0, {str(tools)!r})
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from package_notebook_acceptance import verify_tree
verify_tree(REPO_ROOT, SOURCE_REF)
DATASET_DIR = Path(os.environ["GROUP16_DATASET_DIR"])
BENCHMARK_DIR = WORK_DIR / "benchmark"
BASELINE_VERSIONS = (0, 1, 2, 3, 4, 5)
TIMED_RUNS = 5
if BENCHMARK_DIR.exists():
    raise RuntimeError("Fresh acceptance must not reuse a benchmark session")
print("Effective source SHA:", SOURCE_REF)
print("Run purpose:", {"candidate - source freeze pending" if candidate else "frozen source declared; acceptance checks still required"!r})
print("Timed runs:", TIMED_RUNS)
'''
    setup_found = producer_found = False
    for i, cell in enumerate(notebook.cells, 1):
        if cell.cell_type == "code":
            cell.outputs, cell.execution_count = [], None
        if cell.get("id") == "runtime-setup":
            cell.source = bootstrap
            setup_found = True
            changed.append(dict(cell=i, change="exact verified source/path bootstrap; no checkout fallback"))
        if cell.get("id") == "thanh-producer":
            old = "fn.supported_versions(STITCH)"
            if old not in cell.source:
                raise ValueError("Producer changed upstream; review overlay rather than guessing")
            cell.source = cell.source.replace(old, "fn.supported_versions(STITCH, candidates=BASELINE_VERSIONS)")
            # Dataset has been downloaded/validated before the kernel starts.
            producer_found = True
            changed.append(dict(cell=i, change="probe V0-V5 explicitly, bypass legacy candidate-list default"))
        if cell.cell_type == "code":
            ast.parse(cell.source)
    if not setup_found or not producer_found:
        raise ValueError("Missing runtime-setup/thanh-producer anchors; manual integration required")
    notebook.metadata["group16_acceptance"] = dict(source_sha=source_sha, candidate=candidate,
        input_sha256=sha256(original), overlay=changed, local_reference_hashes=references)
    nbf.validate(notebook)
    return notebook


def inspect_outputs(path):
    notebook = executed_notebook(path)
    _, errors = section_structure(notebook.cells)
    if errors:
        raise ValueError("; ".join(errors))
    by_id = {c.get("id"): c for c in notebook.cells}
    for cell_id in VISIBLE_CELLS:
        if cell_id not in by_id or not by_id[cell_id].get("outputs"):
            raise ValueError(f"Required result cell has no outputs: {cell_id}")
    gallery = by_id["thanh-gallery"].outputs
    if not any(any(k.startswith("image/") for k in o.get("data", {})) for o in gallery):
        raise ValueError("Gallery contains no embedded image output")
    setup = "".join(o.get("text", "") for o in by_id["runtime-setup"].outputs)
    sha = notebook.metadata["group16_acceptance"]["source_sha"]
    if sha not in setup:
        raise ValueError("Effective source SHA is absent from executed setup output")
    return dict(status="passed", code_cells=sum(c.cell_type == "code" for c in notebook.cells),
                source_sha=sha, gallery_embedded=True, sections=SECTIONS)


def benchmark_evidence(root, binary, expected_versions=VERSIONS):
    from notebook import final_notebook as fn
    root = Path(root)
    benchmark = fn.load_benchmark(root, expected_versions)
    env = benchmark.environment
    if env.get("runs", 0) < 5 or "T4" not in env.get("gpu", ""):
        raise ValueError("Benchmark session is not a five-run T4 session")
    if env.get("stitch_sha256") != sha256(binary):
        raise ValueError("Benchmark binary hash does not match the executed source build")
    checked = []
    for version in expected_versions:
        for site in ("site1", "site2", "site3", "challenge"):
            for size in ("small", "medium", "large"):
                failure = benchmark.failure(f"V{version}", site, size)
                path = root / f"v{version}" / site / f"{size}.csv"
                if failure:
                    if site != "challenge":
                        raise ValueError(f"Unexpected standard failure: V{version}/{site}/{size}")
                    log = path.with_suffix(".log")
                    if not log.is_file() or failure["error"] not in log.read_text(encoding="utf-8"):
                        raise ValueError(f"Failure lacks its raw log: {path}")
                else:
                    parse_version_csv(path.read_text(encoding="utf-8"), env["runs"], version)
                    panorama = path.with_name(f"{size}_panorama.jpg")
                    if not panorama.is_file() or not panorama.stat().st_size:
                        raise ValueError(f"Missing successful panorama: {panorama}")
                checked.append(dict(version=version, site=site, size=size,
                                    status=failure["error"] if failure else "Success"))
    return dict(status="passed", cases=checked, environment=env,
                limits="CSV/status/output validation only; geometric/RGB regression comes from T02")


def bundle(run):
    run = Path(run)
    hashes = {p.relative_to(run).as_posix(): sha256(p) for p in sorted(run.rglob("*"))
              if p.is_file() and p.name != "evidence_checksums.json"}
    write_json(run / "evidence_checksums.json", hashes)
    archive = run.with_name(run.name + f"-{uuid.uuid4().hex[:6]}.zip")
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as zipped:
        for name in (*hashes, "evidence_checksums.json"):
            zipped.write(run / name, arcname=f"{run.name}/{name}")
    write_json(archive.with_suffix(".json"), dict(archive=archive.name, sha256=sha256(archive)))
    return archive


def validate_artifacts(run):
    """Recheck returned artifacts; manual/scientific/visual approval remains explicit."""
    run = Path(run)
    report = dict(status="failed", manual_review="pending; no final acceptance implied")
    try:
        summary = json.loads((run / "execution_summary.json").read_text(encoding="utf-8"))
        if summary["status"] != "executed_review_pending":
            raise ValueError(f"Execution did not complete: {summary['status']}")
        for name, digest in json.loads((run / "evidence_checksums.json").read_text()).items():
            path = (run / name).resolve()
            if not path.is_relative_to(run.resolve()) or not path.is_file() or sha256(path) != digest:
                raise ValueError(f"Returned evidence checksum mismatch: {name}")
        notebook = run / "Group16_Final.ipynb"
        if sha256(notebook) != summary["notebook_sha256"]:
            raise ValueError("Executed notebook changed after execution")
        report["outputs"] = inspect_outputs(notebook)
        from export_notebook_pdf import inspect_pdf
        report["pdf"] = inspect_pdf(run / "pdf/Group16_Final.pdf", expect_raster=True)
        if report["pdf"]["problems"]:
            raise ValueError(f"PDF QA failed: {report['pdf']['problems']}")
        if summary["environment"]["status"] != "passed" or summary["environment"]["gpu"]["compute_capability"] != "7.5":
            raise ValueError("GPU manifest does not certify T4 preflight")
        report["source_sha"] = summary["source_sha"]
        report["candidate"] = summary["candidate"]
        report["status"] = "automatic_checks_passed_manual_review_pending"
    except Exception as error:
        report["error"] = str(error)
    output = run / f"artifact_validation-{uuid.uuid4().hex[:8]}.json"
    write_json(output, report)
    return report


def execute(args):
    import nbformat as nbf
    from nbclient import NotebookClient
    run = new_run(args.evidence_root)
    print(f"Evidence directory: {run}", flush=True)
    report = dict(status="failed", candidate=not args.frozen, source_sha=args.source_sha,
                  invocation=vars(args).copy(), started_utc=datetime.now(timezone.utc).isoformat())
    report["invocation"] = {k: str(v) if isinstance(v, Path) else v for k, v in report["invocation"].items()}
    notebook = None
    try:
        # Sources live next to the evidence, not inside its ZIP (avoid dataset/build payloads).
        source = run.parent / (run.name + "-source")
        if args.source_mode == "archive":
            manifest = verify_archive(args.source_archive, source, args.source_sha, args.archive_sha256)
            report["source_archive_sha256"] = sha256(args.source_archive)
            write_json(run / "source_manifest.json", manifest)
            comparison = manifest.get("freeze_comparison", {"status": "comparison_unavailable", "src_build_equivalent": False})
        else:
            published(source, args.repo_url, args.source_sha)
            from package_notebook_acceptance import command
            command(source, "fetch", "--depth", "1", args.repo_url, FREEZE_SHA)
            comparison = compare_freeze(source, args.source_sha)
        report["freeze_comparison"] = comparison
        write_json(run / "freeze_comparison.json", comparison)
        if args.frozen and not comparison["src_build_equivalent"]:
            raise ValueError("Execution source differs from tested freeze scope or comparison is unavailable; use candidate mode and obtain new T4 verification")
        (run / "source_sha.txt").write_text(args.source_sha + "\n", encoding="utf-8")
        report["environment"] = environment(run)
        # Use the established Drive loader and manifest verifier.
        from notebook import final_notebook as fn
        data_path, _ = fn.fetch_dataset(args.dataset, run.parent / "dataset_drive")
        dataset(data_path, run)
        original = args.notebook or source / "Group16_Final.ipynb"
        shutil.copy2(original, run / "Group16_Final.input.ipynb")
        notebook = prepare_notebook(original, source, args.source_sha, run,
                                    Path(__file__).parent, candidate=not args.frozen)
        write_json(run / "runtime_overlay.json", dict(notebook.metadata["group16_acceptance"]))
        # Inject only the dataset path into the child process, avoiding ambient benchmark caches.
        import os
        old_dataset = os.environ.get("GROUP16_DATASET_DIR")
        os.environ["GROUP16_DATASET_DIR"] = str(data_path.resolve())
        try:
            with (run / "execution.log").open("w", encoding="utf-8") as log:
                def before(cell, cell_index, **kwargs):
                    log.write(f"START cell={cell_index + 1} id={cell.get('id')}\n")
                    log.flush()
                    print(f"Executing report cell {cell_index + 1}: {cell.get('id')}", flush=True)
                def after(cell, cell_index, **kwargs):
                    log.write(f"END cell={cell_index + 1} count={cell.get('execution_count')}\n")
                    log.flush()
                NotebookClient(notebook, timeout=args.cell_timeout, kernel_name=args.kernel,
                    allow_errors=False, resources={"metadata": {"path": str(source)}},
                    on_cell_execute=before, on_cell_executed=after).execute()
        finally:
            if old_dataset is None:
                os.environ.pop("GROUP16_DATASET_DIR", None)
            else:
                os.environ["GROUP16_DATASET_DIR"] = old_dataset
        nbf.write(notebook, run / "Group16_Final.ipynb")
        report["outputs"] = inspect_outputs(run / "Group16_Final.ipynb")
        binary = source / "build/stitch"
        report["benchmark"] = benchmark_evidence(run / "benchmark", binary)
        verify_tree(source, args.source_sha)
        build_log = source / "build/build.log"
        shutil.copy2(build_log, run / "build.log")
        report["pdf"] = export(run / "Group16_Final.ipynb", run / "pdf")
        if report["pdf"]["status"] != "exported_visual_review_pending":
            raise ValueError("PDF automatic QA failed; see pdf/pdf_export.json")
        report["status"] = "executed_review_pending"
    except Exception as error:
        report["error"] = str(error)
        (run / "failure.log").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        if notebook is not None:
            nbf.write(notebook, run / "Group16_Final.ipynb")
            report["notebook_sha256"] = sha256(run / "Group16_Final.ipynb")
            write_json(run / "cell_errors.json", [dict(cell=i, id=c.get("id"), error=dict(o))
                for i, c in enumerate(notebook.cells, 1) if c.cell_type == "code"
                for o in c.outputs if o.output_type == "error"])
        write_json(run / "execution_summary.json", report)
        write_json(run / "review_required.json", dict(source_freeze="pending" if not args.frozen else "declared; verify T02 logs",
            numerical_claims="pending: reconcile all prose with outputs; see N01-N07 audit",
            gallery="pending: inspect seams and course-provided sample",
            pdf_visual="pending: render and inspect every page", final_acceptance="NOT CERTIFIED"))
        # Preserve build failure logs as well as successful build output.
        source_path = run.parent / (run.name + "-source")
        if source_path.exists():
            apod = source_path / "docs/report/p10-t05-v5-apod.md"
            if apod.is_file():
                try:
                    write_json(run / "numerical_audit.json", dict(published_table=reconcile_apod(apod),
                        raw_v5_verified=False, prose_reconciliation="manual review pending; see P11 audit N01-N07"))
                except Exception as error:
                    write_json(run / "numerical_audit.json", dict(error=str(error), status="review required"))
            for path in (source_path / "build").rglob("*.log"):
                relative = path.relative_to(source_path)
                target = run / "source_logs" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
        archive = bundle(run)
        print(f"Status: {report['status']}\nEvidence ZIP: {archive}", flush=True)
    return run, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mode", choices=("archive", "published"))
    parser.add_argument("--source-sha")
    parser.add_argument("--validate-run", type=Path)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--archive-sha256")
    parser.add_argument("--repo-url", default="https://github.com/nh-atuan/panorama-stitching.git")
    parser.add_argument("--dataset", type=Path, default=Path("/content/group16-dataset"))
    parser.add_argument("--notebook", type=Path)
    parser.add_argument("--evidence-root", type=Path, default=Path("results/p11-t06"))
    parser.add_argument("--frozen", action="store_true", help="only after T02 confirms this exact SHA")
    parser.add_argument("--kernel", default="python3")
    parser.add_argument("--cell-timeout", type=int, default=3600)
    args = parser.parse_args()
    if args.validate_run:
        report = validate_artifacts(args.validate_run)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(report["status"] == "failed")
    if not args.source_mode or not args.source_sha:
        parser.error("--source-mode and --source-sha are required for execution")
    if args.source_mode == "archive" and (not args.source_archive or not args.archive_sha256):
        parser.error("archive mode requires --source-archive and --archive-sha256")
    _, report = execute(args)
    return int(report["status"] != "executed_review_pending")


if __name__ == "__main__":
    raise SystemExit(main())
