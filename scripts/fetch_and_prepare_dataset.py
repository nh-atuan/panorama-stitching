#!/usr/bin/env python3
# Authors: Nguyen Ho Anh Tuan (23120185), Tran Huu Kim Thanh (23120166)
# External source: none

"""Fetch raw dataset from Google Drive and prepare final dataset for CSC14120.

This script automates the complete dataset pipeline chosed on 03/11:
1. Downloads the raw photos folder from Google Drive (folder ID: 127SOMhoY2EwBbkCxGWGPju-EbmG0QiOq).
2. Standardizes filenames (e.g. standard2_left.jpg for Thanh, challenge1_left.jpg for De).
3. Invokes prepare_dataset.py to crop 16:9 and resize to small, medium, large.
4. Generates dataset/manifest.csv and packages dataset.zip for Drive upload.

Example (on Google Colab or local machine with gdown and Pillow):
    python scripts/fetch_and_prepare_dataset.py --out dataset --zip dataset.zip
"""

import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

RAW_DRIVE_FOLDER_ID = "127SOMhoY2EwBbkCxGWGPju-EbmG0QiOq"
CHOSEN_PAIRS = [
    ("site1", "thanh-standard1"),
    ("site2", "thanh-standard2"),
    ("site3", "de-standard2"),
    ("challenge", "de-challenge1"),
]


def ensure_gdown():
    if importlib.util.find_spec("gdown") is None:
        print("[dataset] Installing gdown...", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gdown"], check=True)


def download_raw(raw_dir: Path):
    import gdown

    raw_dir.mkdir(parents=True, exist_ok=True)
    print(f"[dataset] Downloading raw folder from Google Drive ({RAW_DRIVE_FOLDER_ID})...", flush=True)
    url = f"https://drive.google.com/drive/folders/{RAW_DRIVE_FOLDER_ID}?usp=sharing"
    gdown.download_folder(url=url, output=str(raw_dir), quiet=False, use_cookies=False)


def normalize_raw_names(raw_dir: Path):
    """Normalize file extensions and missing pair indexes in raw folder."""
    # 1. Normalize Thanh's files
    thanh_dir = raw_dir / "thanh"
    if thanh_dir.is_dir():
        for path in thanh_dir.iterdir():
            if not path.is_file():
                continue
            # Handle files downloaded without .jpg extension
            if not path.suffix:
                new_path = path.with_suffix(".jpg")
                if not new_path.exists():
                    path.rename(new_path)
                    print(f"[normalize] Renamed {path.name} -> {new_path.name}")

    # 2. Normalize De's files
    de_dir = raw_dir / "de"
    if de_dir.is_dir():
        for path in de_dir.iterdir():
            if not path.is_file():
                continue
            stem, suffix = path.stem, path.suffix.lower()
            # Rename .jpeg -> .jpg
            target_suffix = ".jpg" if suffix in (".jpeg", "") else suffix
            # Fix challenge_left / challenge_right -> challenge1_left / challenge1_right
            target_stem = stem
            if target_stem == "challenge_left":
                target_stem = "challenge1_left"
            elif target_stem == "challenge_right":
                target_stem = "challenge1_right"
            new_path = de_dir / f"{target_stem}{target_suffix}"
            if new_path != path:
                if not new_path.exists():
                    path.rename(new_path)
                    print(f"[normalize] Renamed {path.name} -> {new_path.name}")


def run_prepare_dataset(raw_dir: Path, out_dir: Path):
    script = Path(__file__).resolve().parent / "prepare_dataset.py"
    cmd = [
        sys.executable,
        str(script),
        "--raw", str(raw_dir),
        "--out", str(out_dir),
    ]
    for site, code in CHOSEN_PAIRS:
        cmd.extend(["--pair", f"{site}={code}"])

    print(f"[dataset] Running prepare_dataset.py...", flush=True)
    subprocess.run(cmd, check=True)


def package_zip(out_dir: Path, zip_path: Path):
    print(f"[dataset] Packaging {out_dir} into {zip_path}...", flush=True)
    archive_base = zip_path.with_suffix("")
    shutil.make_archive(str(archive_base), "zip", root_dir=str(out_dir))
    print(f"[dataset] Successfully created {zip_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", default="raw", type=Path, help="Path for raw photos directory")
    parser.add_argument("--out", default="dataset", type=Path, help="Output directory for prepared dataset")
    parser.add_argument("--skip-download", action="store_true", help="Skip Google Drive download if raw/ exists")
    parser.add_argument("--zip", type=Path, default=None, help="Optional output zip file path")
    args = parser.parse_args()

    if not args.skip_download:
        ensure_gdown()
        download_raw(args.raw)

    normalize_raw_names(args.raw)
    run_prepare_dataset(args.raw, args.out)

    if args.zip:
        package_zip(args.out, args.zip)

    print("[dataset] Final dataset preparation complete!")


if __name__ == "__main__":
    main()
