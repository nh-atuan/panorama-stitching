#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""T4/environment and official dataset gates; all failures retain their manifest."""

import csv
import importlib.util
import io
import platform
from pathlib import Path
import shutil
import sys

from profiling_common import capture, write_json
from midterm_notebook import sha256, validate_dataset

MANIFEST_SHA256 = "99fc712988075326a351d0bf580405e418bb28d24d56d4cc1b31505c480bdd9d"
VERSIONS = tuple(range(6))


def parse_gpu(text):
    rows = list(csv.reader(io.StringIO(text.strip())))
    if len(rows) != 1 or len(rows[0]) != 6:
        raise ValueError("Require exactly one visible GPU with six nvidia-smi fields")
    name, uuid, driver, cc, total, free = [s.strip() for s in rows[0]]
    if name not in {"Tesla T4", "NVIDIA T4", "T4"} or cc != "7.5":
        raise ValueError(f"T4 certification requires T4 / sm_75, detected {name} / {cc}")
    memory = dict(total_mib=float(total), free_mib=float(free))
    if not 0 < memory["free_mib"] <= memory["total_mib"]:
        raise ValueError("GPU memory query is invalid or no free memory remains")
    return dict(name=name, uuid=uuid, driver=driver, compute_capability=cc, **memory)


def environment(evidence):
    evidence = Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    result = dict(status="failed", python=sys.version, host=platform.platform())
    try:
        result["tools"] = {t: shutil.which(t) for t in ("nvidia-smi", "nvcc", "git", "g++")}
        result["python_modules"] = {m: importlib.util.find_spec(m) is not None
                                    for m in ("nbformat", "nbclient", "PIL", "numpy", "matplotlib")}
        missing = [k for k, v in result["tools"].items() if not v]
        missing += [k for k, v in result["python_modules"].items() if not v]
        if missing:
            raise RuntimeError(f"Missing preflight dependencies: {missing}")
        record, stdout, _ = capture([
            "nvidia-smi", "--query-gpu=name,uuid,driver_version,compute_cap,memory.total,memory.free",
            "--format=csv,noheader,nounits"], evidence / "logs/gpu", timeout=30)
        if record["returncode"] != 0:
            raise RuntimeError("nvidia-smi failed; see logs/gpu.stderr")
        result["gpu"] = parse_gpu(stdout)
        record, stdout, _ = capture(["nvcc", "--version"], evidence / "logs/nvcc", timeout=30)
        if record["returncode"] != 0:
            raise RuntimeError("nvcc --version failed")
        result["nvcc"] = stdout
        result["status"] = "passed"
        return result
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        write_json(evidence / "environment.json", result)


def dataset(root, evidence, expected_hash=MANIFEST_SHA256):
    """Reuse exact 24-file hash/layout checks; no new data or synthetic fixtures required."""
    root, evidence = Path(root), Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    result = dict(root=str(root.resolve()), status="failed")
    try:
        manifest = root / "manifest.csv"
        if not manifest.is_file():
            raise FileNotFoundError(f"Missing official dataset: {manifest}; use final_notebook.fetch_dataset")
        result["manifest_sha256"] = sha256(manifest)
        if result["manifest_sha256"] != expected_hash:
            raise ValueError("Official dataset manifest SHA-256 mismatch")
        result["images"] = validate_dataset(root)
        result["sizes_bytes"] = {r["file"]: (root / r["file"]).stat().st_size for r in result["images"]}
        shutil.copy2(manifest, evidence / "dataset_manifest.csv")
        result["status"] = "passed"
        return result
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        write_json(evidence / "dataset.json", result)
