#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Check the main candidate pairs in raw/<member>/ (docs/dataset.md, sections 1, 3, 4 and 6).

Only main pairs (no _b<k> suffix) are checked. Every criterion gets "Đạt", "Chưa đạt" or "Cần review";
criteria that cannot be verified automatically are always "Cần review", never assumed to pass.
The overlap is an estimate from a horizontal shift search and only supports the human review.

Prints Markdown: a result table for section 5.3 and a suggested priority order for section 6.
The order is a script suggestion, not the members' review.

Example: python scripts/check_pairs.py --raw raw --out results/check_pairs.md
"""

import argparse
from pathlib import Path
import statistics
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset_common import MEMBERS, MIN_HEIGHT, MIN_WIDTH, crop_box_16_9, exif_fields, load_oriented, scan_member  # noqa: E402

PASS, FAIL, REVIEW, SKIP = "Đạt", "Chưa đạt", "Cần review", "—"
MAX_GAP_SECONDS = 60
MAIN_CAMERA_35MM = (22, 30)
OVERLAP_RANGE = (0.30, 0.50)
MIN_SHIFT_SCORE = 0.3
MANUAL = "Cảnh tĩnh, ít parallax, đủ texture (cặp chuẩn), không lộ mặt người lạ"
CRITERIA = ("Tên file", "Đọc được JPEG", "Ảnh ngang", "Đủ 3840×2160 sau khi cắt 16:9", "Hai ảnh cùng kích thước",
            "Không có GPS", "Camera chính 1x", "Cùng thiết bị", "Chụp liền nhau", "Độ nét", "Chồng lấn 30-50%", MANUAL)


def gray_array(image, width):
    height = max(1, round(image.height * width / image.width))
    return np.asarray(image.convert("L").resize((width, height)), dtype=np.float64)


def sharpness(image):
    """Variance of the 4-neighbour Laplacian on a 1024-px-wide gray copy."""
    g = gray_array(image, 1024)
    lap = g[1:-1, :-2] + g[1:-1, 2:] + g[:-2, 1:-1] + g[2:, 1:-1] - 4.0 * g[1:-1, 1:-1]
    return float(lap.var())


def estimate_overlap(left, right, width=256, max_dy=6, min_fraction=0.1):
    """Horizontal shift s with right(x, y) ~ left(x + s, y + dy), by normalised cross-correlation of
    gradient images. Returns (overlap fraction (W - s) / W, best correlation)."""
    a = np.abs(np.diff(gray_array(left, width), axis=1))
    b = np.abs(np.diff(gray_array(right, width), axis=1))
    h, w = a.shape
    best = (-1.0, 0)
    for dy in range(-max_dy, max_dy + 1):
        a_rows = a[max(0, dy):h + min(0, dy)]
        b_rows = b[max(0, -dy):h + min(0, -dy)]
        for s in range(1, int(w * (1.0 - min_fraction)) + 1):
            x = a_rows[:, s:].ravel()
            y = b_rows[:, :w - s].ravel()
            x = x - x.mean()
            y = y - y.mean()
            denominator = np.sqrt((x * x).sum() * (y * y).sum())
            score = float((x * y).sum() / denominator) if denominator > 0 else 0.0
            if score > best[0]:
                best = (score, s)
    score, s = best
    return (w - s) / w, score


def check_pair(pair):
    """Returns ({criterion: (status, note)}, metrics) for one candidate pair."""
    result = {name: (SKIP, "") for name in CRITERIA}
    result[MANUAL] = (REVIEW, "không kiểm tra tự động được")
    metrics: dict = {"overlap": None, "sharpness": None}
    result["Tên file"] = (FAIL, "; ".join(pair.naming_problems)) if pair.naming_problems else (PASS, "")
    missing = [side for side in ("left", "right") if getattr(pair, side) is None]
    if missing:
        result["Đọc được JPEG"] = (FAIL, f"thiếu ảnh {', '.join(missing)}")
        return result, metrics

    images, fields = [], []
    for path in (pair.left, pair.right):
        try:
            image, exif, image_format = load_oriented(path)
        except Exception as error:  # Pillow raises several types for unreadable files
            result["Đọc được JPEG"] = (FAIL, f"{path.name}: không đọc được ({type(error).__name__}); "
                                             "stb chỉ đọc JPEG/PNG, không đọc HEIC")
            return result, metrics
        if image_format != "JPEG":
            result["Đọc được JPEG"] = (FAIL, f"{path.name}: định dạng {image_format}")
            return result, metrics
        images.append(image)
        fields.append(exif_fields(exif))
    result["Đọc được JPEG"] = (PASS, "")

    (lw, lh), (rw, rh) = images[0].size, images[1].size
    result["Ảnh ngang"] = (PASS, "") if lw > lh and rw > rh else (FAIL, f"{lw}×{lh}, {rw}×{rh}")
    box = crop_box_16_9(lw, lh)
    crop = (box[2] - box[0], box[3] - box[1])
    big_enough = crop[0] >= MIN_WIDTH and crop[1] >= MIN_HEIGHT
    result["Đủ 3840×2160 sau khi cắt 16:9"] = (PASS if big_enough else FAIL, f"gốc {lw}×{lh}, cắt {crop[0]}×{crop[1]}")
    result["Hai ảnh cùng kích thước"] = (PASS, "") if (lw, lh) == (rw, rh) else (FAIL, f"{lw}×{lh} và {rw}×{rh}")

    gps = [f["has_gps"] for f in fields]
    result["Không có GPS"] = (REVIEW, "EXIF có tọa độ GPS") if any(gps) else (PASS, "")

    focal = [f["focal_35mm"] for f in fields]
    zoom = [f["digital_zoom"] for f in fields]
    if any(z not in (None, 1.0) for z in zoom):
        result["Camera chính 1x"] = (REVIEW, f"digital zoom {zoom}")
    elif all(v is not None and MAIN_CAMERA_35MM[0] <= v <= MAIN_CAMERA_35MM[1] for v in focal):
        result["Camera chính 1x"] = (PASS, f"{focal[0]} mm (35 mm)")
    elif all(v is not None for v in focal):
        result["Camera chính 1x"] = (REVIEW, f"tiêu cự 35 mm {focal}")
    else:
        real = [f["focal_mm"] for f in fields]
        note = f"không có tiêu cự 35 mm; tiêu cự thật {real} mm" if any(real) else "không có EXIF tiêu cự"
        result["Camera chính 1x"] = (REVIEW, note)

    devices = [(f["make"], f["model"]) for f in fields]
    if devices[0] == devices[1] and devices[0][1]:
        result["Cùng thiết bị"] = (PASS, " ".join(d for d in devices[0] if d))
    else:
        result["Cùng thiết bị"] = (REVIEW, "không có EXIF thiết bị" if not devices[0][1] else f"{devices}")

    taken = [f["taken"] for f in fields]
    if all(taken):
        gap = (taken[1] - taken[0]).total_seconds()
        ok = 0 <= gap <= MAX_GAP_SECONDS
        result["Chụp liền nhau"] = (PASS if ok else REVIEW, f"phải chụp sau trái {gap:.0f} s")
    else:
        result["Chụp liền nhau"] = (REVIEW, "không có EXIF thời gian chụp")

    metrics["sharpness"] = min(sharpness(image) for image in images)
    overlap, score = estimate_overlap(*images)
    metrics["overlap"] = overlap
    if score < MIN_SHIFT_SCORE:
        result["Chồng lấn 30-50%"] = (REVIEW, f"ước lượng {overlap:.0%} không tin cậy (tương quan {score:.2f})")
    else:
        inside = OVERLAP_RANGE[0] <= overlap <= OVERLAP_RANGE[1]
        result["Chồng lấn 30-50%"] = (PASS if inside else REVIEW, f"ước lượng {overlap:.0%} (tương quan {score:.2f})")
    return result, metrics


def rate_sharpness(rows):
    """Flag pairs below half the median sharpness of the checked pairs; the threshold is relative."""
    values = [m["sharpness"] for _, _, m in rows if m["sharpness"] is not None]
    if not values:
        return
    limit = 0.5 * statistics.median(values)
    for _, result, m in rows:
        if m["sharpness"] is None:
            continue
        status = PASS if m["sharpness"] >= limit else REVIEW
        result["Độ nét"] = (status, f"{m['sharpness']:.0f} (ngưỡng tương đối {limit:.0f})")


def priority_key(row):
    _, result, metrics = row
    statuses = [status for status, _ in result.values()]
    overlap = metrics["overlap"]
    # Criteria left unchecked after a failure count against the pair, like review items.
    not_passed = len(statuses) - statuses.count(PASS)
    return (FAIL in statuses, not_passed,
            abs(overlap - 0.40) if overlap is not None else 1.0, -(metrics["sharpness"] or 0.0))


def summary(result):
    statuses = [status for status, _ in result.values()]
    if FAIL in statuses:
        return FAIL
    return REVIEW if REVIEW in statuses else PASS


def render(rows, unrecognised):
    lines = ["## Kết quả kiểm tra (mục 5.3)", "",
             "| Mã cặp | Đạt? | Ghi chú |", "|---|---|---|"]
    for pair, result, _ in rows:
        notes = [f"{name}: {status}" + (f" ({note})" if note else "")
                 for name, (status, note) in result.items() if status != PASS and status != SKIP]
        lines.append(f"| {pair.code} | {summary(result)} | {'; '.join(notes) or 'Mọi tiêu chí tự động đạt'} |")
    for member, names in unrecognised:
        lines.append(f"| {member}: {len(names)} file | {FAIL} | Tên file không theo quy ước mục 4, "
                     f"không ghép được cặp: {', '.join(names)} |")
    lines += ["", "## Thứ tự ưu tiên do script đề xuất (mục 6)", "",
              "Thứ tự chỉ là gợi ý của script: cặp có tiêu chí chưa đạt xếp cuối, sau đó ít tiêu chí chưa đạt "
              "hoặc chưa kiểm tra được hơn, "
              "ước lượng chồng lấn gần 40% hơn, độ nét cao hơn. Kết luận do từng thành viên review.", "",
              "| Loại (chuẩn / khó) | Thứ tự ưu tiên đề xuất | Mã cặp chính | Lý do đề xuất | Kết quả review của từng thành viên |",
              "|---|---|---|---|---|"]
    for kind, label in (("standard", "chuẩn"), ("challenge", "khó")):
        ranked = sorted((row for row in rows if row[0].kind == kind), key=priority_key)
        for rank, (pair, result, metrics) in enumerate(ranked, 1):
            statuses = [status for status, _ in result.values()]
            reason = f"{statuses.count(FAIL)} chưa đạt, {statuses.count(REVIEW)} cần review"
            if statuses.count(SKIP):
                reason += f", {statuses.count(SKIP)} chưa kiểm tra được"
            if metrics["overlap"] is not None:
                reason += f", chồng lấn ước lượng {metrics['overlap']:.0%}"
            lines.append(f"| {label} | {rank} | {pair.code} | {reason} | |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", default="raw", help="folder holding raw/<member>/ photos")
    parser.add_argument("--out", help="also write the Markdown report to this file")
    args = parser.parse_args(argv)
    rows, unrecognised = [], []
    for member in MEMBERS:
        folder = Path(args.raw) / member
        if not folder.is_dir():
            continue
        pairs, unknown = scan_member(folder, member)
        if unknown:
            unrecognised.append((member, unknown))
        for pair in pairs:
            if pair.is_main:
                result, metrics = check_pair(pair)
                rows.append((pair, result, metrics))
    rate_sharpness(rows)
    report = render(rows, unrecognised)
    sys.stdout.buffer.write(report.encode("utf-8"))
    sys.stdout.flush()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
