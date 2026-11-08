#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none
"""Build and verify the production V2 CLI on T4, preserving all acceptance evidence."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

from dataset_common import SIZES
from fetch_and_prepare_dataset import CHOSEN_PAIRS
from homography_common import as_matrix, project
from homography_error import parse_estimate
from package_s6_verification import EXTENSIONS, PREFIXES, git_output
from profiling_common import capture, inspect_environment, reject_stub, write_json
from run_benchmark import parse_version_csv, read_error_code, sha256, version_columns


ROOT = Path(__file__).resolve().parents[1]
RUNS = 5
VERSIONS = (0, 1, 2)
PAIRWISE = ((0, 1), (0, 2), (1, 2))
DRIFT_PX = 0.1
RGB_TOLERANCE = 1
V2_HEADER = version_columns(2)
CANVAS = re.compile(r"^\[debug\] S6 canvas=(\d+)x(\d+) offset=\((-?\d+),\s*(-?\d+)\)$", re.MULTILINE)
SANITIZER = ("compute-sanitizer", "--tool", "memcheck", "--leak-check", "full", "--error-exitcode", "99")


def source_snapshot():
    hashes = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for directory in PREFIXES for path in sorted((ROOT / directory).rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() in EXTENSIONS
    }
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    packaged = ROOT / "source_manifest.json"
    if packaged.is_file():
        manifest = json.loads(packaged.read_text(encoding="utf-8"))
        if manifest["files"] != hashes or manifest["snapshot_sha256"] != digest:
            raise ValueError("Packaged source differs from source_manifest.json")
        return manifest
    return {"git_commit": git_output("rev-parse", "HEAD"),
            "git_branch": git_output("branch", "--show-current"),
            "source_status": git_output("status", "--porcelain", "--", *PREFIXES),
            "snapshot_sha256": digest, "files": hashes}


def official_inputs(dataset):
    manifest = dataset / "manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    by_name = {row["file"]: row for row in records}
    if len(records) != 24 or len(by_name) != 24:
        raise ValueError("Official manifest must describe 24 distinct images")
    cases = []
    for site, pair in CHOSEN_PAIRS:
        for size, width, height in SIZES:
            paths = []
            for side in ("left", "right"):
                name = f"{site}/{size}_{side}.jpg"
                row = by_name[name]
                path = dataset / name
                if ((row["site"], row["pair"], row["side"]) != (site, pair, side) or
                        (int(row["width"]), int(row["height"])) != (width, height) or
                        sha256(path) != row["sha256"]):
                    raise ValueError(f"Image does not match the official manifest: {name}")
                with Image.open(path) as image:
                    if image.size != (width, height):
                        raise ValueError(f"Unexpected decoded image size: {name}: {image.size}")
                paths.append(path)
            cases.append((site, pair, size, width, height, *paths))
    return cases


def parse_v2_csv(text, runs):
    if runs < 1:
        raise ValueError("runs must be positive")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0] != V2_HEADER:
        raise ValueError(f"Unexpected V2 CSV header: {rows[0] if rows else 'empty stdout'}")
    labels = [str(i) for i in range(1, runs + 1)] + ["Average", "Minimum"]
    if any(len(row) != len(V2_HEADER) for row in rows[1:]) or [row[0] for row in rows[1:]] != labels:
        raise ValueError("V2 CSV has wrong row labels or column count")
    records = [dict(zip(V2_HEADER[1:], map(float, row[1:]))) for row in rows[1:]]
    if any(not math.isfinite(value) or value < 0 for row in records for value in row.values()):
        raise ValueError("V2 CSV contains invalid timing values")
    measured = records[:runs]
    for row in measured:
        spans = (row["H2D_ms"], row["D2H_ms"], row["Total_Kernel_ms"])
        if min(spans) <= 0 or sum(spans) > row["Total_ms"] + 0.1:
            raise ValueError("V2 transfer/kernel timings are missing or exceed end-to-end")
    for key in V2_HEADER[1:]:
        samples = [row[key] for row in measured]
        if not math.isclose(records[-2][key], math.fsum(samples) / runs, abs_tol=1e-6, rel_tol=1e-7):
            raise ValueError(f"Incorrect Average for {key}")
        if not math.isclose(records[-1][key], min(samples), abs_tol=1e-6, rel_tol=1e-7):
            raise ValueError(f"Incorrect Minimum for {key}")
    return {"average": records[-2], "minimum": records[-1]}


def projection_drift(first, second, width, height):
    xs, ys = np.meshgrid(np.linspace(0, width - 1, 20), np.linspace(0, height - 1, 20))
    projected = []
    for values in (first, second):
        x, y, w = project(as_matrix(values), xs, ys)
        if not (np.all(w > 0) or np.all(w < 0)) or not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("Invalid projection on the B->A comparison grid")
        projected.append((x, y))
    (xa, ya), (xb, yb) = projected
    return float(np.max(np.hypot(xa - xb, ya - yb)))


def rgb_delta(first, second):
    maximum = 0
    with Image.open(first) as a, Image.open(second) as b:
        if a.mode != "RGB" or b.mode != "RGB" or a.size != b.size:
            raise ValueError("Panorama PNGs must be RGB with identical dimensions")
        for y in range(0, a.height, 128):
            region = (0, y, a.width, min(y + 128, a.height))
            left = np.asarray(a.crop(region), dtype=np.int16)
            right = np.asarray(b.crop(region), dtype=np.int16)
            maximum = max(maximum, int(np.abs(left - right).max()))
    return maximum


def stitch_command(stitch, left, right, output, version, runs=None, debug=False):
    command = [stitch, left, right, output, "--version", str(version)]
    if runs is not None:
        command.extend(("--runs", str(runs)))
    if debug:
        command.append("--debug")
    return command


def run_version(stitch, left, right, output, version, log):
    result, stdout, stderr = capture(stitch_command(stitch, left, right, output, version, RUNS, True), log)
    rc = result["returncode"]
    row = {"returncode": rc, "status": "Success" if rc == 0 else read_error_code(stderr),
           "error": next((line for line in stderr.splitlines() if line.startswith("Error: [")), ""),
           "log": log.name, "validation_errors": []}
    if rc != 0:
        if rc is None or rc < 0 or stdout.strip() or output.exists():
            row["validation_errors"].append("Expected a normal error exit without timing rows or output")
        return row
    if reject_stub(stderr):
        row["validation_errors"].append("CLI reported an infrastructure scaffold")
    try:
        row["timing"] = parse_v2_csv(stdout, RUNS) if version == 2 else parse_version_csv(stdout, RUNS, version)
    except ValueError as error:
        row["validation_errors"].append(str(error))
    try:
        row["H"] = parse_estimate(stderr).ravel().tolist()
        row["config"] = next(line for line in stderr.splitlines() if line.startswith("[debug] config: "))
        geometry = CANVAS.findall(stderr)
        if len(geometry) != 1:
            raise ValueError("Expected one S6 canvas diagnostic")
        row["canvas"] = list(map(int, geometry[0]))
        with Image.open(output) as image:
            if image.format != "PNG" or image.mode != "RGB" or list(image.size) != row["canvas"][:2]:
                raise ValueError("D2H PNG format or dimensions disagree with S6")
            image.load()
        row["panorama_sha256"] = sha256(output)
    except (ValueError, OSError, StopIteration) as error:
        row["validation_errors"].append(str(error) or "Missing configuration diagnostic")
    return row


def run_case(stitch, case, out):
    site, pair, size, width, height, left, right = case
    case_id = f"{site}_{size}"
    folder = out / "panoramas" / site / size
    folder.mkdir(parents=True)
    outputs = [folder / f"v{version}.png" for version in VERSIONS]
    rows = [run_version(stitch, left, right, outputs[version], version,
                        out / "logs" / f"{case_id}_v{version}") for version in VERSIONS]
    expected = "NumericalFailure" if site == "challenge" and size != "small" else "Success"
    errors = [f"V{version}: {error}" for version, row in enumerate(rows) for error in row["validation_errors"]]
    statuses = [row["status"] for row in rows]
    if any(status != expected for status in statuses):
        errors.append(f"Expected {expected}, got {statuses}")
    result = {"site": site, "pair": pair, "size": size, "expected": expected, "versions": rows, "errors": errors,
              "matches_v0_v1_status": statuses[0] == statuses[1] == statuses[2]}
    if all(status == "Success" for status in statuses) and all("panorama_sha256" in row for row in rows):
        try:
            if len({row["config"] for row in rows}) != 1:
                raise ValueError("Config differs between versions")
            result["h_drift_px"] = {f"V{a}/V{b}": projection_drift(rows[a]["H"], rows[b]["H"], width, height)
                                    for a, b in PAIRWISE}
            if max(result["h_drift_px"].values()) >= DRIFT_PX:
                raise ValueError("S5 homography drift exceeds 0.1 px")
            if any(row["canvas"] != rows[0]["canvas"] for row in rows[1:]):
                raise ValueError("S6 canvas dimensions or offset differ")
            canvas_width, canvas_height = rows[2]["canvas"][:2]
            result["expanded_canvas"] = canvas_width * canvas_height > width * height
            result["rgb_delta"] = {f"V{a}/V{b}": rgb_delta(outputs[a], outputs[b]) for a, b in PAIRWISE}
            if max(result["rgb_delta"].values()) > RGB_TOLERANCE:
                raise ValueError("RGB exceeds 1 level per channel after H and canvas checks")
        except (ValueError, OSError) as error:
            errors.append(str(error))
    print(f"{case_id}: {'/'.join(statuses)} {'; '.join(errors) if errors else 'PASS'}", flush=True)
    write_json(out / "cases" / f"{case_id}.json", result)
    return result


def repeated_features(path):
    # Every interior patch has identical copies. Equal best and second Hamming distances fail the ratio test.
    image = Image.new("RGB", (400, 400), (16, 16, 16))
    draw = ImageDraw.Draw(image)
    for y in (80, 180, 280):
        for x in (80, 180, 280):
            draw.rectangle((x, y, x + 20, y + 24), fill=(230, 230, 230))
            draw.rectangle((x + 14, y + 17, x + 33, y + 28), fill=(120, 120, 120))
    image.save(path)


def cli_checks(stitch, left, right, out):
    corrupt, repeated = out / "corrupt.jpg", out / "repeated_features.png"
    corrupt.write_bytes(b"Invalid image fixture\n")
    repeated_features(repeated)
    fixtures = (
        ("missing", out / "missing.jpg", right, 2, 1, "InputNotFound"),
        ("unreadable", corrupt, right, 2, 1, "ImageReadFailed"),
        ("runs_zero", left, right, 2, 0, "InvalidArgument"),
        ("version_99", left, right, 99, 1, "UnsupportedVersion"),
        ("zero_match", repeated, repeated, 2, 1, "InsufficientMatches"),
        ("default_runs_quiet", left, right, 2, None, "Success"),
    )
    checks = []
    for label, a, b, version, runs, expected in fixtures:
        image = out / f"cli_{label}.png"
        record, stdout, stderr = capture(stitch_command(stitch, a, b, image, version, runs),
                                         out / "logs" / f"cli_{label}")
        rc = record["returncode"]
        status = "Success" if rc == 0 else read_error_code(stderr)
        error = ""
        try:
            if expected == "Success":
                if rc != 0 or stderr.strip() or not image.is_file():
                    raise ValueError("Expected successful quiet execution and an output PNG")
                parse_v2_csv(stdout, RUNS)
            elif status != expected or rc is None or rc <= 0 or stdout.strip() or image.exists():
                raise ValueError(f"Expected a normal {expected} error exit without CSV or output")
        except ValueError as failure:
            error = str(failure)
        checks.append({"case": label, "expected": expected, "status": status, "returncode": rc, "error": error})
    return checks


def memcheck_result(record, stdout, stderr):
    lines = (stdout + "\n" + stderr).splitlines()
    summaries = [line for line in lines if "ERROR SUMMARY:" in line or "LEAK SUMMARY:" in line]
    errors = re.findall(r"ERROR SUMMARY:\s*([\d,]+) errors?", "\n".join(summaries))
    leaks = re.findall(r"LEAK SUMMARY:\s*([\d,]+) bytes leaked in ([\d,]+) allocations?", "\n".join(summaries))
    return {"returncode": record["returncode"], "lines": summaries,
            "passed": record["returncode"] == 0 and bool(errors) and bool(leaks) and
            all(int(value.replace(",", "")) == 0 for value in errors) and
            all(int(value.replace(",", "")) == 0 for pair in leaks for value in pair)}


def run_evidence(dataset, synthetic, out, evidence):
    evidence["environment"] = inspect_environment(require_t4=True)
    evidence["source"] = source_snapshot()
    if not re.fullmatch(r"[a-f0-9]{40}", evidence["source"]["git_commit"]):
        raise ValueError("A verifiable source Git base commit is required")
    for name in ("v2_pipeline.h", "v2_pipeline.cu"):
        if not (ROOT / "src/v2" / name).is_file():
            raise ValueError("Missing production V2 pipeline from P7-T02")
    logs = out / "logs"
    for name, command in (("nvcc", ["nvcc", "--version"]),
                          ("sanitizer_version", ["compute-sanitizer", "--version"])):
        record, stdout, stderr = capture(command, logs / name)
        if record["returncode"] != 0:
            raise ValueError(f"Cannot identify {name}: {stderr}")
        evidence["environment"][name] = (stdout + stderr).strip()
    evidence["environment"]["colab_release_tag"] = os.environ.get("COLAB_RELEASE_TAG")
    cases = official_inputs(dataset)
    evidence["manifest_sha256"] = sha256(dataset / "manifest.csv")
    shutil.copy2(dataset / "manifest.csv", out / "dataset_manifest.csv")
    synthetic_hashes = {}
    for kind in ("translation", "projective"):
        for size, _, _ in SIZES:
            for suffix in ("left.png", "right.png", "truth.json"):
                name = f"{kind}/{size}_{suffix}"
                synthetic_hashes[name] = sha256(synthetic / name)
    evidence["synthetic_sha256"] = synthetic_hashes

    build = [sys.executable, "scripts/build.py", "--compiler", "nvcc", "--require-t4"]
    result, _, _ = capture(build, logs / "build", timeout=1800)
    if result["returncode"] != 0:
        raise ValueError("Production build failed; see logs/build.stderr")
    stitch = ROOT / "build/stitch"
    evidence["stitch_sha256"] = sha256(stitch)
    left, right = cases[0][-2:]
    smoke = run_version(stitch, left, right, out / "probe.png", 2, logs / "v2_probe")
    evidence["probe"] = smoke
    if smoke["status"] != "Success":
        raise ValueError(f"Production CLI --version 2 preflight: {smoke['status']}; see logs/v2_probe.stderr")
    # Preserve schema errors while still collecting the full matrix and other independent gates.
    evidence["cli"] = cli_checks(stitch, left, right, out)
    evidence["cases"] = []
    for case in cases:
        evidence["cases"].append(run_case(stitch, case, out))
    runner = [sys.executable, "tests/run_tests.py", "--compiler", "nvcc", "--require-t4",
              "--require-v2-pipeline", "--v2-synthetic-dir", synthetic]
    regression, stdout, _ = capture(runner, logs / "regression", timeout=3600)
    evidence["regression"] = {"returncode": regression["returncode"],
                              "summaries": [line for line in stdout.splitlines() if line.startswith("PASS")]}
    binary = ROOT / "build/tests_gpu/gpu_v2_pipeline"
    commands = {"suite": [binary, "--require-v2-pipeline"],
                "cli": stitch_command(stitch, left, right, out / "memcheck_site1_small.png", 2, 1, True)}
    evidence["memcheck"] = {}
    for label, command in commands.items():
        record, stdout, stderr = capture([*SANITIZER, *command], logs / f"memcheck_{label}", timeout=1800)
        evidence["memcheck"][label] = memcheck_result(record, stdout, stderr)
    evidence["gates"] = {
        "production_cli": not smoke["validation_errors"],
        "real_matrix": len(evidence["cases"]) == 12 and not any(case["errors"] for case in evidence["cases"]),
        "dynamic_d2h": any(case["site"] != "challenge" and case.get("expanded_canvas") and not case["errors"]
                           for case in evidence["cases"]),
        "cli_boundaries": not any(check["error"] for check in evidence["cli"]),
        "regression": regression["returncode"] == 0 and
                      any(line.startswith("PASS GPU V2 pipeline (production pipeline):")
                          for line in evidence["regression"]["summaries"]),
        "memcheck": all(item["passed"] for item in evidence["memcheck"].values()),
        "source_unchanged": evidence["source"]["snapshot_sha256"] == source_snapshot()["snapshot_sha256"],
    }


def render_report(evidence):
    source, env = evidence.get("source", {}), evidence.get("environment", {})
    verdict = "Đạt các cổng tự động" if evidence.get("passed") else "Chưa đạt nghiệm thu"
    lines = ["<!-- Authors: Le Ha Thanh Chuong (23120195). External source: none. -->", "",
             "# P7-T04 V2 Verification", "", verdict, "",
             f"- Thời điểm bắt đầu UTC `{evidence['started_utc']}`",
             f"- Git base `{source.get('git_commit', 'chưa xác minh')}`",
             f"- Source SHA-256 `{source.get('snapshot_sha256', 'chưa xác minh')}`",
             f"- GPU và driver `{env.get('gpu', 'chưa xác minh')}`",
             f"- Môi trường `{env.get('host', 'chưa xác minh')}`",
             f"- Colab release `{env.get('colab_release_tag') or 'không có biến môi trường'}`",
             f"- Stitch SHA-256 `{evidence.get('stitch_sha256', 'chưa build')}`",
             f"- Dataset manifest SHA-256 `{evidence.get('manifest_sha256', 'chưa xác minh')}`", ""]
    if env.get("nvcc"):
        lines.extend(("```text", env["nvcc"], "```", ""))
    if evidence.get("error"):
        lines.extend((f"Lỗi khi chạy harness. {evidence['error']}", ""))
    lines.extend(("## Real Dataset Matrix", "",
                  "| Cấu hình | Status V0 / V1 / V2 | Canvas V0 / V1 / V2 | Offset V0 / V1 / V2 | Max RGB | Total trung bình V0 / V1 / V2 (ms) |",
                  "|---|---|---|---|---:|---|"))
    observed = {(case["site"], case["size"]): case for case in evidence.get("cases", [])}
    for site, _ in CHOSEN_PAIRS:
        for size, _, _ in SIZES:
            case = observed.get((site, size))
            if case is None:
                lines.append(f"| {site}/{size} | Chưa chạy | — | — | — | — |")
                continue
            rows = case["versions"]
            status = " / ".join(row["status"] for row in rows)
            canvas = " / ".join(f"{row['canvas'][0]}×{row['canvas'][1]}" if "canvas" in row else "—" for row in rows)
            offset = " / ".join(f"({row['canvas'][2]},{row['canvas'][3]})" if "canvas" in row else "—" for row in rows)
            latency = " / ".join(f"{row['timing']['average']['Total_ms']:.6f}" if "timing" in row else "—" for row in rows)
            delta = max(case["rgb_delta"].values()) if "rgb_delta" in case else "—"
            lines.append(f"| {site}/{size} | {status} | {canvas} | {offset} | {delta} | {latency} |")
    lines.extend(("", "## Challenge Pair", "",
                  "Baseline P6 của `de-challenge1` ghi nhận ảnh small bị lệch và `NumericalFailure` ở medium/large."))
    for size, _, _ in SIZES:
        case = observed.get(("challenge", size))
        if case:
            statuses = "/".join(row["status"] for row in case["versions"])
            verdict = "cùng trạng thái" if case["matches_v0_v1_status"] else "khác trạng thái"
            lines.append(f"- `{size}` — {statuses}, {verdict} giữa V0, V1 và V2.")
    lines.extend(("", "Đối chiếu trực quan các panorama challenge có trong `panoramas/challenge/` và gallery của notebook.",
                  "", "## CLI, Regression and Memcheck", ""))
    for label, passed in evidence.get("gates", {}).items():
        lines.append(f"- `{label}` — {'PASS' if passed else 'FAIL'}")
    for check in evidence.get("cli", []):
        state = check["error"] or "PASS"
        lines.append(f"- `{check['case']}` — {check['status']}, exit `{check['returncode']}`, {state}")
    for label, result in evidence.get("memcheck", {}).items():
        lines.extend(("", f"### {label} (exit `{result['returncode']}`)", "", "```text", *result["lines"], "```"))
    lines.extend(("", "Log gốc nằm trong `logs/`. Dữ liệu chi tiết của từng cấu hình nằm trong `cases/`.", ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--synthetic-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="new evidence directory")
    args = parser.parse_args()
    dataset, synthetic, out = (path.resolve() for path in (args.dataset, args.synthetic_dir, args.out))
    out.mkdir(parents=True, exist_ok=False)
    (out / "cases").mkdir()
    os.chdir(ROOT)
    evidence = {"started_utc": datetime.now(timezone.utc).isoformat(), "passed": False}
    try:
        run_evidence(dataset, synthetic, out, evidence)
        evidence["passed"] = all(evidence["gates"].values())
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        evidence["error"] = str(error)
        print(f"Acceptance stopped: {error}", file=sys.stderr)
    write_json(out / "verification_summary.json", evidence)
    (out / "p7-v2-verification.md").write_text(render_report(evidence), encoding="utf-8")
    print(f"Evidence: {out}\nResult: {'PASS' if evidence['passed'] else 'FAIL'}")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
