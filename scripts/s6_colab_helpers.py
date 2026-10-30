# Authors: Thanh Chuong (23120195)
# External source: none
"""Bootstrap, verification and evidence helpers embedded in the S6 Colab notebook."""

import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import uuid
import zipfile

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image as PILImage
from IPython.display import display

PROJECT = RESULTS = LOGS = DATASET = NVCC = None
ENVIRONMENT = SOURCE = DATA_HELPERS = None
STATE = {}
REAL_ROWS = []
MEMCHECK_ROWS = []
SOURCE_HASHES = {}
DATA_HASHES = {}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def show_table(rows):
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    display(frame.style.hide(axis="index").set_properties(**{"font-size": "13px"}))


def check_runtime():
    global ENVIRONMENT, NVCC
    NVCC = shutil.which("nvcc")
    if not NVCC:
        raise RuntimeError("nvcc is missing. Select a Colab GPU runtime first.")
    query = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                            "--format=csv,noheader"], capture_output=True, text=True, check=True)
    gpu = next(csv.reader(query.stdout.splitlines()))
    is_t4 = bool(re.search(r"\bT4\b", gpu[0]))
    if REQUIRE_T4 and not is_t4:
        raise RuntimeError(f"Tesla T4 required; actual GPU: {gpu[0]}")
    version = subprocess.run([NVCC, "--version"], capture_output=True, text=True, check=True).stdout
    cpu = platform.processor()
    if Path("/proc/cpuinfo").exists():
        match = re.search(r"model name\s*:\s*(.+)", Path("/proc/cpuinfo").read_text())
        if match:
            cpu = match.group(1)
    ENVIRONMENT = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(), "gpu": gpu[0].strip(),
                   "driver": gpu[1].strip(), "gpu_memory": gpu[2].strip(), "cpu": cpu,
                   "python": sys.version, "platform": platform.platform(),
                   "nvcc": version, "is_t4": is_t4, "require_t4": REQUIRE_T4}
    STATE["runtime_t4"] = is_t4
    show_table([{"Item": key, "Value": ENVIRONMENT[key]} for key in
                ("gpu", "driver", "gpu_memory", "cpu", "python", "utc")])
    print(version.strip())
    if not is_t4:
        print("LOCAL CHECK ONLY: this session cannot certify Colab T4 readiness.")
    return ENVIRONMENT


