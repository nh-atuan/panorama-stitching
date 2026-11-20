#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Package committed source only; resolve public SHA or verified offline source without fallback."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

from audit_final_notebook import PIN_FILES
from midterm_notebook import safe_extract, sha256
from package_s6_verification import EXTENSIONS, PREFIXES

MANIFEST = "source_manifest.json"
ROOT_FILES = {"README.md", "Group16_Final.ipynb", "Group16_P11_T06_Acceptance.ipynb"}


def command(root, *args, binary=False):
    process = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace"))
    return process.stdout if binary else process.stdout.decode("utf-8").strip()


def full_sha(value):
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("Expected exact 40-character Git SHA; branches/main are not accepted")
    return value


def required(root):
    missing = [p for p in (*PIN_FILES, "Group16_Final.ipynb") if not (Path(root) / p).is_file()]
    if missing:
        raise ValueError(f"Incomplete source (V0-V5/helpers required): {missing}")


def package(root, ref, output):
    root, output = Path(root), Path(output)
    if output.exists():
        raise FileExistsError(f"Refuse to overwrite source archive: {output}")
    revision = full_sha(command(root, "rev-parse", f"{ref}^{{commit}}"))
    names = command(root, "ls-tree", "-r", "--name-only", revision).splitlines()
    names = [n for n in names if n.split("/", 1)[0] in {*PREFIXES, "docs"} or n in ROOT_FILES]
    # Git archive uses committed blobs, never untracked or modified working-tree files.
    payload_zip = command(root, "archive", "--format=zip", revision, "--", *names, binary=True)
    with zipfile.ZipFile(io.BytesIO(payload_zip)) as bundle:
        entries = [e for e in bundle.infolist() if not e.is_dir()]
        if any((e.external_attr >> 16) & 0o170000 == 0o120000 for e in entries):
            raise ValueError("Source symlinks are unsupported")
        payload = {e.filename: bundle.read(e) for e in entries}
    if not set(PIN_FILES).issubset(payload):
        raise ValueError(f"Revision lacks required source: {set(PIN_FILES) - payload.keys()}")
    hashes = {n: hashlib.sha256(data).hexdigest() for n, data in sorted(payload.items())}
    source_hashes = {n: h for n, h in hashes.items()
                     if n.split("/", 1)[0] in PREFIXES and Path(n).suffix.lower() in EXTENSIONS}
    manifest = dict(schema=1, git_commit=revision, git_branch=ref, source_status="",
                    snapshot_sha256=hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest(),
                    files=source_hashes, payload_files=hashes, packaging="committed Git blobs only")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted({**payload, MANIFEST: (json.dumps(manifest, indent=2) + "\n").encode()}.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    sidecar = dict(source_sha=revision, archive_sha256=sha256(output), archive=output.name)
    output.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    return sidecar


def verify_archive(archive, destination, expected_sha, expected_archive_hash):
    full_sha(expected_sha)
    archive, destination = Path(archive), Path(destination)
    if not expected_archive_hash or sha256(archive) != expected_archive_hash:
        raise ValueError("Source ZIP SHA-256 mismatch; copy the .json sidecar value")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("Extract source into a new empty directory; never replace a checkout")
    with zipfile.ZipFile(archive) as bundle:
        if sum(e.file_size for e in bundle.infolist()) > 256 * 1024 * 1024:
            raise ValueError("Source archive exceeds 256 MiB uncompressed budget")
        manifest = json.loads(bundle.read(MANIFEST))
        if manifest["git_commit"] != expected_sha:
            raise ValueError("Source manifest Git SHA differs from requested revision")
        names = [e.filename for e in bundle.infolist() if not e.is_dir()]
        if len(names) != len(set(names)) or set(names) != set(manifest["payload_files"]) | {MANIFEST}:
            raise ValueError("Archive payload inventory differs from manifest")
    safe_extract(archive, destination)
    verify_tree(destination, expected_sha)
    return manifest


def verify_tree(root, expected_sha):
    root = Path(root)
    full_sha(expected_sha)
    required(root)
    if (root / MANIFEST).is_file():
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        if manifest["git_commit"] != expected_sha:
            raise ValueError("Extracted source revision mismatch")
        tracked_payload = {p.relative_to(root).as_posix() for prefix in (*PREFIXES, "docs")
                           for p in (root / prefix).rglob("*")
                           if p.is_file() and "__pycache__" not in p.parts}
        expected_payload = {n for n in manifest["payload_files"]
                            if n.split("/", 1)[0] in {*PREFIXES, "docs"}}
        if tracked_payload != expected_payload:
            raise ValueError("Extracted source inventory changed")
        for name, digest in manifest["payload_files"].items():
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file() or sha256(path) != digest:
                raise ValueError(f"Source payload checksum mismatch: {name}")
    else:
        if command(root, "rev-parse", "HEAD") != expected_sha:
            raise ValueError("Checkout SHA mismatch; no fallback to main allowed")
        if command(root, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError("Tracked source is modified; use a clean exact checkout")
    return expected_sha


def published(root, repo_url, revision):
    root = Path(root)
    full_sha(revision)
    if root.exists():
        raise FileExistsError("Published source destination must not exist")
    root.mkdir(parents=True)
    command(root, "init")
    command(root, "fetch", "--depth", "1", repo_url, revision)
    command(root, "checkout", "--detach", "FETCH_HEAD")
    return verify_tree(root, revision)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.root, args.ref, args.output), indent=2))
