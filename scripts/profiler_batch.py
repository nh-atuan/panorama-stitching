# Authors: Le Thuong De (23120232)
# External source: none
"""Collect Nsight reports without treating profiler-instrumented runs as benchmarks."""
from pathlib import Path
import shutil
from profiling_common import capture, reject_stub


def collect(profiler, command, folder, kernel_regex=None, launch_count=1, scope="pipeline"):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    executable = shutil.which(profiler)
    if not executable:
        return {"profiler": profiler, "status": "unavailable", "reason": "executable not found"}
    report = folder / "capture"
    if profiler == "nsys":
        argv = [executable, "profile", "--trace=cuda,nvtx", "--sample=none", "--cpuctxsw=none",
                "--force-overwrite=true", "-o", str(report), *command]
        extension = ".nsys-rep"
    elif profiler == "ncu":
        argv = [executable, "--set", "basic", "--target-processes", "all", "--launch-count", str(launch_count), "--force-overwrite",
                "--export", str(report), *command]
        if kernel_regex:
            argv[1:1] = ["--kernel-name", "regex:" + kernel_regex]
        extension = ".ncu-rep"
    else:
        raise ValueError(f"unknown profiler: {profiler}")
    record, out, err = capture(argv, folder / "profile")
    evidence = {"profiler": profiler, "status": "failed", "profile": record,
                "report": str(report.with_suffix(extension))}
    if reject_stub(out + err):
        evidence["reason"] = "pipeline is a scaffold; profiling is not accepted"
        return evidence
    if scope == "pipeline" and "Verification scope: S4-S5 only" in out + err:
        evidence["reason"] = "stage driver is not a full CUDA pipeline"
        return evidence
    if "ERR_NVGPUCTRPERM" in out + err:
        evidence.update(status="unavailable", reason="GPU performance counter permission denied")
        return evidence
    if "No kernels were profiled" in out + err:
        evidence["reason"] = "kernel filter matched no launches"
        return evidence
    if record["returncode"] != 0 or not report.with_suffix(extension).is_file():
        evidence["reason"] = "profiler failed or did not create its report"
        return evidence
    if profiler == "nsys":
        export = [executable, "stats", "--report", "cuda_gpu_kern_sum,cuda_gpu_mem_time_sum,nvtx_pushpop_sum",
                  "--format", "csv", "--force-export=true", str(report.with_suffix(extension))]
    else:
        export = [executable, "--import", str(report.with_suffix(extension)), "--csv"]
    exported, _, _ = capture(export, folder / "metrics")
    evidence["export"] = exported
    if exported["returncode"] == 0:
        evidence["status"] = "ok"
    else:
        evidence["reason"] = "report export failed"
    return evidence