def upload_if_missing(path):
    path = Path(path)
    if path.is_file():
        return path
    from google.colab import files
    print(f"Upload {path.name}")
    uploaded = files.upload()
    if path.name not in uploaded:
        raise FileNotFoundError(f"Expected file named {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(uploaded[path.name])
    return path


def extract_selected(archive, destination, prefixes, extra=()):
    """Validate member paths before extracting only the requested payload."""
    destination = Path(destination).resolve()
    selected, seen = [], set()
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            name = entry.filename
            parts = PurePosixPath(name).parts
            if (not parts or "\\" in name or ":" in name or name.startswith("/") or
                    any(part in (".", "..") for part in parts) or
                    stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError(f"Unsafe ZIP member: {name}")
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or target == destination or target in seen:
                raise ValueError(f"Duplicate or unsafe ZIP target: {name}")
            seen.add(target)
            if not entry.is_dir() and (parts[0] in prefixes or name in extra):
                selected.append(entry)
        for entry in selected:
            target = destination / entry.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    return {entry.filename for entry in selected}


def prepare_source():
    global PROJECT, RESULTS, LOGS, SOURCE, SOURCE_HASHES, DATA_HELPERS
    if ENVIRONMENT is None:
        raise RuntimeError("Run Runtime Verification first.")
    upload_if_missing(SOURCE_ARCHIVE)
    PROJECT = CONTENT_DIR / ("group16-s6-" + uuid.uuid4().hex[:10])
    PROJECT.mkdir(parents=True)
    RESULTS = PROJECT / "results"
    LOGS = RESULTS / "logs"
    LOGS.mkdir(parents=True)
    names = extract_selected(SOURCE_ARCHIVE, PROJECT, ("src", "scripts", "tests"),
                             ("source_manifest.json",))
    SOURCE = json.loads((PROJECT / "source_manifest.json").read_text())
    if SOURCE.get("schema") != 1:
        raise ValueError("Unsupported source archive schema")
    SOURCE_HASHES = SOURCE["files"]
    if names != set(SOURCE_HASHES) | {"source_manifest.json"}:
        raise ValueError("ZIP content differs from its source manifest")
    for name, expected in SOURCE_HASHES.items():
        if sha256(PROJECT / name) != expected:
            raise ValueError(f"Source hash mismatch: {name}")
    snapshot = hashlib.sha256(json.dumps(SOURCE_HASHES, sort_keys=True).encode()).hexdigest()
    if snapshot != SOURCE["snapshot_sha256"]:
        raise ValueError("Source snapshot digest is invalid")
    if SOURCE_HASHES.get("scripts/s6_colab_helpers.py") != HELPER_SHA256:
        raise ValueError("Notebook/helper version mismatch: regenerate the notebook and source ZIP together")
    spec = importlib.util.spec_from_file_location("s6_snapshot_midterm", PROJECT / "scripts/midterm_notebook.py")
    DATA_HELPERS = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(DATA_HELPERS)
    STATE["source"] = True
    (RESULTS / "environment.json").write_text(json.dumps(ENVIRONMENT, indent=2))
    shutil.copy2(PROJECT / "source_manifest.json", RESULTS / "source_manifest.json")
    SOURCE["archive_sha256"] = sha256(SOURCE_ARCHIVE)
    show_table([{"Item": "Workspace", "Value": str(PROJECT)},
                {"Item": "Git base commit", "Value": SOURCE["git_commit"]},
                {"Item": "Branch", "Value": SOURCE["git_branch"]},
                {"Item": "Snapshot SHA-256", "Value": snapshot},
                {"Item": "Verified files", "Value": len(SOURCE_HASHES)},
                {"Item": "Source working-tree status", "Value": SOURCE["source_status"] or "clean"}])


def prepare_dataset():
    global DATASET, DATA_HASHES
    if not SUPPORT_ARCHIVE.is_file():
        try:
            if importlib.util.find_spec("gdown") is None:
                subprocess.run([sys.executable, "-m", "pip", "-q", "install", "gdown"], check=True)
            import gdown
            SUPPORT_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
            gdown.download(id=SUPPORT_DRIVE_ID, output=str(SUPPORT_ARCHIVE), quiet=False)
            if not zipfile.is_zipfile(SUPPORT_ARCHIVE):
                raise ValueError("Drive response is not a ZIP")
        except Exception as error:
            print(f"Automatic dataset download failed: {error}")
            # Do not treat a partial/HTML download as a valid local archive.
            from google.colab import files
            print(f"Upload {SUPPORT_ARCHIVE.name} from the team Drive")
            uploaded = files.upload()
            if SUPPORT_ARCHIVE.name not in uploaded:
                raise FileNotFoundError(SUPPORT_ARCHIVE.name)
            SUPPORT_ARCHIVE.write_bytes(uploaded[SUPPORT_ARCHIVE.name])
    extract_selected(SUPPORT_ARCHIVE, PROJECT, ("dataset",))
    DATASET = PROJECT / "dataset"
    verified = DATA_HELPERS.validate_dataset(DATASET)
    DATA_HASHES = {row["file"]: row["sha256"] for row in verified}
    STATE["dataset"] = True
    STATE["dataset_provenance"] = {"support_zip_sha256": sha256(SUPPORT_ARCHIVE),
                                    "manifest_sha256": sha256(DATASET / "manifest.csv"),
                                    "files": DATA_HASHES}
    show_table([{ "Pair": pair, "Resolutions": ", ".join(SIZES),
                  "Verified RGB images": sum(name.startswith(pair + "/") for name in DATA_HASHES)}
                for pair in PAIRS])
    print("Only dataset/ was extracted; archived scripts/tests were not used.")


def run_command(command, name, check=True, timeout=1800):
    command = [str(value) for value in command]
    record = {"argv": command, "cwd": str(PROJECT),
              "utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    try:
        result = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True, timeout=timeout)
        record["returncode"] = result.returncode
        (LOGS / f"{name}.stdout.log").write_text(result.stdout)
        (LOGS / f"{name}.stderr.log").write_text(result.stderr)
    except subprocess.TimeoutExpired as error:
        record["error"] = "timeout"
        (LOGS / f"{name}.command.json").write_text(json.dumps(record, indent=2))
        raise RuntimeError(f"Timeout in {name}; see {LOGS}") from error
    (LOGS / f"{name}.command.json").write_text(json.dumps(record, indent=2))
    if check and result.returncode != 0:
        tail = "\n".join((result.stdout + "\n" + result.stderr).splitlines()[-30:])
        raise RuntimeError(f"{name} failed (exit {result.returncode})\n{tail}")
    return result


def build_programs():
    STATE["build"] = False
    command = [sys.executable, "scripts/build.py", "--compiler", NVCC]
    if REQUIRE_T4:
        command.append("--require-t4")
    run_command(command, "build-stitch")
    command = [NVCC, "-arch=sm_75", "-std=c++11", "-O2", "--fmad=false",
               "-Xcompiler=-Wall,-Wextra,-Werror,-ffp-contract=off,-fno-tree-vectorize,-fno-tree-slp-vectorize",
               "-Isrc", "src/v1/v1_warp_blend.cu", "src/v0/v0_warp_blend.cpp",
               "tests/gpu/test_gpu_s6_warp_blend.cu", "build/stb_impl.o",
               "-Xlinker=--wrap=cudaMalloc", "-o", "build/test_gpu_s6"]
    run_command(command, "build-s6-test")
    STATE["build"] = True
    STATE["binaries"] = {name: sha256(PROJECT / "build" / name) for name in ("stitch", "test_gpu_s6")}
    show_table([{"Binary": name, "SHA-256": digest} for name, digest in STATE["binaries"].items()])


def check_v0():
    STATE["v0"] = False
    command = [sys.executable, "tests/run_tests.py", "--compiler", NVCC, "--group", "v0"]
    if not RUN_FULL_V0_TESTS:
        command += ["--suite", "warp", "--suite", "pipeline"]
    if REQUIRE_T4:
        command.append("--require-t4")
    suites = run_command(command, "v0-regression")
    match = re.search(r"PASS v0 suites: (\d+), total checks: (\d+)", suites.stdout)
    if not match:
        raise ValueError("Missing V0 suite PASS summary")
    (RESULTS / "panoramas").mkdir(exist_ok=True)
    output = RESULTS / "panoramas/site1_small.png"
    result = run_command([PROJECT / "build/stitch", DATASET / "site1/small_left.jpg",
                          DATASET / "site1/small_right.jpg", output, "--version", "0", "--debug"],
                         "v0-default-five-runs")
    timing = DATA_HELPERS.parse_stitch_csv(result.stdout, runs=5)
    with PILImage.open(output) as image:
        image.load()
        if image.mode != "RGB" or image.width <= 0 or image.height <= 0:
            raise ValueError("V0 did not write a valid RGB panorama")
    STATE["v0"] = True
    STATE["full_v0_regression"] = bool(RUN_FULL_V0_TESTS)
    STATE["v0_suite"] = {"suites": int(match[1]), "checks": int(match[2]), "default_runs": 5}
    show_table([{"Stage": name, "Average ms": timing["average"][name],
                 "Minimum ms": timing["minimum"][name]} for name in DATA_HELPERS.TIMING_COLUMNS])
    print(f"PASS: {match[1]} V0 suites, {match[2]} checks; default five-run CSV validated.")


def parse_gpu_pass(text):
    match = re.search(r"PASS: (\d+) checks, (\d+) V0/V1 comparisons; max RGB error=(\d+), threshold=(\d+)", text)
    if not match:
        raise ValueError("GPU test did not report a valid PASS summary")
    threshold = re.search(r"max_channel_error\s*=\s*(\d+)",
                          (PROJECT / "tests/gpu/test_gpu_s6_warp_blend.cu").read_text())
    if not threshold or int(match[4]) != int(threshold[1]) or int(match[3]) > int(match[4]):
        raise ValueError("Reported color error/threshold differs from the submitted test")
    return {"checks": int(match[1]), "comparisons": int(match[2]),
            "max_rgb_error": int(match[3]), "tolerance": int(match[4])}


def check_s6_fixtures():
    STATE["s6_fixtures"] = False
    result = run_command([PROJECT / "build/test_gpu_s6"], "s6-fixtures")
    stats = parse_gpu_pass(result.stdout)
    STATE["s6_fixtures"] = True
    STATE["fixture_metrics"] = stats
    show_table([stats])


def parse_homography(text):
    match = re.search(r"\[debug\] H\(B->A\)=([^\n]+)", text)
    if not match:
        raise ValueError("V0 diagnostics do not contain H(B->A)")
    tokens = match[1].split()
    if len(tokens) != 9 or not all(math.isfinite(float(value)) for value in tokens):
        raise ValueError("Homography must contain nine finite coefficients")
    return tokens


def verify_real_pairs():
    global REAL_ROWS
    STATE["real_pairs"] = False
    REAL_ROWS = []
    (RESULTS / "cases").mkdir(exist_ok=True)
    for pair in PAIRS:
        for size in SIZES:
            name = f"{pair}_{size}"
            left, right = [DATASET / pair / f"{size}_{side}.jpg" for side in ("left", "right")]
            if name == "site1_small" and STATE.get("v0"):
                diagnostic = (LOGS / "v0-default-five-runs.stderr.log").read_text()
            else:
                cpu = run_command([PROJECT / "build/stitch", left, right,
                                   RESULTS / f"panoramas/{name}.png", "--version", "0",
                                   "--runs", "1", "--debug"], f"v0-{name}")
                DATA_HELPERS.parse_stitch_csv(cpu.stdout, runs=1)
                diagnostic = cpu.stderr
            h = parse_homography(diagnostic)
            gpu = run_command([PROJECT / "build/test_gpu_s6", left, right, *h], f"s6-{name}")
            metrics = parse_gpu_pass(gpu.stdout)
            canvas = re.search(r"S6 canvas=(\d+)x(\d+) offset=\((\d+),(\d+)\)", diagnostic)
            if not canvas:
                raise ValueError("Missing canvas metadata in V0 diagnostics")
            record = {"pair": pair, "size": size, "H_B_to_A": [float(value) for value in h],
                      "H_cli_tokens": h, "inputs": {str(p.relative_to(DATASET)): sha256(p) for p in (left, right)},
                      "canvas": [int(value) for value in canvas.groups()], "metrics": metrics}
            (RESULTS / f"cases/{name}.json").write_text(json.dumps(record, indent=2))
            REAL_ROWS.append({"Pair": pair, "Size": size, "Canvas W": int(canvas[1]),
                              "Canvas H": int(canvas[2]), "Max RGB error": metrics["max_rgb_error"],
                              "Tolerance": metrics["tolerance"], "Status": "PASS"})
            print(f"PASS: {name}; same H, geometry matched, max RGB error={metrics['max_rgb_error']}")
    expected = {(pair, size) for pair in ("site1", "site2", "site3", "challenge")
                for size in ("small", "medium", "large")}
    STATE["real_pairs"] = {(row["Pair"], row["Size"]) for row in REAL_ROWS} == expected
    pd.DataFrame(REAL_ROWS).to_csv(RESULTS / "real_pair_summary.csv", index=False)
    show_table(REAL_ROWS)


def show_gallery():
    # Display V0 references only: GPU pixels are compared inside the C++ test.
    for pair in PAIRS:
        paths = [DATASET / pair / "small_left.jpg", DATASET / pair / "small_right.jpg",
                 RESULTS / f"panoramas/{pair}_small.png"]
        figure, axes = plt.subplots(1, 3, figsize=(15, 4))
        for axis, path, title in zip(axes, paths, ("A", "B", "V0 reference panorama")):
            with PILImage.open(path) as image:
                preview = image.copy()
                preview.thumbnail((1100, 550))
            axis.imshow(preview)
            axis.set_title(f"{pair} — {title}")
            axis.axis("off")
        plt.tight_layout()
        plt.show()
        plt.close(figure)


def run_memcheck():
    global MEMCHECK_ROWS
    STATE["memcheck"] = False
    MEMCHECK_ROWS = []
    if not RUN_MEMCHECK:
        MEMCHECK_ROWS.append({"Case": "all", "Status": "SKIPPED", "Reason": "RUN_MEMCHECK=False"})
    else:
        candidates = [shutil.which("compute-sanitizer"),
                      str(Path(NVCC).parent / "compute-sanitizer"), "/usr/local/cuda/bin/compute-sanitizer"]
        tool = next((path for path in candidates if path and Path(path).is_file()), None)
        if tool is None:
            MEMCHECK_ROWS.append({"Case": "all", "Status": "UNAVAILABLE",
                                  "Reason": "Install Compute Sanitizer matching this CUDA runtime, then rerun this cell"})
        else:
            cases = [("fixtures", [])]
            for pair, size in MEMCHECK_REAL_CASES:
                record = json.loads((RESULTS / f"cases/{pair}_{size}.json").read_text())
                cases.append((f"{pair}_{size}", [DATASET / pair / f"{size}_left.jpg",
                                                DATASET / pair / f"{size}_right.jpg", *record["H_cli_tokens"]]))
            for name, arguments in cases:
                result = run_command([tool, "--tool", "memcheck", "--leak-check", "full",
                                      "--error-exitcode", "99", PROJECT / "build/test_gpu_s6", *arguments],
                                     f"memcheck-{name}", check=False, timeout=2400)
                text = result.stdout + "\n" + result.stderr
                summaries = re.findall(r"ERROR SUMMARY:\s*([\d,]+) errors?", text)
                leaks = re.findall(r"LEAK SUMMARY:\s*([\d,]+) bytes leaked", text)
                try:
                    parse_gpu_pass(text)
                    target_passed = True
                except ValueError:
                    target_passed = False
                passed = (result.returncode == 0 and target_passed and bool(summaries) and
                          all(int(value.replace(",", "")) == 0 for value in summaries) and
                          all(int(value.replace(",", "")) == 0 for value in leaks) and
                          not re.search(r"^=+\s*(?:Error|Fatal):", text, flags=re.MULTILINE))
                MEMCHECK_ROWS.append({"Case": name, "Status": "PASS" if passed else "FAIL",
                                      "Return code": result.returncode,
                                      "Reason": "Target PASS and zero error summary" if passed else
                                                f"Inspect logs/memcheck-{name}.*.log"})
                print(f"Memcheck {name}: {MEMCHECK_ROWS[-1]['Status']}")
    STATE["memcheck"] = bool(MEMCHECK_ROWS) and all(row["Status"] == "PASS" for row in MEMCHECK_ROWS)
    pd.DataFrame(MEMCHECK_ROWS).to_csv(RESULTS / "memcheck_summary.csv", index=False)
    show_table(MEMCHECK_ROWS)


def export_evidence():
    # Detect source/input/binary changes after the recorded tests.
    unchanged = all(sha256(PROJECT / name) == digest for name, digest in SOURCE_HASHES.items())
    unchanged &= all(sha256(DATASET / name) == digest for name, digest in DATA_HASHES.items())
    unchanged &= all(sha256(PROJECT / "build" / name) == digest
                     for name, digest in STATE.get("binaries", {}).items())
    STATE["snapshot_unchanged"] = bool(unchanged)
    gates = ("runtime_t4", "source", "dataset", "build", "v0", "full_v0_regression", "s6_fixtures", "real_pairs",
             "memcheck", "snapshot_unchanged")
    ready = all(STATE.get(gate) is True for gate in gates)
    report = {"ready_for_t4_review": ready, "gates": {gate: STATE.get(gate, False) for gate in gates},
              "environment": ENVIRONMENT, "source": SOURCE, "checks": STATE,
              "real_pairs": REAL_ROWS, "memcheck": MEMCHECK_ROWS,
              "scope": "Independent S6 verification, not full V1 integration or a speedup benchmark"}
    (RESULTS / "verification_summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    show_table([{"Gate": name, "Status": "PASS" if STATE.get(name) is True else "INCOMPLETE"} for name in gates])
    print("READY FOR T4 REVIEW" if ready else "INCOMPLETE — retain logs and resolve the gates above")
    archive = PROJECT.parent / (PROJECT.name + "-evidence.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(RESULTS.rglob("*")):
            if path.is_file() and "panoramas" not in path.relative_to(RESULTS).parts:
                bundle.write(path, Path("results") / path.relative_to(RESULTS))
    print(f"Evidence ZIP: {archive}; SHA-256: {sha256(archive)}")
    return archive
