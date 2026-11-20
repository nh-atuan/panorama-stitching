#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Read-only notebook preflight. Static checks do not certify GPU execution or claims."""

import argparse
import ast
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
from urllib.parse import unquote, urlsplit

import run_benchmark as rb

SECTIONS = (
    "Team Information", "Introduction", "Chosen Methods", "V0 Sequential",
    "V1 Basic CUDA", "Optimized Versions", "Final Comparison", "Results Gallery",
    "Conclusion", "References",
)
PIN_FILES = (
    *(f"src/v{v}/v{v}_pipeline.{ 'cpp' if v == 0 else 'cu'}" for v in range(6)),
    "src/v5/v5_image_branch.h", "src/v5/v5_image_branch.cu", "src/main.cu",
    "src/versions.h", "scripts/build.py", "scripts/final_notebook.py",
    "scripts/run_benchmark.py", "scripts/prepare_dataset.py",
)


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    return result.returncode, result.stdout.strip()


def constants(source):
    """Read literal top-level assignments without executing notebook code."""
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return values


def local_links(source):
    """Inventory Markdown links; fragments and remote URLs are not filesystem paths."""
    for target in re.findall(r"\]\(([^\n)]+)\)", source):
        target = target.strip().strip("<>")
        parsed = urlsplit(target)
        if not parsed.scheme and parsed.path:
            yield unquote(parsed.path)


