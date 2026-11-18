#!/usr/bin/env python3
"""P026 PageTrace — deterministic synthetic fixture generator (T002).

Generates 48 deterministic PDFs + fixture specs + pagetrace.bundle/v1
trace bundles, covering the PROJECT_BOOK.md v1.0.0 §8.1 matrix:

  PAGE_OFFSET (12) · PAGE_METADATA_MISSING (12) ·
  DUPLICATE_TEXT_AMBIGUITY (12) · UNLOCATABLE (12)

Determinism rules (no wall-clock, no randomness, no network):
  * Fixed PDF metadata (CreationDate / ModDate pinned, fixed Title /
    Creator / Producer); the final bytes are produced by pypdf, whose
    writer output was verified byte-identical across separate processes.
  * Chinese text uses ReportLab's built-in CID font ``STSong-Light``
    (no font file is embedded and nothing is downloaded); Latin text
    uses built-in Helvetica. Image pages are Pillow rasters drawn with
    the system Noto Sans CJK font (raster only — the PDF carries no
    text layer on those pages, which is exactly the point).
  * JSON is written with sort_keys=True, indent=2, UTF-8, trailing LF.
  * Page content is derived from the case index only (no RNG).

Fault model: the PDF itself is always ground truth. The fault is
implanted in the *trace* (stage snapshots in the bundle), never by
editing PDF bytes by hand. Each case also carries >= 1 control
citation whose trace is correct end-to-end.

FIX-R1 P1-R1-02: near-miss UNLOCATABLE cases (``near-miss-quote``)
carry ``first_fault_stage=None`` / ``expected_source_pages0=None``
(no stage can be blamed without a provable extraction failure;
PROJECT_BOOK §5 / §7.2 / §7.3), and every UNLOCATABLE case is
guaranteed >= 1 image-style / text-less page (PROJECT_BOOK §8.1).

Usage (from PACKAGE_ROOT, i.e. 04_source/source):
    python tools/generate_fixtures.py --out fixtures
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixed constants
# ---------------------------------------------------------------------------

GENERATOR_VERSION = "t002-1.0.0"
FIXED_CREATION_DATE = "D:20260101000000Z"
FIXED_MOD_DATE = "D:20260101000000Z"
FIXED_TITLE_PREFIX = "PageTrace synthetic fixture"
PAGE_WIDTH, PAGE_HEIGHT = 595.27, 841.89  # A4 in points
MARGIN = 72.0
CJK_FONT = "STSong-Light"
LATIN_FONT = "Helvetica"

FAULT_TYPES = (
    "PAGE_OFFSET",
    "PAGE_METADATA_MISSING",
    "DUPLICATE_TEXT_AMBIGUITY",
    "UNLOCATABLE",
)

# ---------------------------------------------------------------------------
# Text normalisation (PROJECT_BOOK §4.2)
# ---------------------------------------------------------------------------


def norm_text(text: str) -> str:
    """NFC, CRLF/CR -> LF, collapse every whitespace run to one space."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sha256_hex(text: str) -> str:
    return hashlib.sha256(norm_text(text).encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


# ---------------------------------------------------------------------------
# Sentence pools (each line is short enough to fit on one drawn line, so a
# quote is always exactly one extracted line after normalisation).
# ---------------------------------------------------------------------------

CN_SENTENCES = [
    "本页讨论引用页码漂移的成因与检测方法。",
    "读者按引用页码查找原文时常常翻到错误页面。",
    "页码基准混用是引用系统最常见的隐性缺陷。",
    "物理页与印刷页号本是两套不同的计数体系。",
    "扫描件页面没有文本层，引用无法用文本定位。",
    "空白页应当诚实标记，不应被当作内容页处理。",
    "跨页断句需要把前后两页都记为来源页集合。",
    "重复出现的句子必须保留全部候选页，不得猜一页。",
    "页标签只是辅助标识，不能代替物理页身份。",
    "索引重建时丢失来源页集合会使引用无据可查。",
    "展示层把零基索引直接交给阅读器必然错位一页。",
    "同一句话出现在多页时，消歧需要可靠的页级锚点。",
]

EN_SENTENCES = [
    "Page numbers drift when extraction, chunking and display disagree.",
    "A citation is only as good as the page it points to.",
    "The viewer expects one-based pages; the index stores zero-based.",
    "Roman numerals are labels, not numbers to do arithmetic on.",
    "A blank page is evidence of nothing, and must be marked as such.",
    "When a sentence spans two pages, both pages are the source.",
    "Losing the source set in the index breaks every later check.",
    "An image-only page carries no text layer to search.",
]

# Cross-page sentence halves (drawn on two adjacent pages).
SPLIT_FIRST = "跨页长句前半部分：引用内容在翻页处断开，"
SPLIT_SECOND = "后半部分接续于此，合起来才是一句完整引用。"


def fault_quote(case_id: str) -> str:
    return f"关键引文{case_id}：页码漂移误导定位。"


def control_quote(case_id: str) -> str:
    return f"对照引文{case_id}：本页引用页码正确无误。"


def duplicate_sentence(case_id: str) -> str:
    return f"重复句{case_id}：本句在多页出现，须保留全部候选页。"


def near_miss_sentence(case_id: str) -> str:
    return f"近似句{case_id}：引用页码漂移会误导读者定位原文。"


def near_miss_quote(case_id: str) -> str:
    # One character differs from near_miss_sentence (原文 -> 正文).
    return f"近似句{case_id}：引用页码漂移会误导读者定位正文。"


def image_visible_text(case_id: str) -> str:
    return f"图像页文字{case_id}：仅见于扫描图像，无文本层。"


# ---------------------------------------------------------------------------
# Page labels
# ---------------------------------------------------------------------------

ROMAN_LOWER = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii"]


def page_labels(scheme: str, n_pages: int) -> list[str]:
    """Return one label per physical page (0-based order)."""
    if scheme == "decimal":
        return [str(k + 1) for k in range(n_pages)]
    if scheme == "roman":
        return ROMAN_LOWER[:n_pages]
    if scheme == "roman-decimal":
        labels = ROMAN_LOWER[:2]
        labels += [str(k + 1) for k in range(n_pages - 2)]
        return labels
    if scheme == "alpha-prefix":
        return [f"A-{k + 1}" for k in range(n_pages)]
    if scheme == "label-7":
        # PAGE_SEMANTICS.md example E: physical page 0 carries label "7".
        return [str(7 + k) for k in range(n_pages)]
    raise ValueError(f"unknown label scheme: {scheme}")


def label_ranges(scheme: str, n_pages: int) -> list[tuple[int, int, str, str, int]]:
    """(from, to, style, prefix, start) ranges for pypdf set_page_label."""
    if scheme == "decimal":
        return [(0, n_pages - 1, "/D", "", 1)]
    if scheme == "roman":
        return [(0, n_pages - 1, "/r", "", 1)]
    if scheme == "roman-decimal":
        ranges = [(0, 1, "/r", "", 1)]
        if n_pages > 2:
            ranges.append((2, n_pages - 1, "/D", "", 1))
        return ranges
    if scheme == "alpha-prefix":
        return [(0, n_pages - 1, "/D", "A-", 1)]
    if scheme == "label-7":
        return [(0, n_pages - 1, "/D", "", 7)]
    raise ValueError(f"unknown label scheme: {scheme}")


# ---------------------------------------------------------------------------
# Case table
# ---------------------------------------------------------------------------

# (within-category index -> (stage, variant)) per fault type.
PO_PLAN = [
    ("extraction", "plus-one-shift"),
    ("extraction", "minus-one-shift"),
    ("extraction", "swap-with-distant-page"),
    ("chunking", "number1-used-as-index0"),
    ("chunking", "index0-minus-one"),
    ("chunking", "roman-label-read-as-number"),
    ("indexing", "plus-one-shift"),
    ("indexing", "minus-one-shift"),
    ("indexing", "label-A3-read-as-index3"),
    ("display", "index0-passed-to-viewer"),
    ("display", "plus-one-extra"),
    ("display", "label-7-read-as-number1"),
]

MM_PLAN = [
    ("extraction", "record-text-state-error"),
    ("extraction", "record-hash-omitted"),
    ("extraction", "record-omitted"),
    ("chunking", "source-pages-emptied"),
    ("chunking", "chunk-record-absent"),
    ("chunking", "chunk-text-hash-omitted"),
    ("indexing", "source-pages-emptied"),
    ("indexing", "index-record-absent"),
    ("indexing", "label-dropped-on-rebuild"),
    ("display", "display-record-absent"),
    ("display", "page-value-missing"),
    ("display", "viewer-page-missing"),
]

DU_PLAN = [
    ("chunking", "reduce-to-first"),
    ("chunking", "reduce-to-last"),
    ("chunking", "reduce-to-middle"),
    ("chunking", "reduce-to-first-again"),
    ("indexing", "reduce-to-first"),
    ("indexing", "reduce-to-last"),
    ("indexing", "reduce-to-middle"),
    ("indexing", "reduce-to-last-again"),
    ("display", "reduce-to-first"),
    ("display", "reduce-to-last"),
    ("display", "reduce-to-middle"),
    ("display", "reduce-to-first-again"),
]

UN_PLAN = [
    ("extraction", "image-only-page") for _ in range(4)
] + [
    ("extraction", "blank-page") for _ in range(4)
] + [
    ("extraction", "near-miss-quote") for _ in range(4)
]

PLANS = {
    "PAGE_OFFSET": PO_PLAN,
    "PAGE_METADATA_MISSING": MM_PLAN,
    "DUPLICATE_TEXT_AMBIGUITY": DU_PLAN,
    "UNLOCATABLE": UN_PLAN,
}

PREFIX = {
    "PAGE_OFFSET": "po",
    "PAGE_METADATA_MISSING": "mm",
    "DUPLICATE_TEXT_AMBIGUITY": "du",
    "UNLOCATABLE": "un",
}

STAGE_ABBR = {
    "extraction": "ext",
    "chunking": "chk",
    "indexing": "idx",
    "display": "dsp",
}

EXPECTED_VERDICT = {
    "PAGE_OFFSET": "FAIL_PAGE_OFFSET",
    "PAGE_METADATA_MISSING": "FAIL_METADATA_MISSING",
    "DUPLICATE_TEXT_AMBIGUITY": "FAIL_AMBIGUOUS",
    "UNLOCATABLE": "FAIL_UNLOCATABLE",
}


def build_cases() -> list[dict]:
    """Build the 48 case definitions (human-authored matrix, §8.1)."""
    cases: list[dict] = []
    idx = 0
    for fault_type in FAULT_TYPES:
        plan = PLANS[fault_type]
        for j, (stage, variant) in enumerate(plan):
            case_id = f"{PREFIX[fault_type]}-{STAGE_ABBR[stage]}-{j + 1:02d}"
            cases.append(_build_case(idx, case_id, fault_type, stage, variant, j))
            idx += 1
    return cases


def _build_case(i: int, case_id: str, fault_type: str, stage: str,
                variant: str, j: int) -> dict:
    # FIX-R1 P1-R1-02: a near-miss UNLOCATABLE quote (one character
    # off the sentence on a TEXT anchor page, honest extraction) has
    # no attributable first fault stage and no confirmed source page.
    is_near_miss = (fault_type == "UNLOCATABLE"
                    and variant == "near-miss-quote")
    n_pages = 5 + (i % 4)  # 5..8 physical pages
    # True fault page: kept in [1, n-2] so +/-1 neighbours always exist.
    tp = 1 + ((i * 3 + 1) % (n_pages - 2))
    cp = (tp + 2) % n_pages  # control page (single-page control)
    if fault_type == "PAGE_OFFSET" and variant == "label-7-read-as-number1":
        # PAGE_SEMANTICS.md example E: physical page 0 carries label "7".
        tp, cp = 0, 2

    # Label scheme: cycle the four schemes; a few cases pin one scheme
    # because their fault mechanism needs it.
    scheme = ["decimal", "roman", "roman-decimal", "alpha-prefix"][i % 4]
    if fault_type == "PAGE_OFFSET" and stage == "display" and variant == "label-7-read-as-number1":
        scheme = "label-7"
    if fault_type == "PAGE_OFFSET" and stage == "chunking" and variant == "roman-label-read-as-number":
        scheme = "roman"
    if fault_type == "PAGE_OFFSET" and stage == "indexing" and variant == "label-A3-read-as-index3":
        scheme = "alpha-prefix"
    labels = page_labels(scheme, n_pages)

    # Occurrence pages for the duplicate sentence.
    occ: list[int] = []
    if fault_type == "DUPLICATE_TEXT_AMBIGUITY":
        if j % 2 == 0:
            occ = sorted({tp, (tp + 2) % n_pages})
        else:
            occ = sorted({tp, (tp + 2) % n_pages, (tp + 3) % n_pages})

    # Cross-page control: a split sentence on two adjacent TEXT pages.
    # Used on odd-index cases when the pages are free (not fault/control/
    # occurrence pages); then the control citation spans both pages (R-10).
    split_pages: list[int] = []
    if i % 2 == 1:
        sp = (cp + 1) % n_pages
        sp2 = (sp + 1) % n_pages
        blocked = {tp, cp} | set(occ)
        if sp not in blocked and sp2 not in blocked and sp2 != sp:
            split_pages = [sp, sp2]

    # Page kinds.
    kind: dict[int, str] = {k: "text" for k in range(n_pages)}
    if fault_type == "UNLOCATABLE" and variant == "image-only-page":
        kind[tp] = "image"
    elif fault_type == "UNLOCATABLE" and variant == "blank-page":
        kind[tp] = "blank"
    else:
        # Blank page (even cases) and image page (every third case) for
        # structural coverage, placed on pages free of citations.
        blocked = {tp, cp} | set(occ) | set(split_pages)
        if fault_type == "PAGE_OFFSET" and stage == "extraction":
            # The +/-1 extraction fault swaps text hashes with tp-1/tp+1,
            # so those neighbours must be TEXT pages.
            blocked |= {tp - 1, tp + 1} & set(range(n_pages))
        free = [k for k in range(n_pages) if k not in blocked]
        if i % 2 == 0 and free:
            kind[free[0]] = "blank"
        free = [k for k in range(n_pages) if k not in blocked and kind[k] == "text"]
        if i % 3 == 0 and free:
            kind[free[-1]] = "image"

    # FIX-R1 P1-R1-02 (§8.1): every UNLOCATABLE case must contain at
    # least one image-style / text-less page. Near-miss cases have no
    # fault page of their own (the near-miss sentence sits on a TEXT
    # anchor page), and the structural blank/image rules above fire
    # only on even / every-third case indices — un-ext-12 (i=47) got
    # neither. If no non-text page exists yet, turn the last free
    # page (never the anchor page, never a control page, never a
    # split/occurrence page) into a blank page.
    if is_near_miss and not any(k != "text" for k in kind.values()):
        blocked = {tp, cp} | set(occ) | set(split_pages)
        free = [k for k in range(n_pages) if k not in blocked]
        assert free, f"{case_id}: no free page for §8.1 non-text page"
        kind[free[-1]] = "blank"

    # Non-cited duplicate sentence (extra structural coverage) on two
    # free TEXT pages, only when the fault quote is not itself duplicated.
    extra_dup_pages: list[int] = []
    if fault_type != "DUPLICATE_TEXT_AMBIGUITY" and i % 3 == 1:
        free = [k for k in range(n_pages)
                if k not in ({tp, cp} | set(occ) | set(split_pages))
                and kind[k] == "text"]
        if len(free) >= 2:
            extra_dup_pages = [free[0], free[-1]]

    # ---- Page lines ------------------------------------------------------
    pages: list[dict] = []
    fq = fault_quote(case_id)
    cq = control_quote(case_id)
    dup = duplicate_sentence(case_id)
    for k in range(n_pages):
        lines: list[str] = []
        image_text: str | None = None
        if k == 0:
            lines.append(f"PageTrace 合成案例 {case_id}")
            # FIX-R1 P1-R1-02: a near-miss UNLOCATABLE has no
            # attributable stage (null) — the page-0 header must not
            # claim "首错阶段 extraction".
            stage_label = ("未定（无阶段可归咎）" if is_near_miss else stage)
            lines.append(f"故障类别 {fault_type} · 首错阶段 {stage_label}")
        if kind[k] == "text":
            lines.append(CN_SENTENCES[(i + k) % len(CN_SENTENCES)])
            lines.append(EN_SENTENCES[(i + k) % len(EN_SENTENCES)])
            lines.append(CN_SENTENCES[(i + 2 * k + 3) % len(CN_SENTENCES)])
            if k in split_pages:
                lines.append(SPLIT_FIRST if k == split_pages[0] else SPLIT_SECOND)
            if fault_type == "DUPLICATE_TEXT_AMBIGUITY" and k in occ:
                lines.append(dup)
            elif fault_type == "UNLOCATABLE" and variant == "near-miss-quote" and k == tp:
                lines.append(near_miss_sentence(case_id))
            elif k == tp:
                lines.append(fq)
            if k in extra_dup_pages:
                lines.append(dup)
            if not split_pages and k == cp:
                lines.append(cq)
            lines.append(f"第 {k + 1} 页 / 共 {n_pages} 页")
        elif kind[k] == "image":
            image_text = (
                fq if (fault_type == "UNLOCATABLE" and variant == "image-only-page"
                       and k == tp)
                else f"图像页文字{case_id}：本页为扫描图像，无文本层。"
            )
        # Blank pages carry no lines at all.
        pages.append({
            "pdf_page_index0": k,
            "pdf_page_label": labels[k],
            "kind": kind[k],
            "lines": lines,
            "image_visible_text": image_text,
        })

    # ---- Citation truth --------------------------------------------------
    if split_pages:
        control_pages = split_pages
        control_text = SPLIT_FIRST + SPLIT_SECOND
    else:
        control_pages = [cp]
        control_text = cq

    if fault_type == "DUPLICATE_TEXT_AMBIGUITY":
        fault_pages = occ
        fault_text = dup
    elif fault_type == "UNLOCATABLE" and variant == "image-only-page":
        fault_pages = [tp]
        fault_text = fq  # visible only inside the raster image
    elif fault_type == "UNLOCATABLE" and variant == "blank-page":
        fault_pages = [tp]
        fault_text = fq  # appears nowhere in the PDF
    elif fault_type == "UNLOCATABLE" and variant == "near-miss-quote":
        fault_pages = [tp]
        fault_text = near_miss_quote(case_id)
    else:
        fault_pages = [tp]
        fault_text = fq

    # The page the faulty trace wrongly claims (PAGE_OFFSET / DUPLICATE).
    wrong_page: int | None = None
    if fault_type == "PAGE_OFFSET":
        if variant in ("plus-one-shift", "number1-used-as-index0",
                       "roman-label-read-as-number", "label-A3-read-as-index3"):
            wrong_page = tp + 1
        elif variant in ("minus-one-shift", "index0-minus-one"):
            wrong_page = tp - 1
        elif variant == "swap-with-distant-page":
            # Partner must be a TEXT page (blank/image pages have no text
            # hash to swap); first TEXT page at distance >= 3, else any
            # other TEXT page. Recomputed here because kinds are known.
            partner = None
            for cand in range(n_pages):
                m = (tp + 3 + cand) % n_pages
                if m != tp and m != cp and pages[m]["kind"] == "text":
                    partner = m
                    break
            assert partner is not None
            wrong_page = partner
        elif variant == "index0-passed-to-viewer":
            wrong_page = tp  # value is right, viewer conversion is wrong
        elif variant == "plus-one-extra":
            wrong_page = tp + 1
        elif variant == "label-7-read-as-number1":
            wrong_page = tp  # label value 7 misread as viewer page 7
    elif fault_type == "DUPLICATE_TEXT_AMBIGUITY":
        picks = {
            "reduce-to-first": occ[0],
            "reduce-to-last": occ[-1],
            "reduce-to-middle": occ[len(occ) // 2],
            "reduce-to-first-again": occ[0],
            "reduce-to-last-again": occ[-1],
        }
        wrong_page = picks[variant]

    case: dict = {
        "case_id": case_id,
        "fault_type": fault_type,
        # FIX-R1 P1-R1-02: near-miss UNLOCATABLE has no attributable
        # stage (PROJECT_BOOK §5 / §7.2 / §7.3) — null, not "extraction".
        "first_fault_stage": None if is_near_miss else stage,
        "variant": variant,
        "pdf_file_name": f"{case_id}.pdf",
        "page_count": n_pages,
        "label_scheme": scheme,
        "pages": pages,
        "fault_citation": {
            "citation_id": "cite-fault",
            "quote_text": fault_text,
            "true_source_pages0": fault_pages,
            "claimed_page0": wrong_page,
        },
        "control_citation": {
            "citation_id": "cite-control",
            "quote_text": control_text,
            "true_source_pages0": control_pages,
            "claimed_page0": control_pages[0],
        },
        "duplicate_occurrence_pages0": occ,
        "extra_duplicate_pages0": extra_dup_pages,
        "split_pages0": split_pages,
        "true_page0": tp,
        "control_page0": cp,
        "expected": {
            "verdict": EXPECTED_VERDICT[fault_type],
            "fault_type": fault_type,
            "first_fault_stage": None if is_near_miss else stage,
            "expected_source_pages0": None if is_near_miss else fault_pages,
            "candidate_source_pages0": (
                occ if fault_type == "DUPLICATE_TEXT_AMBIGUITY"
                else (fault_pages if fault_type != "UNLOCATABLE" else [])
            ),
        },
    }
    return case


# ---------------------------------------------------------------------------
# Image pages (Pillow raster; visible text, no text layer)
# ---------------------------------------------------------------------------

_CJK_FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
]


def _pil_cjk_font(size: int):
    from PIL import ImageFont

    for path in _CJK_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size, index=0)
        except Exception:
            continue
    return ImageFont.load_default()


