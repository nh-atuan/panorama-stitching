# Authors: Le Thuong De (23120232)
# External source: none
"""Command capture and provenance shared by the P5-T09 batch tools."""
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys


class BatchError(RuntimeError):
    pass


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def capture(command, prefix, timeout=600):
    """Retain the exact argv, stdout, stderr and process status, including timeouts."""
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    command = list(map(str, command))
    record = {"command": command, "returncode": None, "timeout": False}
    out, err = "", ""
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        out, err = process.stdout, process.stderr
        record["returncode"] = process.returncode
    except subprocess.TimeoutExpired as error:
        record["timeout"] = True
        out = error.stdout or ""
        err = error.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", errors="replace")
    except OSError as error:
        err = str(error)
    prefix.with_suffix(".stdout").write_text(out, encoding="utf-8")
    prefix.with_suffix(".stderr").write_text(err, encoding="utf-8")
    write_json(prefix.with_suffix(".command.json"), record)
    return record, out, err


def reject_stub(text):
    lowered = text.lower()
    return any(marker in lowered for marker in ("infrastructure scaffold", "six stubs", "stubs only"))


def inspect_environment(binary=None, require_t4=False):
    gpu = "unavailable"
    if shutil.which("nvidia-smi"):
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            gpu = result.stdout.strip()
    if require_t4 and not any(name.strip() in {"Tesla T4", "NVIDIA T4", "T4"} for name in
                             (line.split(",")[0] for line in gpu.splitlines())):
        raise BatchError("Official verification requires Colab Tesla T4")
    environment = {"gpu": gpu, "host": platform.platform(), "python": sys.version,
                   "profiler_paths": {name: shutil.which(name) for name in ("nsys", "ncu")}}
    if binary is not None:
        path = Path(binary).resolve()
        if not path.is_file():
            raise BatchError(f"Executable not found: {path}")
        environment.update(binary=str(path), binary_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return environment
