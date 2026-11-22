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
    "Thông tin nhóm", "Giới thiệu", "Phương pháp đã chọn", "V0 tuần tự",
    "V1 CUDA cơ bản", "Các phiên bản tối ưu", "So sánh tổng hợp", "Kết quả ghép ảnh",
    "Kết luận", "Tài liệu tham khảo",
)
ANCHORS = ("team-information", "introduction", "chosen-methods", "v0-sequential",
           "v1-basic-cuda", "optimized-versions", "final-comparison", "results-gallery",
           "conclusion", "references")
CODE_ROLES = ("runtime-setup", "thanh-producer", "method-settings", "thanh-v0-tables",
              "thanh-v1-tables", "thanh-v4-tables", "thanh-v5-tables",
              "thanh-comparison-tables", "thanh-charts", "thanh-gallery")


def section_structure(cells):
    """Validate numbered sections by stable anchors, independently of display language."""
    found, problems = [], []
    roles = {c.get("id") for c in cells if c.get("cell_type") == "code"}
    for index, cell in enumerate(cells, 1):
        if cell.get("cell_type") != "markdown":
            continue
        source = "".join(cell.get("source", ""))
        headings = list(re.finditer(r"^## (\d+)\. (.+)$", source, re.M))
        for heading in headings:
            number, title = int(heading[1]), heading[2].strip()
            anchors = re.findall(r'<a\s+(?:id|name)=[\'"]([^\'"]+)[\'"]\s*>', source)
            if not 1 <= number <= 10 or anchors != [ANCHORS[number - 1]]:
                problems.append(f"Cell {index}: missing/wrong section anchor for section {number}")
            if len(source[heading.end():].strip()) < 20:
                problems.append(f"Cell {index}: section {number} has no substantive body")
            found.append((number, title, index))
    if [n for n, _, _ in found] != list(range(1, 11)):
        problems.append(f"Missing, duplicated or unordered sections: {[n for n, _, _ in found]}")
    missing = sorted(set(CODE_ROLES) - roles)
    if missing:
        problems.append(f"Missing essential executable cell roles: {missing}")
    return found, problems
PIN_FILES = (
    *(f"src/v{v}/v{v}_pipeline.{ 'cpp' if v == 0 else 'cu'}" for v in range(6)),
    "src/v5/v5_image_branch.h", "src/v5/v5_image_branch.cu", "src/main.cu",
    "src/versions.h", "scripts/build.py", "scripts/notebook/final_notebook.py",
    "scripts/notebook/midterm_notebook.py", "scripts/dataset/prepare_dataset.py",
    "scripts/run_benchmark.py", "scripts/fetch_and_prepare_dataset.py",
)
FREEZE_SHA = "f2837a85b770e6c8bb2eba1bb6de7aee7fa23eb7"


def compare_freeze(root, revision, freeze=FREEZE_SHA):
    """Compare the tested production scope, keeping tooling/docs changes separate."""
    result = dict(source_sha=revision, freeze_sha=freeze, src_build_equivalent=False)
    if any(git(root, "cat-file", "-e", f"{ref}^{{commit}}")[0] for ref in (revision, freeze)):
        return dict(result, status="comparison_unavailable")
    status, paths = git(root, "diff", "--name-only", freeze, revision, "--", "src", "scripts/build.py")
    if status:
        return dict(result, status="comparison_unavailable")
    result["production_changes"] = paths.splitlines()
    result["src_build_equivalent"] = not paths
    _, changes = git(root, "diff", "--name-only", "--no-renames", freeze, revision)
    changed = changes.splitlines()
    result["tooling_changes"] = [p for p in changed if p.startswith(("scripts/", "tests/")) and p != "scripts/build.py"]
    result["documentation_changes"] = [p for p in changed if p.startswith("docs/") or p.endswith((".ipynb", ".md"))]
    result["status"] = "same_production_scope" if not paths else "new_production_verification_required"
    return result


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
    headings, structure_errors = section_structure(data["cells"])
    for error in structure_errors:
        add("BLOCKER", "SECTION_ORDER", error)
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
        _, helper = git(root, "show", f"{pin}:scripts/notebook/final_notebook.py")
        candidates = constants(helper).get("CANDIDATE_VERSIONS", ())
        if 5 not in candidates:
            add("MAJOR", "V5_NOT_PROBED", f"Pinned helper candidates: {candidates}")
    if frozen_source is None:
        add("BLOCKER", "FREEZE_UNCONFIRMED", "P11-T02 must supply a verified frozen SHA.")
    elif pin != frozen_source:
        comparison = compare_freeze(root, pin, frozen_source)
        if not comparison["src_build_equivalent"]:
            add("BLOCKER", "FREEZE_MISMATCH", f"Pin/freeze production scope not verified: {comparison}")
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
