# Authors: Le Thuong De (23120232)
# External source: none
"""Evaluate the six documented image pairs for selected executable versions."""
import csv
from pathlib import Path
from homography_common import load_truth
from homography_error import EvaluationError, evaluate, parse_estimate
from profiling_common import BatchError, capture, reject_stub, write_json

CASES = ("translation", "projective")
SIZES = ("small", "medium", "large")


def inputs(folder):
    pairs = []
    for case in CASES:
        for size in SIZES:
            prefix = Path(folder) / case / size
            left, right, truth = (Path(str(prefix) + suffix) for suffix in
                                  ("_left.png", "_right.png", "_truth.json"))
            for path in (left, right, truth):
                if not path.is_file():
                    raise BatchError(f"Synthetic input missing: {path}")
            pairs.append((case, size, left, right, truth))
    return pairs


def check_case(binary, version, pair, folder, scope="pipeline"):
    case, size, left, right, truth_file = pair
    folder = Path(folder) / f"v{version}" / case / size
    folder.mkdir(parents=True, exist_ok=True)
    command = [str(binary), str(left), str(right), str(folder / "panorama.png"),
               "--version", str(version), "--runs", "1", "--debug"]
    record, out, err = capture(command, folder / "run")
    row = {"version": version, "case": case, "size": size, "scope": scope, "status": "failed"}
    try:
        if record["returncode"] != 0:
            raise EvaluationError("executable failed")
        if reject_stub(out + err):
            raise EvaluationError("scaffold output cannot verify homography")
        if scope == "pipeline" and "Verification scope: S4-S5 only" in err:
            raise EvaluationError("stage driver is not a full CUDA pipeline")
        if not (folder / "panorama.png").is_file():
            raise EvaluationError("panorama output missing")
        metrics = evaluate(load_truth(truth_file), parse_estimate(err))
        row.update(metrics)
        row["status"] = "ok" if metrics["rmse_px"] <= 0.5 and metrics["max_px"] <= 1.0 else "failed"
        if row["status"] != "ok":
            row["reason"] = "ground-truth error exceeds RMSE 0.5 px / Max 1 px"
    except (OSError, ValueError, EvaluationError) as error:
        row["reason"] = str(error)
    write_json(folder / "evaluation.json", row)
    return row


def write_summary(folder, rows):
    keys = ["version", "case", "size", "scope", "status", "points", "grid_points", "rmse_px", "max_px", "nrmse", "reason"]
    with (Path(folder) / "synthetic.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
