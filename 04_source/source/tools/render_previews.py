#!/usr/bin/env python3
"""Render preview PNGs + extracted-text对照 for T002 evidence.

For each selected case, renders the first page and the fault page:
  * TEXT pages: re-drawn from the fixture spec lines with Pillow
    (Noto Sans CJK for CJK lines, DejaVu Sans for Latin lines).
  * IMAGE pages: the embedded raster image is extracted from the PDF
    itself (pypdf page.images), so the preview shows exactly what a
    reader sees on the scanned page.
Also writes <case_id>-extracted.txt with the pypdf extraction of the
rendered pages, so text rendering can be checked against the spec.

Usage (from PACKAGE_ROOT):
    python tools/render_previews.py --cases po-ext-01 po-ext-02 ... \
        --out ../../07_evidence/t002-previews
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

DEFAULT_CASES = [
    "po-ext-01", "po-ext-02",
    "mm-ext-01", "mm-ext-02",
    "du-chk-01", "du-chk-02",
    "un-ext-01", "un-ext-02",
]

CJK_FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
]
LATIN_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _font(path, size, index=0):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()


def _cjk_font(size):
    for path in CJK_FONT_PATHS:
        try:
            from PIL import ImageFont
            return ImageFont.truetype(path, size, index=0)
        except Exception:
            continue
    from PIL import ImageFont
    return ImageFont.load_default()


def _is_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def render_text_page(case_id: str, page: dict) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 1200, 1714], outline="black", width=3)
    header = _font(LATIN_FONT_PATH, 30)
    draw.text((80, 70), f"{case_id}  -  page index0 {page['pdf_page_index0']} "
                        f"(label {page['pdf_page_label']}, {page['kind']})",
              fill="black", font=header)
    y = 170
    for line in page["lines"]:
        font = _cjk_font(34) if _is_cjk(line) else _font(LATIN_FONT_PATH, 30)
        # Simple wrap at ~30 CJK chars / ~62 Latin chars.
        width = 30 if _is_cjk(line) else 62
        while len(line) > width:
            draw.text((80, y), line[:width], fill="black", font=font)
            y += 60
            line = line[width:]
        draw.text((80, y), line, fill="black", font=font)
        y += 60
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render T002 preview evidence.")
    parser.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    parser.add_argument("--fixtures", default="fixtures")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    fixtures = Path(args.fixtures)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    from pypdf import PdfReader

    for case_id in args.cases:
        spec = json.loads((fixtures / "specs" / f"{case_id}.json")
                          .read_text(encoding="utf-8"))
        pdf_path = fixtures / "pdfs" / f"{case_id}.pdf"
        reader = PdfReader(str(pdf_path))
        fault_pages = spec["fault_citation"]["true_source_pages0"]
        render_idx = sorted({0, *fault_pages})
        extracted_lines = []
        for k in render_idx:
            page = spec["pages"][k]
            if page["kind"] == "image":
                images = reader.pages[k].images
                assert images, f"{case_id} p{k}: no embedded image"
                png = images[0].data
                note = (f"[image page: embedded raster extracted from PDF; "
                        f"visible text: {page['image_visible_text']!r}]")
            else:
                png = render_text_page(case_id, page)
                note = ""
            (out / f"{case_id}-p{k}.png").write_bytes(png)
            text = reader.pages[k].extract_text() or ""
            extracted_lines.append(
                f"=== {case_id} page index0 {k} "
                f"(label {page['pdf_page_label']}, kind {page['kind']}) ===")
            if note:
                extracted_lines.append(note)
            extracted_lines.append(text)
            print(f"preview {case_id} p{k} ({page['kind']})")
        (out / f"{case_id}-extracted.txt").write_text(
            "\n".join(extracted_lines) + "\n", encoding="utf-8")
    print(f"previews written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