def render_image_page_png(visible_text: str, case_id: str) -> bytes:
    """A4-ish raster (1240x1754) with the visible text drawn in ink.

    The PNG is embedded in the PDF as an image only: the PDF page has
    no text layer, so extraction must report IMAGE_ONLY.
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([60, 60, 1180, 1694], outline="black", width=4)
    font = _pil_cjk_font(44)
    small = _pil_cjk_font(32)
    draw.text((100, 140), "扫描件页面（无文本层）", fill="black", font=font)
    draw.text((100, 260), f"案例 {case_id}", fill="black", font=small)
    # Wrap the visible text at ~22 CJK chars per raster line.
    y = 420
    line = ""
    for ch in visible_text:
        line += ch
        if len(line) >= 22:
            draw.text((100, y), line, fill="black", font=font)
            y += 80
            line = ""
    if line:
        draw.text((100, y), line, fill="black", font=font)
    draw.text((100, 1500), "本页内容仅存在于图像中。", fill="black", font=small)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF building (ReportLab -> pypdf for labels + pinned metadata)
# ---------------------------------------------------------------------------


def build_pdf_bytes(case: dict) -> bytes:
    """Render the case PDF and return its final deterministic bytes."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(f"{FIXED_TITLE_PREFIX} {case['case_id']}")
    c.setAuthor("pagetrace-fixture-generator")
    c.setCreator("pagetrace-fixture-generator")
    c.setSubject(case["fault_type"])
    for page in case["pages"]:
        if page["kind"] == "image":
            png = render_image_page_png(
                page["image_visible_text"] or "", case["case_id"])
            c.drawImage(ImageReader(io.BytesIO(png)), MARGIN, MARGIN,
                        PAGE_WIDTH - 2 * MARGIN, PAGE_HEIGHT - 2 * MARGIN,
                        preserveAspectRatio=True, anchor="c", mask="auto")
        elif page["kind"] == "text":
            y = PAGE_HEIGHT - MARGIN - 10
            for line in page["lines"]:
                font = CJK_FONT if _is_cjk(line) else LATIN_FONT
                c.setFont(font, 13 if _is_cjk(line) else 11)
                c.drawString(MARGIN, y, line)
                y -= 26
        # Blank pages: nothing drawn.
        c.showPage()
    c.save()
    raw = buf.getvalue()

    # Second pass with pypdf: apply page labels + pinned metadata.
    # pypdf's writer output is byte-deterministic for identical input.
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(raw))
    writer = PdfWriter()
    for pdf_page in reader.pages:
        writer.add_page(pdf_page)
    for (frm, to, style, prefix, start) in label_ranges(
            case["label_scheme"], case["page_count"]):
        writer.set_page_label(frm, to, style, prefix, start)
    writer.add_metadata({
        "/Title": f"{FIXED_TITLE_PREFIX} {case['case_id']}",
        "/Author": "pagetrace-fixture-generator",
        "/Creator": "pagetrace-fixture-generator",
        "/Producer": "pagetrace-fixture-generator",
        "/Subject": case["fault_type"],
        "/CreationDate": FIXED_CREATION_DATE,
        "/ModDate": FIXED_MOD_DATE,
    })
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def measure_extraction(pdf_bytes: bytes, case: dict) -> list[dict]:
    """Extract every page with pypdf (the production reading path) and
    return the honest per-page extraction facts the bundle is built on."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == case["page_count"]
    facts = []
    for page in case["pages"]:
        k = page["pdf_page_index0"]
        if page["kind"] == "text":
            raw = reader.pages[k].extract_text() or ""
            facts.append({
                "pdf_page_index0": k,
                "pdf_page_label": page["pdf_page_label"],
                "text_state": "TEXT",
                "text_sha256": sha256_hex(raw),
                "extracted_norm": norm_text(raw),
            })
        elif page["kind"] == "blank":
            facts.append({
                "pdf_page_index0": k,
                "pdf_page_label": page["pdf_page_label"],
                "text_state": "EMPTY",
                "text_sha256": None,
                "extracted_norm": "",
            })
        else:  # image
            facts.append({
                "pdf_page_index0": k,
                "pdf_page_label": page["pdf_page_label"],
                "text_state": "IMAGE_ONLY",
                "text_sha256": None,
                "extracted_norm": "",
            })
    return facts


def verify_pdf_matches_spec(pdf_bytes: bytes, case: dict,
                            facts: list[dict]) -> list[str]:
    """Cross-check the built PDF against the authored spec.

    Every authored line of every TEXT page must survive extraction
    (after §4.2 normalisation); blank/image pages must extract nothing.
    """
    problems: list[str] = []
    for page, fact in zip(case["pages"], facts):
        if page["kind"] == "text":
            for line in page["lines"]:
                if norm_text(line) not in fact["extracted_norm"]:
                    problems.append(
                        f"{case['case_id']} p{page['pdf_page_index0']}: "
                        f"line not extractable: {line!r}")
        else:
            if fact["extracted_norm"]:
                problems.append(
                    f"{case['case_id']} p{page['pdf_page_index0']}: "
                    f"{page['kind']} page extracted text: "
                    f"{fact['extracted_norm'][:60]!r}")
    return problems


# ---------------------------------------------------------------------------
# Bundle builder: honest true trace, then the implanted fault
# ---------------------------------------------------------------------------


def _chunk(chunk_id: str, pages: list[int], text: str | None) -> dict:
    rec: dict = {
        "chunk_id": chunk_id,
        "source_page_indices0": sorted(pages),
    }
    if text is not None:
        rec["text_sha256"] = sha256_hex(text)
    else:
        rec["text_sha256"] = None
    return rec


def _index(record_id: str, pages: list[int], label: str | None) -> dict:
    return {
        "record_id": record_id,
        "source_page_indices0": sorted(pages),
        "pdf_page_label": label,
    }


def _display(citation_id: str, value, basis: str, viewer) -> dict:
    return {
        "citation_id": citation_id,
        "citation_page_value": value,
        "citation_page_basis": basis,
        "viewer_page1": viewer,
    }


def build_bundle(case: dict, pdf_sha: str, facts: list[dict]) -> dict:
    """Build the pagetrace.bundle/v1 trace for one case.

    The PDF is ground truth; the fault is implanted in the stage
    snapshots only. Downstream stages faithfully propagate the wrong
    value from the first fault stage (a real pipeline does not repair
    an upstream error on its own).
    """
    fault_type = case["fault_type"]
    stage = case["first_fault_stage"]
    variant = case["variant"]
    n = case["page_count"]
    labels = [p["pdf_page_label"] for p in case["pages"]]
    tp = case["true_page0"]
    fault_pages = case["fault_citation"]["true_source_pages0"]
    control_pages = case["control_citation"]["true_source_pages0"]
    fq = case["fault_citation"]["quote_text"]
    cq = case["control_citation"]["quote_text"]
    claimed = case["fault_citation"]["claimed_page0"]

    # ---- Extraction (honest, then mutated for PO-extraction / MM-extraction)
    extraction = []
    for fact in facts:
        rec: dict = {
            "pdf_page_index0": fact["pdf_page_index0"],
            "text_state": fact["text_state"],
        }
        if fact["text_state"] == "TEXT":
            rec["text_sha256"] = fact["text_sha256"]
        else:
            rec["text_sha256"] = None
        if fact["pdf_page_label"] is not None:
            rec["pdf_page_label"] = fact["pdf_page_label"]
        extraction.append(rec)

    if fault_type == "PAGE_OFFSET" and stage == "extraction":
        m = claimed  # page whose text hash is attached to tp's record
        assert 0 <= m < n and facts[m]["text_state"] == "TEXT"
        assert facts[tp]["text_state"] == "TEXT"
        extraction[tp]["text_sha256"], extraction[m]["text_sha256"] = (
            extraction[m]["text_sha256"], extraction[tp]["text_sha256"])
    if fault_type == "PAGE_METADATA_MISSING" and stage == "extraction":
        if variant == "record-text-state-error":
            extraction[tp]["text_state"] = "ERROR"
            extraction[tp]["text_sha256"] = None
        elif variant == "record-hash-omitted":
            extraction[tp].pop("text_sha256", None)
        elif variant == "record-omitted":
            extraction = [r for r in extraction
                          if r["pdf_page_index0"] != tp]

    # ---- Chunking ---------------------------------------------------------
    # Fault-chunk text hash: null when the quote has no extractable text
    # (UNLOCATABLE image/blank pages), else the quote's hash.
    un_no_text = (fault_type == "UNLOCATABLE"
                  and variant in ("image-only-page", "blank-page"))
    fault_chunk_text = None if un_no_text else fq
    if fault_type == "PAGE_OFFSET" and stage == "extraction":
        chunk_fault_pages = [claimed]
    elif fault_type == "PAGE_OFFSET" and stage == "chunking":
        chunk_fault_pages = [claimed]
    elif fault_type == "DUPLICATE_TEXT_AMBIGUITY" and stage == "chunking":
        chunk_fault_pages = [claimed]
    elif fault_type == "PAGE_METADATA_MISSING" and stage == "chunking" \
            and variant == "source-pages-emptied":
        chunk_fault_pages = []
    else:
        chunk_fault_pages = list(fault_pages)

    chunking = []
    if not (fault_type == "PAGE_METADATA_MISSING" and stage == "chunking"
            and variant == "chunk-record-absent"):
        fault_chunk = _chunk("c-fault", chunk_fault_pages, fault_chunk_text)
        if (fault_type == "PAGE_METADATA_MISSING" and stage == "chunking"
                and variant == "chunk-text-hash-omitted"):
            fault_chunk.pop("text_sha256", None)
        chunking.append(fault_chunk)
    chunking.append(_chunk("c-control", control_pages, cq))

    # ---- Indexing ---------------------------------------------------------
    if fault_type == "PAGE_OFFSET" and stage in ("extraction", "chunking"):
        index_fault_pages = [claimed]
    elif fault_type == "PAGE_OFFSET" and stage == "indexing":
        index_fault_pages = [claimed]
    elif fault_type == "DUPLICATE_TEXT_AMBIGUITY" and stage in ("chunking", "indexing"):
        index_fault_pages = [claimed]
    elif fault_type == "PAGE_METADATA_MISSING" and stage == "indexing" \
            and variant == "source-pages-emptied":
        index_fault_pages = []
    else:
        index_fault_pages = list(fault_pages)

    indexing = []
    if not (fault_type == "PAGE_METADATA_MISSING" and stage == "indexing"
            and variant == "index-record-absent"):
        fault_index = _index("v-fault", index_fault_pages,
                             labels[index_fault_pages[0]]
                             if index_fault_pages else None)
        if (fault_type == "PAGE_METADATA_MISSING" and stage == "indexing"
                and variant == "label-dropped-on-rebuild"):
            fault_index.pop("pdf_page_label", None)
        indexing.append(fault_index)
    indexing.append(_index("v-control", control_pages, labels[control_pages[0]]))

    # ---- Display ----------------------------------------------------------
    # The page the display layer shows for the fault citation: the
    # propagated claimed page, unless display itself is the fault stage.
    if fault_type == "PAGE_OFFSET" and stage == "display":
        if variant == "index0-passed-to-viewer":
            disp_fault = _display("cite-fault", tp, "PDF_INDEX_0", tp)
        elif variant == "plus-one-extra":
            disp_fault = _display("cite-fault", tp + 2, "PDF_NUMBER_1", tp + 2)
        elif variant == "label-7-read-as-number1":
            disp_fault = _display("cite-fault", labels[tp], "PDF_LABEL",
                                  int(labels[tp]))
        else:  # pragma: no cover - plan is closed
            raise ValueError(variant)
    elif fault_type == "DUPLICATE_TEXT_AMBIGUITY" and stage == "display":
        disp_fault = _display("cite-fault", claimed + 1, "PDF_NUMBER_1",
                              claimed + 1)
    elif fault_type == "PAGE_METADATA_MISSING" and stage == "display":
        if variant == "page-value-missing":
            disp_fault = _display("cite-fault", None, "PDF_NUMBER_1", None)
        elif variant == "viewer-page-missing":
            disp_fault = _display("cite-fault", fault_pages[0] + 1,
                                  "PDF_NUMBER_1", None)
        else:  # display-record-absent: no record at all (below)
            disp_fault = None
    else:
        shown = index_fault_pages[0] if index_fault_pages else fault_pages[0]
        disp_fault = _display("cite-fault", shown + 1, "PDF_NUMBER_1",
                              shown + 1)

    display = []
    if disp_fault is not None:
        display.append(disp_fault)
    display.append(_display("cite-control", control_pages[0] + 1,
                            "PDF_NUMBER_1", control_pages[0] + 1))

    # Runtime cross-field checks the JSON Schema cannot express (R-05).
    for rec in display:
        v = rec["viewer_page1"]
        if v is not None:
            assert 1 <= v <= n, f"viewer out of range: {rec}"
    for recs in (chunking, indexing):
        for rec in recs:
            for p in rec["source_page_indices0"]:
                assert 0 <= p < n, f"source page out of range: {rec}"

    bundle = {
        "schema": "pagetrace.bundle/v1",
        "case_id": case["case_id"],
        "document": {
            "file_name": case["pdf_file_name"],
            "sha256": pdf_sha,
            "page_count": n,
        },
        "page_semantics": {
            "canonical_field": "pdf_page_index0",
            "index_base": 0,
            "viewer_base": 1,
        },
        "stages": {
            "extraction": extraction,
            "chunking": chunking,
            "indexing": indexing,
            "display": display,
            "missing_stages": [],
        },
        "citations": [
            {
                "citation_id": "cite-fault",
                "quote_text": fq,
                "chunk_id": "c-fault",
                "index_record_id": "v-fault",
            },
            {
                "citation_id": "cite-control",
                "quote_text": cq,
                "chunk_id": "c-control",
                "index_record_id": "v-control",
            },
        ],
    }
    return bundle


# ---------------------------------------------------------------------------
# Spec + manifest
# ---------------------------------------------------------------------------

FAULT_DESCRIPTIONS = {
    ("PAGE_OFFSET", "plus-one-shift"):
        "Extraction attached the next page's text hash to this page's record (+1).",
    ("PAGE_OFFSET", "minus-one-shift"):
        "Extraction attached the previous page's text hash to this page's record (-1).",
    ("PAGE_OFFSET", "swap-with-distant-page"):
        "Extraction swapped the text hashes of this page and a distant TEXT page.",
    ("PAGE_OFFSET", "number1-used-as-index0"):
        "Chunking treated the 1-based page number as a 0-based index (+1).",
    ("PAGE_OFFSET", "index0-minus-one"):
        "Chunking applied a spurious -1 to the 0-based index.",
    ("PAGE_OFFSET", "roman-label-read-as-number"):
        "Chunking read the roman page label as if it were a decimal number (+1).",
    ("PAGE_OFFSET", "plus-one-shift-index"):
        "Indexing shifted the source pages by +1 (unused key; see fault_description).",
    ("PAGE_OFFSET", "minus-one-shift-index"):
        "Indexing shifted the source pages by -1 (unused key; see fault_description).",
    ("PAGE_OFFSET", "label-A3-read-as-index3"):
        "Indexing read the numeric suffix of label A-(n+1) as the 0-based index (+1).",
    ("PAGE_OFFSET", "index0-passed-to-viewer"):
        "Display passed the 0-based index straight to the 1-based viewer (R-06).",
    ("PAGE_OFFSET", "plus-one-extra"):
        "Display added an extra +1 on top of the correct conversion.",
    ("PAGE_OFFSET", "label-7-read-as-number1"):
        "Display read page label '7' (physical page 0) as viewer page 7 (R-03/E).",
    ("PAGE_METADATA_MISSING", "record-text-state-error"):
        "Extraction marked the true page ERROR with no text hash.",
    ("PAGE_METADATA_MISSING", "record-hash-omitted"):
        "Extraction record for the true page omits text_sha256.",
    ("PAGE_METADATA_MISSING", "record-omitted"):
        "Extraction has no record at all for the true page.",
    ("PAGE_METADATA_MISSING", "source-pages-emptied"):
        "The record's source_page_indices0 was emptied to [].",
    ("PAGE_METADATA_MISSING", "chunk-record-absent"):
        "The chunk record is absent; the citation still references c-fault.",
    ("PAGE_METADATA_MISSING", "chunk-text-hash-omitted"):
        "The chunk record omits text_sha256.",
    ("PAGE_METADATA_MISSING", "index-record-absent"):
        "The index record is absent; the citation still references v-fault.",
    ("PAGE_METADATA_MISSING", "label-dropped-on-rebuild"):
        "The rebuilt index record dropped pdf_page_label.",
    ("PAGE_METADATA_MISSING", "display-record-absent"):
        "The display record for the fault citation is absent.",
    ("PAGE_METADATA_MISSING", "page-value-missing"):
        "The display record has citation_page_value null and viewer null.",
    ("PAGE_METADATA_MISSING", "viewer-page-missing"):
        "The display record has the right page value but viewer_page1 null.",
    ("DUPLICATE_TEXT_AMBIGUITY", "reduce-to-first"):
        "The stage reduced the multi-page candidate set to the first occurrence.",
    ("DUPLICATE_TEXT_AMBIGUITY", "reduce-to-last"):
        "The stage reduced the multi-page candidate set to the last occurrence.",
    ("DUPLICATE_TEXT_AMBIGUITY", "reduce-to-middle"):
        "The stage reduced the multi-page candidate set to a middle occurrence.",
    ("DUPLICATE_TEXT_AMBIGUITY", "reduce-to-first-again"):
        "The stage reduced the multi-page candidate set to the first occurrence.",
    ("DUPLICATE_TEXT_AMBIGUITY", "reduce-to-last-again"):
        "The stage reduced the multi-page candidate set to the last occurrence.",
    ("UNLOCATABLE", "image-only-page"):
        "The quote is visible only inside a scanned image page; no text layer, no OCR.",
    ("UNLOCATABLE", "blank-page"):
        "The quote appears nowhere; the claimed page is blank (EMPTY).",
    ("UNLOCATABLE", "near-miss-quote"):
        "The quote differs by one character from the sentence on the page; exact match fails.",
}


def fault_description(case: dict) -> str:
    # The +/-1 variants are shared by extraction and indexing; the stage
    # disambiguates them.
    if case["first_fault_stage"] == "indexing":
        if case["variant"] == "plus-one-shift":
            return "Indexing shifted the source pages by +1."
        if case["variant"] == "minus-one-shift":
            return "Indexing shifted the source pages by -1."
    # FIX-R1 P1-R1-02: the near-miss description must state that the
    # anchor page is where the near-miss sentence was placed by design,
    # NOT a verified source of the quote (first_fault_stage /
    # expected_source_pages0 are null). This reproduces the FIX-R1
    # clarification previously hand-written into the four specs, so a
    # regeneration no longer loses it. (The short
    # FAULT_DESCRIPTIONS entry below is superseded for this variant.)
    if case["fault_type"] == "UNLOCATABLE" \
            and case["variant"] == "near-miss-quote":
        tp = case["true_page0"]
        return (
            "The quote differs by one character from the sentence placed "
            f"on page index {tp} (the near-miss sentence is on that page "
            "by design); exact match fails. "
            f"Page {tp} is the intended near-miss page, NOT a verified "
            "source of the quote: no stage is blamed (first_fault_stage "
            "null, expected_source_pages0 null) because the extraction "
            "records match the honest extraction (FIX-R1 P1-R1-02). "
            "fault_citation.true_source_pages0 "
            f"[{tp}] records where the near-miss sentence was placed, "
            "not a confirmed source page.")
    key = (case["fault_type"], case["variant"])
    desc = FAULT_DESCRIPTIONS.get(key)
    if desc is None:
        raise KeyError(key)
    return desc


def build_spec(case: dict, pdf_sha: str) -> dict:
    return {
        "spec_format_version": "pagetrace.fixture-spec/v1",
        "case_id": case["case_id"],
        "fault_type": case["fault_type"],
        "first_fault_stage": case["first_fault_stage"],
        "variant": case["variant"],
        "fault_description": fault_description(case),
        "pdf_file_name": case["pdf_file_name"],
        "pdf_sha256": pdf_sha,
        "page_count": case["page_count"],
        "label_scheme": case["label_scheme"],
        "pages": [
            {
                "pdf_page_index0": p["pdf_page_index0"],
                "pdf_page_label": p["pdf_page_label"],
                "kind": p["kind"],
                "lines": p["lines"],
                "image_visible_text": p["image_visible_text"],
            }
            for p in case["pages"]
        ],
        "fault_citation": {
            "citation_id": "cite-fault",
            "quote_text": case["fault_citation"]["quote_text"],
            "true_source_pages0": case["fault_citation"]["true_source_pages0"],
            "claimed_page0": case["fault_citation"]["claimed_page0"],
            "candidate_source_pages0": case["expected"]["candidate_source_pages0"],
        },
        "control_citation": {
            "citation_id": "cite-control",
            "quote_text": case["control_citation"]["quote_text"],
            "true_source_pages0": case["control_citation"]["true_source_pages0"],
            "note": ("Cross-page citation (R-10): the quote spans two pages."
                     if case["split_pages0"]
                     else "Single-page control citation; trace is correct end-to-end."),
        },
        "duplicate_occurrence_pages0": case["duplicate_occurrence_pages0"],
        "extra_duplicate_pages0": case["extra_duplicate_pages0"],
        "split_pages0": case["split_pages0"],
        "expected": case["expected"],
    }


def write_json(path: Path, obj: dict) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def load_bundle_schema(package_root: Path) -> dict:
    schema_path = package_root / "contracts" / "pagetrace.bundle.v1.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_bundle(bundle: dict, schema: dict) -> None:
    import jsonschema

    jsonschema.validate(bundle, schema)


def generate(out_dir: Path, package_root: Path, log=print) -> dict:
    """Generate all fixtures into out_dir; return the manifest dict."""
    from pypdf import PdfReader

    schema = load_bundle_schema(package_root)
    pdfs_dir = out_dir / "pdfs"
    specs_dir = out_dir / "specs"
    bundles_dir = out_dir / "bundles"
    for d in (pdfs_dir, specs_dir, bundles_dir):
        d.mkdir(parents=True, exist_ok=True)

    cases = build_cases()
    assert len(cases) == 48, len(cases)
    manifest_cases = []
    sha_lines = []
    for case in cases:
        pdf_bytes = build_pdf_bytes(case)
        pdf_sha = sha256_bytes(pdf_bytes)
        facts = measure_extraction(pdf_bytes, case)
        problems = verify_pdf_matches_spec(pdf_bytes, case, facts)
        if problems:
            raise RuntimeError("\n".join(problems))
        # Labels actually stored in the PDF must equal the spec labels.
        reader = PdfReader(io.BytesIO(pdf_bytes))
        stored_labels = list(reader.page_labels)
        spec_labels = [p["pdf_page_label"] for p in case["pages"]]
        if stored_labels != spec_labels:
            raise RuntimeError(
                f"{case['case_id']}: stored labels {stored_labels} != "
                f"spec labels {spec_labels}")
        bundle = build_bundle(case, pdf_sha, facts)
        validate_bundle(bundle, schema)

        pdf_path = pdfs_dir / case["pdf_file_name"]
        pdf_path.write_bytes(pdf_bytes)
        write_json(specs_dir / f"{case['case_id']}.json",
                   build_spec(case, pdf_sha))
        write_json(bundles_dir / f"{case['case_id']}.trace.json", bundle)
        sha_lines.append(f"{pdf_sha}  {case['pdf_file_name']}")
        manifest_cases.append({
            "case_id": case["case_id"],
            "fault_type": case["fault_type"],
            "first_fault_stage": case["first_fault_stage"],
            "variant": case["variant"],
            "pdf_file_name": case["pdf_file_name"],
            "pdf_sha256": pdf_sha,
            "page_count": case["page_count"],
            "label_scheme": case["label_scheme"],
            "page_labels": spec_labels,
            "fault_citation_id": "cite-fault",
            "fault_quote_text": case["fault_citation"]["quote_text"],
            "fault_true_source_pages0":
                case["fault_citation"]["true_source_pages0"],
            "fault_claimed_page0": case["fault_citation"]["claimed_page0"],
            "control_citation_id": "cite-control",
            "control_quote_text": case["control_citation"]["quote_text"],
            "control_true_source_pages0":
                case["control_citation"]["true_source_pages0"],
            "expected_verdict": case["expected"]["verdict"],
        })
        log(f"generated {case['case_id']}: {case['fault_type']} / "
            f"{case['first_fault_stage']} / {case['variant']} "
            f"pages={case['page_count']} sha={pdf_sha[:12]}...")

    counts = {ft: sum(1 for c in manifest_cases if c["fault_type"] == ft)
              for ft in FAULT_TYPES}
    coverage = {
        "pdfs_with_chinese_text": sum(
            1 for c in cases if any(
                p["kind"] == "text" and any(_is_cjk(line) for line in p["lines"])
                for p in c["pages"])),
        "pdfs_with_blank_page": sum(
            1 for c in cases if any(p["kind"] == "blank" for p in c["pages"])),
        "pdfs_with_image_page": sum(
            1 for c in cases if any(p["kind"] == "image" for p in c["pages"])),
        "pdfs_with_cross_page_split": sum(
            1 for c in cases if c["split_pages0"]),
        "pdfs_with_duplicate_sentence": sum(
            1 for c in cases if c["duplicate_occurrence_pages0"]
            or c["extra_duplicate_pages0"]),
        "control_citations_total": sum(
            1 for _ in manifest_cases),
        "label_schemes_used": sorted({c["label_scheme"] for c in cases}),
    }
    manifest = {
        "manifest_format_version": "pagetrace.fixture-manifest/v1",
        "generator": f"tools/generate_fixtures.py {GENERATOR_VERSION}",
        "schema": "pagetrace.bundle/v1",
        "case_count": len(manifest_cases),
        "counts_by_fault_type": counts,
        "coverage": coverage,
        "cases": manifest_cases,
    }
    write_json(out_dir / "manifest.json", manifest)
    (out_dir / "sha256sums.txt").write_text(
        "\n".join(sorted(sha_lines)) + "\n", encoding="utf-8")
    log(f"cases={len(manifest_cases)} counts={counts}")
    log(f"coverage={json.dumps(coverage, ensure_ascii=False, sort_keys=True)}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the 48 deterministic PageTrace fixtures.")
    parser.add_argument("--out", default="fixtures",
                        help="output directory (default: fixtures)")
    parser.add_argument("--package-root", default=None,
                        help="PACKAGE_ROOT (default: parent of tools/)")
    args = parser.parse_args(argv)
    here = Path(__file__).resolve()
    package_root = (Path(args.package_root).resolve() if args.package_root
                    else here.parent.parent)
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    generate(out_dir, package_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
