#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Build dataset/<site>/<small|medium|large>_<left|right>.jpg from selected raw pairs (docs/dataset.md, section 7).

For each pair: apply EXIF orientation, require equal left/right sizes, cut both with the same centred
16:9 box (at least 3840x2160, never upscaled), resize with Lanczos to 1280x720, 1920x1080 and 3840x2160,
and save JPEG quality 95 without EXIF. dataset/manifest.csv records sources, crop box and SHA-256.

Example:
  python scripts/prepare_dataset.py --raw raw --out dataset \\
      --pair site1=tuan-standard1 --pair site2=chuong-standard1 --pair challenge=tuan-challenge1
"""

import argparse
import csv
import hashlib
from pathlib import Path
import re
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset_common import MIN_HEIGHT, MIN_WIDTH, SIZES, crop_box_16_9, load_oriented, pair_paths  # noqa: E402

SITE_NAME = re.compile(r"^(site\d+|challenge\d*)$")
JPEG_QUALITY = 95


class DatasetError(Exception):
    pass


def parse_pairs(entries):
    pairs = []
    for entry in entries:
        site, _, code = entry.partition("=")
        if not SITE_NAME.match(site) or not code:
            raise DatasetError(f"--pair must look like site1=tuan-standard1, got '{entry}'")
        if site in (s for s, _ in pairs):
            raise DatasetError(f"Site '{site}' is given twice")
        pairs.append((site, code))
    return pairs


def load_pair(raw_root, code):
    try:
        left_path, right_path = pair_paths(raw_root, code)
    except ValueError as error:
        raise DatasetError(str(error)) from error
    for path in (left_path, right_path):
        if not path.is_file():
            raise DatasetError(f"{code}: missing {path.as_posix()}")
    left, _, left_format = load_oriented(left_path)
    right, _, right_format = load_oriented(right_path)
    if left_format != "JPEG" or right_format != "JPEG":
        raise DatasetError(f"{code}: both files must be JPEG")
    if left.size != right.size:
        raise DatasetError(f"{code}: left {left.size} and right {right.size} differ after EXIF orientation")
    width, height = left.size
    if width < height:
        raise DatasetError(f"{code}: image is portrait ({width}x{height}) after EXIF orientation")
    box = crop_box_16_9(width, height)
    crop_w, crop_h = box[2] - box[0], box[3] - box[1]
    if crop_w < MIN_WIDTH or crop_h < MIN_HEIGHT:
        raise DatasetError(f"{code}: 16:9 crop is {crop_w}x{crop_h}, below {MIN_WIDTH}x{MIN_HEIGHT}")
    return (left_path, right_path), (left.convert("RGB"), right.convert("RGB")), box


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_site(out_root, site, code, paths, images, box):
    folder = Path(out_root) / site
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for side, source, image in zip(("left", "right"), paths, images):
        cropped = image.crop(box)
        for size_name, width, height in SIZES:
            target = folder / f"{size_name}_{side}.jpg"
            resized = cropped.resize((width, height), Image.Resampling.LANCZOS)
            # No exif argument: Pillow writes no EXIF block, so orientation and GPS are dropped.
            resized.save(target, "JPEG", quality=JPEG_QUALITY)
            rows.append({
                "site": site, "pair": code, "side": side, "source": source.as_posix(),
                "crop_box": "{} {} {} {}".format(*box), "width": width, "height": height,
                "file": target.relative_to(out_root).as_posix(), "sha256": sha256(target),
            })
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", default="raw", help="folder holding raw/<member>/ photos")
    parser.add_argument("--out", default="dataset", help="output folder")
    parser.add_argument("--pair", action="append", required=True, metavar="SITE=CODE",
                        help="site name (site1, site2, site3, challenge) and pair code")
    args = parser.parse_args(argv)
    try:
        pairs = parse_pairs(args.pair)
        # Validate every pair before writing anything.
        loaded = [(site, code, *load_pair(args.raw, code)) for site, code in pairs]
        rows = []
        for site, code, paths, images, box in loaded:
            rows += write_site(args.out, site, code, paths, images, box)
            print(f"{site}: {code}, crop {box}, 3 sizes x 2 sides")
    except DatasetError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    manifest = Path(args.out) / "manifest.csv"
    with open(manifest, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} images and {manifest.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