def audit(notebook, root, frozen_source=None):
    notebook, root = Path(notebook), Path(root)
    data = json.loads(notebook.read_text(encoding="utf-8"))
    findings = []

    def add(severity, code, detail, cell=None):
        findings.append(dict(severity=severity, code=code, cell=cell, detail=detail))

    if data.get("nbformat") != 4 or not isinstance(data.get("cells"), list):
        raise ValueError("Expected nbformat 4 with a cells array")
    try:
        import nbformat
    except ImportError:
        add("MAJOR", "NBFORMAT_UNAVAILABLE", "Install nbformat to perform schema validation.")
    else:
        # nbformat may normalize missing IDs; validate a disposable copy only.
        nbformat.validate(nbformat.from_dict(json.loads(json.dumps(data))))
    config, headings, ids, code_count, unexecuted = {}, [], set(), 0, []
    for index, cell in enumerate(data["cells"], 1):
        cell_id = cell.get("id")
        if not cell_id:
            add("MINOR", "MISSING_CELL_ID", "nbformat 4.5 requires a stable cell id.", index)
        elif cell_id in ids:
            add("MAJOR", "DUPLICATE_CELL_ID", cell_id, index)
        ids.add(cell_id)
        source = "".join(cell.get("source", []))
        for match in re.finditer(r"^## (\d+)\. (.+)$", source, re.M):
            headings.append((int(match[1]), match[2].strip(), index))
        if cell.get("cell_type") == "code":
            code_count += 1
            try:
                config.update(constants(source))
            except SyntaxError as error:
                add("BLOCKER", "PYTHON_SYNTAX", f"line {error.lineno}: {error.msg}", index)
            if cell.get("execution_count") is None:
                unexecuted.append(index)
            if any(o.get("output_type") == "error" for o in cell.get("outputs", [])):
                add("BLOCKER", "SAVED_EXECUTION_ERROR", "Saved error output is present.", index)
            # Only visible producer cells need output, not imports/definitions.
            if re.search(r"\b(print|display)\(", source) and not cell.get("outputs"):
                add("BLOCKER", "MISSING_OUTPUT", "Visible output missing; execute and save on T4.", index)
        for path in local_links(source):
            if not (notebook.parent / path).is_file():
                add("MAJOR", "BROKEN_LOCAL_LINK", path, index)
        if re.search(r"(?:(?<!\w)[A-Za-z]:[\\/]|file:///|/Users/|/home/[^/\s]+/)", source):
            add("MAJOR", "LOCAL_MACHINE_PATH", "Review machine-specific absolute path.", index)
        if re.search(r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b", source):
            add("MAJOR", "PLACEHOLDER", "Unresolved marker; manual review required.", index)
    if [(n, title) for n, title, _ in headings] != list(enumerate(SECTIONS, 1)):
        add("BLOCKER", "SECTION_ORDER", f"Found headings: {headings}")
    if unexecuted:
        add("BLOCKER", "UNEXECUTED_CELLS", f"No execution count: {unexecuted}")
    pin = config.get("SOURCE_REF")
    pin_exists = bool(isinstance(pin, str) and re.fullmatch(r"[0-9a-f]{40}", pin))
    pin_exists = pin_exists and git(root, "cat-file", "-e", f"{pin}^{{commit}}")[0] == 0
    availability = {}
    if not pin_exists:
        add("BLOCKER", "INVALID_SOURCE_PIN", f"SOURCE_REF is undefined or not a local commit: {pin!r}")
    else:
        for relative in PIN_FILES:
            availability[relative] = git(root, "cat-file", "-e", f"{pin}:{relative}")[0] == 0
            if not availability[relative]:
                add("BLOCKER", "PIN_MISSING_FILE", relative)
        _, helper = git(root, "show", f"{pin}:scripts/final_notebook.py")
        candidates = constants(helper).get("CANDIDATE_VERSIONS", ())
        if 5 not in candidates:
            add("MAJOR", "V5_NOT_PROBED", f"Pinned helper candidates: {candidates}")
    if frozen_source is None:
        add("BLOCKER", "FREEZE_UNCONFIRMED", "P11-T02 must supply a verified frozen SHA.")
    elif pin != frozen_source:
        add("BLOCKER", "FREEZE_MISMATCH", f"Pin {pin} != declared freeze {frozen_source}")
    if not isinstance(config.get("TIMED_RUNS"), int) or config["TIMED_RUNS"] < 5:
        add("BLOCKER", "TIMED_RUNS", "TIMED_RUNS must be an integer >= 5.")
    for key in ("REPO_URL", "BASELINE_VERSIONS"):
        if key not in config:
            add("MAJOR", "MISSING_CONFIG", key)
    return dict(notebook=str(notebook), notebook_sha256=hashlib.sha256(notebook.read_bytes()).hexdigest(),
                head=git(root, "rev-parse", "HEAD")[1], source_pin=pin, pin_files=availability,
                sections=headings, code_cells=code_count, findings=findings,
                limits="Static audit only; no GPU execution, claim validation or PDF acceptance implied.")


def reconcile_apod(path):
    """Recompute nine-case aggregates from displayed table precision, not raw runs."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        fields = [v.strip() for v in line.strip().strip("|").split("|")]
        if len(fields) == 7 and fields[0] in {"site1", "site2", "site3"}:
            v0, v4, v5 = (float(v.replace(",", ".")) for v in fields[2:5])
            if not all(math.isfinite(v) and v > 0 for v in (v0, v4, v5)):
                raise ValueError("APOD timings must be finite and positive")
            rows.append(dict(case=f"{fields[0]}/{fields[1]}", v0=v0, v4=v4, v5=v5,
                             speedup_v4_v5=v4 / v5))
    expected = {f"site{i}/{size}" for i in (1, 2, 3) for size in ("small", "medium", "large")}
    if len(rows) != 9 or {row["case"] for row in rows} != expected:
        raise ValueError("Expected exactly nine unique standard configurations")
    ratios = [r["speedup_v4_v5"] for r in rows]
    return dict(basis="Published rounded means; raw V5 runs not verified", rows=rows,
                arithmetic_mean=statistics.mean(ratios),
                geometric_mean=math.exp(statistics.mean(math.log(r) for r in ratios)),
                ratio_of_sums=sum(r["v4"] for r in rows) / sum(r["v5"] for r in rows),
                median_configuration_speedup=statistics.median(ratios),
                median_paired_run_speedup=None)


def reconcile_pres4(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped = {}
    for row in rows:
        grouped.setdefault(row["case"], []).append(row)
    result = {}
    for case, records in grouped.items():
        pres4 = [float(r["PreS4_ms"]) for r in records]
        total = [float(r["Total_ms"]) for r in records]
        if not all(math.isfinite(x) and x > 0 for x in pres4 + total):
            raise ValueError("Pre-S4 probe timings must be finite and positive")
        result[case] = dict(runs=len(records), pres4_mean_ms=statistics.mean(pres4),
                            total_probe_mean_ms=statistics.mean(total),
                            mean_run_share=statistics.mean(p / t for p, t in zip(pres4, total)),
                            ratio_of_means=statistics.mean(pres4) / statistics.mean(total))
    return result


def check_csv(path, version, runs):
    """Delegate version-dependent schema and Average/Minimum checks to the runner."""
    return rb.parse_version_csv(Path(path).read_text(encoding="utf-8"), runs=runs, version=version)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--notebook", type=Path)
    parser.add_argument("--frozen-source")
    parser.add_argument("--apod", type=Path)
    parser.add_argument("--pres4-raw", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--version", type=int, choices=range(6), default=4)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit(args.notebook or args.root / "Group16_Final.ipynb", args.root, args.frozen_source)
    if args.apod:
        result["apod"] = reconcile_apod(args.apod)
    if args.pres4_raw:
        result["pres4_probe"] = reconcile_pres4(args.pres4_raw)
    if args.csv:
        result["csv"] = check_csv(args.csv, args.version, args.runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audit: {len(result['findings'])} findings; report: {args.output}")
    return int(any(f["severity"] in ("BLOCKER", "MAJOR") for f in result["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
