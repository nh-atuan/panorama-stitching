# Authors: Thanh Chuong (23120195)
# External source: none

"""Package the current source, scripts and tests for the S6 Colab notebook."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ("src", "scripts", "tests")
EXTENSIONS = {".h", ".hpp", ".cuh", ".cpp", ".cu", ".py", ".md", ".json"}
REQUIRED = {"src/main.cu", "src/common/common.h", "src/common/cuda_utils.cuh",
            "src/v1/v1_warp_blend.h", "src/v1/v1_warp_blend.cu",
            "scripts/build.py", "scripts/midterm_notebook.py", "tests/run_tests.py",
            "tests/gpu/test_gpu_s6_warp_blend.cu"}


def git_output(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def package(destination):
    destination = Path(destination).resolve()
    payload = {}
    for directory in PREFIXES:
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Source symlinks are not supported: {path}")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() in EXTENSIONS:
                payload[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    if not REQUIRED.issubset(payload):
        raise ValueError(f"Missing required files: {sorted(REQUIRED - payload.keys())}")
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}
    snapshot = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    manifest = {"schema": 1, "git_commit": git_output("rev-parse", "HEAD"),
                "git_branch": git_output("branch", "--show-current"),
                "source_status": git_output("status", "--porcelain", "--", *PREFIXES),
                "snapshot_sha256": snapshot, "files": hashes}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stable timestamps make the same snapshot produce the same archive bytes.
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
        entry = zipfile.ZipInfo("source_manifest.json", (2026, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Archive: {destination}")
    print(f"Files: {len(payload)}; snapshot SHA-256: {snapshot}")
    print(f"ZIP SHA-256: {hashlib.sha256(destination.read_bytes()).hexdigest()}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/Group16_S6_Source.zip")
    package(parser.parse_args().output)
