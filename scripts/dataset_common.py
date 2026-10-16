# Authors: Nguyen Ho Anh Tuan (23120185)
# External source: none

"""Shared helpers for the dataset scripts: file naming, EXIF orientation, 16:9 crop, EXIF fields.

Naming follows section 4 of docs/dataset.md:
raw/<member>/<standard|challenge><n>_<left|right>[_b<k>].jpg, pair code <member>-<kind><n>[-b<k>].
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
from typing import Optional

from PIL import Image, ImageOps

MEMBERS = ("tuan", "thanh", "chuong", "de")
MIN_WIDTH, MIN_HEIGHT = 3840, 2160
SIZES = (("small", 1280, 720), ("medium", 1920, 1080), ("large", 3840, 2160))

STRICT_NAME = re.compile(r"^(standard|challenge)(\d+)_(left|right)(?:_b(\d+))?\.jpg$")
# Recognises an intended pair even when the number is missing or the extension is wrong.
LENIENT_NAME = re.compile(r"^(standard|challenge)(\d*)_(left|right)(?:_b(\d+))?(?:\.([A-Za-z0-9]+))?$",
                          re.IGNORECASE)
PAIR_CODE = re.compile(r"^([a-z]+)-(standard|challenge)(\d+)(?:-b(\d+))?$")

EXIF_IFD, GPS_IFD = 0x8769, 0x8825
TAG_MAKE, TAG_MODEL = 271, 272
TAG_DATETIME_ORIGINAL, TAG_FOCAL, TAG_FOCAL_35, TAG_DIGITAL_ZOOM = 36867, 37386, 41989, 41988
TAG_GPS_LATITUDE = 2


@dataclass
class PairFiles:
    member: str
    kind: str
    number: str
    backup: str
    left: Optional[Path] = None
    right: Optional[Path] = None
    naming_problems: list = field(default_factory=list)

    @property
    def code(self):
        suffix = f"-b{self.backup}" if self.backup else ""
        return f"{self.member}-{self.kind}{self.number or '?'}{suffix}"

    @property
    def is_main(self):
        return not self.backup


def pair_paths(raw_root, code):
    """Files of a pair code such as tuan-standard1 or tuan-standard1-b2."""
    match = PAIR_CODE.match(code)
    if not match:
        raise ValueError(f"Invalid pair code '{code}' (expected <member>-<kind><n>[-b<k>])")
    member, kind, number, backup = match.groups()
    suffix = f"_b{backup}" if backup else ""
    folder = Path(raw_root) / member
    return (folder / f"{kind}{number}_left{suffix}.jpg", folder / f"{kind}{number}_right{suffix}.jpg")


def scan_member(folder, member):
    """Group the files of raw/<member>/ into pairs; also return files that match no pattern."""
    pairs, unrecognised = {}, []
    for path in sorted(Path(folder).iterdir()):
        if not path.is_file():
            continue
        lenient = LENIENT_NAME.match(path.name)
        if not lenient:
            unrecognised.append(path.name)
            continue
        kind, number, side, backup, extension = lenient.groups()
        kind = kind.lower()
        key = (kind, number, backup or "")
        pair = pairs.setdefault(key, PairFiles(member, kind, number, backup or ""))
        setattr(pair, side.lower(), path)
        if not STRICT_NAME.match(path.name):
            problems = []
            if not number:
                problems.append("thiếu số thứ tự")
            if not extension:
                problems.append("không có phần mở rộng .jpg")
            elif extension.lower() != "jpg":
                problems.append(f"phần mở rộng .{extension} thay vì .jpg")
            if path.name != path.name.lower():
                problems.append("có chữ hoa")
            pair.naming_problems.append(f"{path.name}: {', '.join(problems) or 'sai quy ước'}")
    return list(pairs.values()), unrecognised


def load_oriented(path):
    """Decode an image and apply its EXIF orientation. Returns (image, exif of the original file)."""
    with Image.open(path) as source:
        source.load()
        exif = source.getexif()
        image_format = source.format
        oriented = ImageOps.exif_transpose(source)
        if oriented is None:  # only returned for in_place=True
            oriented = source.copy()
    return oriented, exif, image_format


def crop_box_16_9(width, height):
    """Largest centred 16:9 box (left, top, right, bottom) inside width x height."""
    if width * 9 >= height * 16:
        crop_w, crop_h = height * 16 // 9, height
        crop_w -= crop_w % 16
        crop_h = crop_w * 9 // 16
    else:
        crop_w = width - width % 16
        crop_h = crop_w * 9 // 16
    left = (width - crop_w) // 2
    top = (height - crop_h) // 2
    return left, top, left + crop_w, top + crop_h


def exif_fields(exif):
    """EXIF fields used by the checks; missing values are None."""
    sub = exif.get_ifd(EXIF_IFD) if exif else {}
    gps = exif.get_ifd(GPS_IFD) if exif else {}
    taken = sub.get(TAG_DATETIME_ORIGINAL)
    try:
        taken = datetime.strptime(str(taken).strip("\x00 "), "%Y:%m:%d %H:%M:%S") if taken else None
    except ValueError:
        taken = None
    zoom = sub.get(TAG_DIGITAL_ZOOM)
    return {
        "make": str(exif.get(TAG_MAKE)).strip("\x00 ") if exif and exif.get(TAG_MAKE) else None,
        "model": str(exif.get(TAG_MODEL)).strip("\x00 ") if exif and exif.get(TAG_MODEL) else None,
        "taken": taken,
        "focal_mm": float(sub[TAG_FOCAL]) if sub.get(TAG_FOCAL) else None,
        "focal_35mm": int(sub[TAG_FOCAL_35]) if sub.get(TAG_FOCAL_35) else None,
        "digital_zoom": float(zoom) if zoom else None,
        "has_gps": bool(gps.get(TAG_GPS_LATITUDE)),
    }
