#!/usr/bin/env python3
# Authors: Le Ha Thanh Chuong (23120195)
# External source: none

"""Export saved executed outputs via nbconvert HTML + Chromium; retain fallback logs and QA."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil
import traceback
import unicodedata

from audit_final_notebook import SECTIONS
from midterm_notebook import sha256
from profiling_common import write_json

PRINT_CSS = """
@page { size: A4 landscape; margin: 12mm; }
body { color: #111; background: white; font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 10.5pt; }
main, .jp-Notebook { width: auto !important; max-width: none !important; padding: 0 !important; }
.jp-Cell { overflow: visible !important; }
.jp-OutputArea-output, .jp-RenderedHTMLCommon { overflow: visible !important; }
table { width: 100%; font-size: 9pt; border-collapse: collapse; }
td, th { overflow-wrap: anywhere; padding: 4px; }
tr, figure, img, mjx-container { break-inside: avoid; }
thead { display: table-header-group; }
pre, code { white-space: pre-wrap !important; overflow-wrap: anywhere; font-size: 9pt; }
img, svg { max-width: 100% !important; height: auto; }
img { max-height: 170mm; object-fit: contain; }
h1, h2, h3, h4 { break-after: avoid; }
.jp-InputPrompt, .jp-OutputPrompt { min-width: 32px; font-size: 8pt; }
"""


def dependencies():
    return dict(modules={m: importlib.util.find_spec(m) is not None
                         for m in ("nbformat", "nbconvert", "playwright", "pypdf")},
                latex={t: shutil.which(t) for t in ("xelatex", "pandoc")})


def executed_notebook(path):
    import nbformat
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    if not cells or [c.execution_count for c in cells] != list(range(1, len(cells) + 1)):
        raise ValueError("PDF requires a complete, ordered executed notebook (counts 1..N)")
    for cell in cells:
        if any(o.output_type == "error" for o in cell.outputs):
            raise ValueError("Notebook contains error outputs; preserve failure evidence, do not export as final")
        if re.search(r"\b(?:display|print)\(", cell.source) and not cell.outputs:
            raise ValueError("Visible output is missing; PDF export must not erase or skip outputs")
    return notebook


def normalized(text):
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def inspect_pdf(path, expected_sections=SECTIONS, expect_raster=False):
    from pypdf import PdfReader
    path = Path(path)
    if not path.is_file() or path.stat().st_size < 100 or not path.read_bytes().startswith(b"%PDF-"):
        raise ValueError("Missing, empty or invalid PDF header")
    reader = PdfReader(path, strict=True)
    if not reader.pages:
        raise ValueError("PDF has no pages")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    missing = [s for s in expected_sections if normalized(s) not in normalized(text)]
    figures = sum(len(page.images) for page in reader.pages)
    problems = []
    if missing:
        problems.append(f"Missing PDF headings: {missing}")
    if not text.strip() or "\ufffd" in text or "\u25a1" in text:
        problems.append("Empty text or possible Unicode replacement glyphs")
    if expect_raster and figures == 0:
        problems.append("Raster notebook outputs exist but PDF contains no image objects")
    result = dict(pages=len(reader.pages), size_bytes=path.stat().st_size, sha256=sha256(path),
                  missing_headings=missing, raster_images=figures, problems=problems,
                  visual_review="pending: inspect rendered pages for clipping, tables, math and captions")
    path.with_suffix(".txt").write_text(text, encoding="utf-8")
    return result


def browser_pdf(html, output, browser_path=None):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as driver:
        options = dict(headless=True, args=["--no-sandbox"])
        if browser_path:
            options["executable_path"] = str(browser_path)
        browser = driver.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={"width": 1120, "height": 800})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(Path(html).resolve().as_uri(), wait_until="networkidle", timeout=90000)
            page.add_style_tag(content=PRINT_CSS)
            has_math = page.locator(".math").count() > 0
            if has_math:
                page.wait_for_function("window.MathJax && window.MathJax.startup && window.MathJax.typesetPromise", timeout=60000)
                page.evaluate("async () => { await MathJax.startup.promise; await MathJax.typesetPromise(); }")
                if not page.locator("mjx-container").count():
                    raise RuntimeError("MathJax produced no rendered equations; refuse raw TeX PDF")
            page.evaluate("() => document.fonts.ready")
            page.wait_for_function("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)", timeout=30000)
            if page.locator("mjx-merror, [data-mjx-error]").count():
                raise RuntimeError("MathJax reported an equation rendering error")
            if errors:
                raise RuntimeError(f"HTML JavaScript rendering errors: {errors}")
            widths = page.evaluate("""() => Array.from(document.querySelectorAll('table,pre,img'))
                .filter(e => e.getBoundingClientRect().right > innerWidth)
                .map(e => ({tag:e.tagName, width:e.getBoundingClientRect().width}))""")
            page.pdf(path=str(output), prefer_css_page_size=True, print_background=True)
            return dict(math_rendered=page.locator("mjx-container").count(),
                        html_images=page.locator("img").count(), clipping_candidates=widths)
        finally:
            browser.close()


def export(notebook_path, directory, smoke=False, browser_path=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / ("Group16_PDF_Smoke.pdf" if smoke else "Group16_Final.pdf")
    if output.exists() or (directory / "pdf_export.json").exists():
        raise FileExistsError("Use a new export directory; never overwrite earlier PDF evidence")
    report = dict(status="failed", started_utc=datetime.now(timezone.utc).isoformat(),
                  dependencies=dependencies(), input_sha256=sha256(notebook_path), smoke=smoke, attempts=[])
    try:
        notebook = executed_notebook(notebook_path)
        from nbconvert import HTMLExporter
        exporter = HTMLExporter(embed_images=True)
        exporter.mathjax_url = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg-full.js"
        html, _ = exporter.from_notebook_node(notebook, resources={"metadata": {"path": str(Path(notebook_path).parent)}})
        html_path = directory / "Group16_Final.html"
        html_path.write_text(html, encoding="utf-8")
        try:
            details = browser_pdf(html_path, output, browser_path)
            report["attempts"].append(dict(engine="chromium-html", status="passed", **details))
        except Exception:
            (directory / "chromium-error.log").write_text(traceback.format_exc(), encoding="utf-8")
            report["attempts"].append(dict(engine="chromium-html", status="failed", log="chromium-error.log"))
            # Explicit fallback keeps executed outputs and uses XeLaTeX's Unicode support.
            if not all(report["dependencies"]["latex"].values()):
                raise RuntimeError("Chromium failed; fallback needs pandoc + xelatex. See retained HTML/log.")
            from nbconvert import PDFExporter
            try:
                fallback = PDFExporter()
                fallback.latex_command = ["xelatex", "-interaction=nonstopmode", "{filename}"]
                pdf, _ = fallback.from_notebook_node(notebook)
                output.write_bytes(pdf)
                report["attempts"].append(dict(engine="xelatex", status="passed"))
            except Exception:
                (directory / "xelatex-error.log").write_text(traceback.format_exc(), encoding="utf-8")
                raise
        raster = any(any(key.startswith("image/") and key != "image/svg+xml" for key in o.get("data", {}))
                     for c in notebook.cells if c.cell_type == "code" for o in c.outputs)
        report["qa"] = inspect_pdf(output, () if smoke else SECTIONS, raster)
        report["status"] = "qa_failed" if report["qa"]["problems"] else "exported_visual_review_pending"
        return report
    except Exception as error:
        report["error"] = str(error)
        (directory / "pdf-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        write_json(directory / "pdf_export.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path, nargs="?")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--check-deps", action="store_true")
    args = parser.parse_args()
    if args.check_deps:
        print(json.dumps(dependencies(), indent=2))
    elif not args.notebook or not args.output_dir:
        parser.error("notebook and --output-dir are required")
    else:
        result = export(args.notebook, args.output_dir, args.smoke, args.browser)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(int(result["status"] != "exported_visual_review_pending"))
