# Authors: Thanh Chuong (23120195)
# External source: none

"""Validation and display helpers for Group16_Midterm.ipynb.

This module does not implement the P3-T04 benchmark runner. It validates the
per-pair stdout CSV produced by stitch after that runner has executed.
"""

import csv
import hashlib
import io
import math
from pathlib import Path
import stat
import zipfile

SIZES = {"small": (1280, 720), "medium": (1920, 1080), "large": (3840, 2160)}
SITES = ("site1", "site2", "site3", "challenge")
TIMING_COLUMNS = [f"S{i}_ms" for i in range(1, 7)] + ["Total_ms"]
CSV_COLUMNS = ["Run_Index", *TIMING_COLUMNS]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive, destination):
    """Reject traversal, duplicate targets, and symbolic links before writing."""
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as bundle:
        seen = set()
        for entry in bundle.infolist():
            name = entry.filename.replace("\\", "/")
            target = (destination / name).resolve()
            if not target.is_relative_to(destination) or target == destination:
                raise ValueError(f"Unsafe archive member: {entry.filename}")
            if target in seen or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError(f"Duplicate target or symbolic link: {entry.filename}")
            seen.add(target)
        # The names have been validated; use the same normalized targets to write.
        for entry in bundle.infolist():
            target = destination / entry.filename.replace("\\", "/")
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(entry) as source, target.open("wb") as output:
                    import shutil
                    shutil.copyfileobj(source, output)


def validate_dataset(root):
    """Check all 24 images against the prepared dataset's SHA-256 manifest."""
    from PIL import Image

    root = Path(root).resolve()
    with (root / "manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"file", "site", "side", "width", "height", "sha256"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Dataset manifest is missing required columns")
        rows = list(reader)
    expected = {f"{site}/{size}_{side}.jpg"
                for site in SITES for size in SIZES for side in ("left", "right")}
    names = [row["file"] for row in rows]
    if len(names) != len(set(names)) or set(names) != expected:
        raise ValueError("Manifest must contain exactly the 24 selected image paths")
    verified = []
    for row in rows:
        relative = row["file"]
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Image leaves the dataset directory: {relative}")
        size_name, side = path.stem.split("_")
        dimensions = SIZES[size_name]
        if row["site"] != path.parent.name or row["side"] != side:
            raise ValueError(f"Manifest metadata mismatch: {relative}")
        if (int(row["width"]), int(row["height"])) != dimensions:
            raise ValueError(f"Manifest dimensions mismatch: {relative}")
        actual_hash = sha256(path)
        if actual_hash != row["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
        with Image.open(path) as image:
            if (image.format != "JPEG" or image.mode != "RGB" or
                    image.size != dimensions or image.getexif()):
                raise ValueError(f"Invalid JPEG/layout/EXIF: {relative}")
            image.load()
        verified.append({"file": relative, "width": dimensions[0],
                         "height": dimensions[1], "sha256": actual_hash})
    return verified


def parse_stitch_csv(text, runs=5):
    """Validate numbered runs and the average/minimum rows; never time Python."""
    if runs <= 0:
        raise ValueError("runs must be positive")
    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if row]
    if not rows or rows[0] != CSV_COLUMNS:
        raise ValueError("Unexpected stitch CSV header")
    expected_labels = [str(index) for index in range(1, runs + 1)] + ["Average", "Minimum"]
    if len(rows) != runs + 3 or [row[0] for row in rows[1:]] != expected_labels:
        raise ValueError("Missing, duplicated, or unordered timing rows")
    values = []
    for row in rows[1:]:
        if len(row) != len(CSV_COLUMNS):
            raise ValueError("Unexpected timing column count")
        numbers = [float(value) for value in row[1:]]
        if any(not math.isfinite(value) or value < 0 for value in numbers):
            raise ValueError("Non-finite or negative timing")
        # Independent end-to-end timing can include overhead beyond stage clocks.
        if numbers[-1] + 1e-5 < sum(numbers[:-1]):
            raise ValueError("End-to-end time is smaller than the sum of stage times")
        values.append(numbers)
    measurements = values[:runs]
    average = [sum(row[i] for row in measurements) / runs for i in range(7)]
    minimum = [min(row[i] for row in measurements) for i in range(7)]
    for reported, calculated in ((values[-2], average), (values[-1], minimum)):
        for left, right in zip(reported, calculated):
            if not math.isclose(left, right, rel_tol=1e-7, abs_tol=2e-8):
                raise ValueError("Reported summary disagrees with measured runs")
    return {"runs": [dict(zip(TIMING_COLUMNS, row)) for row in measurements],
            "average": dict(zip(TIMING_COLUMNS, average)),
            "minimum": dict(zip(TIMING_COLUMNS, minimum))}


def collect_benchmark_csv(root, runs=5):
    """Read the proposed handoff layout: <root>/<site>/<size>.csv."""
    root = Path(root)
    averages, minima, measured = [], [], []
    for site in SITES[:3]:
        for size in SIZES:
            parsed = parse_stitch_csv((root / site / f"{size}.csv").read_text(), runs)
            labels = {"site": site, "resolution": size}
            averages.append({**labels, **parsed["average"]})
            minima.append({**labels, **parsed["minimum"]})
            measured.extend({**labels, "run": i, **row}
                            for i, row in enumerate(parsed["runs"], 1))
    return averages, minima, measured


def source_manifest(root):
    root = Path(root)
    paths = [path for folder in ("src", "scripts", "tests")
             for path in (root / folder).rglob("*")
             if path.is_file() and path.suffix in {".cpp", ".cu", ".c", ".h", ".cuh", ".py"}
             and "__pycache__" not in path.parts]
    if not paths:
        raise ValueError("No source files found")
    return {path.relative_to(root).as_posix(): sha256(path) for path in sorted(paths)}


def preview_image(path, width=1200):
    """Return a bounded JPEG preview; never embed the full panorama by default."""
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((width, 800))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def overlap_box(log_text, width_a, height_a, width_b, height_b):
    """Locate an overlap envelope in canvas coordinates, for an inspection crop.

    It is the axis-aligned intersection envelope, not an exact validity mask.
    """
    import re
    from homography_error import parse_estimate
    from homography_common import project
    import numpy as np

    match = re.search(r"\[debug\] S6 canvas=(\d+)x(\d+) offset=\((-?\d+),(-?\d+)\)", log_text)
    if not match:
        raise ValueError("No canvas diagnostics available for an overlap crop")
    canvas_w, canvas_h, ox, oy = map(int, match.groups())
    matrix = parse_estimate(log_text)
    x, y, _ = project(matrix, np.array([0, width_b - 1, 0, width_b - 1]),
                      np.array([0, 0, height_b - 1, height_b - 1]))
    if not np.all(np.isfinite(x + y)):
        raise ValueError("Invalid projected corners")
    x0 = max(ox, math.ceil(float(x.min()) + ox), 0)
    y0 = max(oy, math.ceil(float(y.min()) + oy), 0)
    x1 = min(ox + width_a, math.floor(float(x.max()) + ox) + 1, canvas_w)
    y1 = min(oy + height_a, math.floor(float(y.max()) + oy) + 1, canvas_h)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("No overlap envelope")
    return x0, y0, x1, y1
