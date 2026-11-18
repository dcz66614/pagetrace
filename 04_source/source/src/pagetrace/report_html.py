"""Offline four-column HTML report (P026 T008).

Production implementation of PROJECT_BOOK.md v1.0.0 §9: a single-page,
offline HTML report over real ``pagetrace.report/v1`` results. The
report shows, per citation, the PDF truth, the observed extraction,
the chunk/index chain and the final citation side by side, with a
"wrong page -> first fault stage -> correct source location" table.

Design rules (frozen by the spec, not by this module):

* Data first, presentation second. :func:`build_view_entry` assembles
  one citation's view model from three real inputs only — a
  ``pagetrace.report/v1`` citation result, the ``pagetrace.bundle/v1``
  trace it came from, and the honest per-page extraction of the same
  PDF. It never re-implements verdict logic and never guesses a page:
  ``correct_*`` stays ``None`` exactly when the report says so.
* The truth column is the honest extraction; the extraction column
  keeps the bundle's observed records verbatim, so drift between them
  stays visible. Chunk and index are shown separately and never merged
  into one attribution.
* Status is text as well as colour (§9.3): PASS is neutral green,
  FAIL_* offset/metadata red, and AMBIGUOUS / UNLOCATABLE / UNKNOWN_*
  / NEEDS_MANUAL_REVIEW amber. No uncertainty verdict ever maps to
  the PASS tone.
* Offline by construction: the generated HTML references only the
  sibling ``assets/report.css`` and ``assets/report.js`` and embeds
  its data as JSON in the page. No CDN, remote font, analytics script
  or external request of any kind. ``file://`` double-click is the
  supported way to open it; no build step, server or API is needed.
* Deterministic output: the embedded JSON is canonical (sorted keys,
  no redundant whitespace), so two renders of the same entries are
  byte-identical and share one SHA-256.

This module is presentation only. It does not touch the S0 algorithm
(extract / locate / compare_stages / verdicts), the bundle schema,
the Oracle or the CLI entry point.
"""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from .verdicts import (
    FAULT_TYPES,
    STAGE_ORDER,
    VERDICTS,
)

__all__ = [
    "STATUS_LABELS",
    "FAULT_LABELS",
    "STAGE_LABELS",
    "TEXT_STATE_LABELS",
    "status_tone",
    "build_view_entry",
    "build_view_entries",
    "build_entries_from_fixtures",
    "build_report_document",
    "render_html",
    "write_report",
    "REPORT_SCHEMA",
    "BUNDLE_SCHEMA",
]

REPORT_SCHEMA = "pagetrace.report/v1"
BUNDLE_SCHEMA = "pagetrace.bundle/v1"
TOOL_VERSION = "0.1.0"

#: Directory holding the sibling CSS/JS shipped with this module.
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# --- Status mapping (PROJECT_BOOK §9.3). Text label is part of the
# badge in the UI; tone is never colour-only. An unknown verdict maps
# to amber, never to pass: uncertainty must stay visible. ---
STATUS_LABELS: dict[str, str] = {
    "PASS": "PASS",
    "FAIL_PAGE_OFFSET": "FAIL — 页码偏移",
    "FAIL_METADATA_MISSING": "FAIL — 元数据缺失",
    "FAIL_AMBIGUOUS": "FAIL — 歧义未确认",
    "FAIL_UNLOCATABLE": "FAIL — 无法定位",
    "UNKNOWN_TRACE_MISSING": "UNKNOWN — 阶段快照缺失",
    "UNKNOWN_PAGE_BASIS": "UNKNOWN — 页码基准未知",
    "AMBIGUOUS": "AMBIGUOUS — 未确认",
    "NEEDS_MANUAL_REVIEW": "NEEDS_MANUAL_REVIEW — 需人工复核",
}

#: Verdict -> display tone. Only exactly ``PASS`` is green.
VERDICT_TONES: dict[str, str] = {
    "PASS": "pass",
    "FAIL_PAGE_OFFSET": "fail",
    "FAIL_METADATA_MISSING": "fail",
    "FAIL_AMBIGUOUS": "amber",
    "FAIL_UNLOCATABLE": "amber",
    "UNKNOWN_TRACE_MISSING": "amber",
    "UNKNOWN_PAGE_BASIS": "amber",
    "AMBIGUOUS": "amber",
    "NEEDS_MANUAL_REVIEW": "amber",
}

FAULT_LABELS: dict[str, str] = {
    "PAGE_OFFSET": "页码偏移 PAGE_OFFSET",
    "PAGE_METADATA_MISSING": "元数据缺失 PAGE_METADATA_MISSING",
    "DUPLICATE_TEXT_AMBIGUITY": "重复文本歧义 DUPLICATE_TEXT_AMBIGUITY",
    "UNLOCATABLE": "无法定位 UNLOCATABLE",
}

STAGE_LABELS: dict[str, str] = {
    "extraction": "抽取 extraction",
    "chunking": "分片 chunking",
    "indexing": "索引 indexing",
    "display": "展示 display",
}

TEXT_STATE_LABELS: dict[str, str] = {
    "TEXT": "TEXT 有文本层",
    "EMPTY": "EMPTY 空白页",
    "IMAGE_ONLY": "IMAGE_ONLY 图像页无文本层",
    "ERROR": "ERROR 抽取异常",
}

#: Report verdicts that count as honest uncertainty (never PASS).
UNCERTAINTY_VERDICTS = frozenset({
    "UNKNOWN_TRACE_MISSING",
    "UNKNOWN_PAGE_BASIS",
    "AMBIGUOUS",
    "NEEDS_MANUAL_REVIEW",
})


def status_tone(verdict: str) -> str:
    """Display tone for a verdict: ``pass`` / ``fail`` / ``amber``.

    Only the exact verdict ``PASS`` is green. Anything unknown is
    amber, so a future verdict can never silently render as PASS.
    """
    return VERDICT_TONES.get(verdict, "amber")


def status_label(verdict: str) -> str:
    """Human-readable status label (Chinese + verdict code)."""
    return STATUS_LABELS.get(verdict, f"UNKNOWN — 未确认 ({verdict})")


def _require(mapping: dict, key: str, where: str) -> object:
    if key not in mapping:
        raise ValueError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _page_record(record: object) -> dict:
    """One per-page record as a plain JSON dict.

    Accepts a :class:`pagetrace.extract.PageTextRecord` or a plain
    bundle extraction dict; only the four display fields are kept.
    """
    if hasattr(record, "pdf_page_index0"):
        return {
            "pdf_page_index0": record.pdf_page_index0,  # type: ignore[attr-defined]
            "pdf_page_label": record.pdf_page_label,  # type: ignore[attr-defined]
            "text_state": record.text_state,  # type: ignore[attr-defined]
            "text_sha256": record.text_sha256,  # type: ignore[attr-defined]
        }
    rec = dict(record)  # type: ignore[arg-type]
    return {
        "pdf_page_index0": rec.get("pdf_page_index0"),
        "pdf_page_label": rec.get("pdf_page_label"),
        "text_state": rec.get("text_state"),
        "text_sha256": rec.get("text_sha256"),
    }


def _find(records: list[dict] | None, key: str, wanted: object) -> dict | None:
    if not records or wanted is None:
        return None
    for record in records:
        if record.get(key) == wanted:
            return record
    return None


def build_view_entry(
    *,
    case_id: str,
    result: dict,
    bundle: dict,
    honest_records: list,
    extraction_diffs: list | None = None,
) -> dict:
    """Assemble one citation's four-column view model.

    ``result`` is one ``citation_result`` of a ``pagetrace.report/v1``
    report (as produced by ``CitationVerdict.to_dict()``);
    ``bundle`` is the ``pagetrace.bundle/v1`` trace for ``case_id``;
    ``honest_records`` is the production extraction of the same PDF
    (``extract_pdf`` output). The returned dict is JSON-serializable
    and is embedded verbatim in the report page.

    Raises ``ValueError`` on an unknown verdict, an unknown fault
    type / first-fault stage, or a missing citation in the bundle —
    the report refuses to render a verdict it cannot account for.
    """
    verdict = _require(result, "verdict", f"{case_id} result")
    if verdict not in VERDICTS:
        raise ValueError(f"{case_id}: unknown verdict {verdict!r}")
    fault_type = result.get("fault_type")
    if fault_type is not None and fault_type not in FAULT_TYPES:
        raise ValueError(f"{case_id}: unknown fault_type {fault_type!r}")
    first_stage = result.get("first_fault_stage")
    if first_stage is not None and first_stage not in STAGE_ORDER:
        raise ValueError(
            f"{case_id}: unknown first_fault_stage {first_stage!r}")

    citation_id = str(_require(result, "citation_id", f"{case_id} result"))
    citation = _find(bundle.get("citations"), "citation_id", citation_id)
    if citation is None:
        raise ValueError(
            f"{case_id}: citation {citation_id!r} missing from bundle")
    stages = bundle.get("stages") or {}
    display = _find(stages.get("display"), "citation_id", citation_id)
    chunk = _find(stages.get("chunking"), "chunk_id",
                  citation.get("chunk_id"))
    index_record = _find(stages.get("indexing"), "record_id",
                         citation.get("index_record_id"))
    evidence = [
        {
            "stage": item.get("stage"),
            "field": item.get("field"),
            "upstream_value": item.get("upstream_value"),
            "downstream_value": item.get("downstream_value"),
            "note": item.get("note", ""),
        }
        for item in (result.get("evidence") or [])
    ]
    document = bundle.get("document") or {}
    return {
        "entry_id": f"{case_id}/{citation_id}",
        "case_id": case_id,
        "citation_id": citation_id,
        "quote_text": citation.get("quote_text", ""),
        "quote_sha256": result.get("quote_sha256"),
        "verdict": verdict,
        "fault_type": fault_type,
        "first_fault_stage": first_stage,
        "observed_page_value": result.get("observed_page_value"),
        "citation_page_basis": result.get("citation_page_basis"),
        "correct_pdf_page_number1": result.get("correct_pdf_page_number1"),
        "correct_viewer_page1": result.get("correct_viewer_page1"),
        "candidate_source_pages0": result.get("candidate_source_pages0"),
        "expected_source_pages0": result.get("expected_source_pages0"),
        "document": {
            "file_name": document.get("file_name"),
            "page_count": document.get("page_count"),
            "sha256": document.get("sha256"),
        },
        # Truth column: the honest extraction. Extraction column: the
        # bundle's observed records, verbatim — drift stays visible.
        "truth_pages": [_page_record(r) for r in honest_records],
        "extraction": [_page_record(r) for r in (stages.get("extraction") or [])],
        # Chunk / index shown separately, never merged (PROJECT_BOOK §9.2).
        "chunk": dict(chunk) if chunk is not None else None,
        "index_record": dict(index_record) if index_record is not None else None,
        "display": dict(display) if display is not None else None,
        "stage_diffs": evidence,
        "extraction_diffs": [
            {
                "stage": d.get("stage"),
                "field": d.get("field"),
                "kind": d.get("kind"),
                "pdf_page_index0": d.get("pdf_page_index0"),
                "upstream_value": d.get("upstream_value"),
                "downstream_value": d.get("downstream_value"),
                "note": d.get("note", ""),
            }
            for d in (extraction_diffs or [])
        ],
        "notes": list(result.get("notes") or []),
    }


def build_view_entries(cases) -> list[dict]:
    """View entries for several cases.

    ``cases`` is an iterable of ``(case_id, result, bundle,
    honest_records)`` tuples — one per citation — in display order.
    """
    return [
        build_view_entry(
            case_id=case_id, result=result, bundle=bundle,
            honest_records=honest_records)
        for case_id, result, bundle, honest_records in cases
    ]


def build_entries_from_fixtures(
    fixtures_dir: str | Path,
    case_ids: list[str] | None = None,
) -> tuple[list[dict], dict]:
    """Run the real pipeline over frozen fixtures and build entries.

    For every selected case (default: all 48 in manifest order) both
    citations (``cite-fault`` and ``cite-control``) are analysed with
    the production implementation (``extract_pdf`` +
    ``analyze_bundle``) and turned into view entries. No mock data:
    every verdict, page set and stage diff comes from the pipeline.

    Returns ``(entries, counts)`` where ``counts`` carries the S0
    headline numbers (fault citations detected per fault type,
    first-fault stages correct, control PASS count) so callers can
    assert the report really renders the S0 outcome.
    """
    # Local import: keeps this presentation module importable without
    # pulling the PDF stack in for pure rendering callers.
    from .compare_stages import analyze_bundle, compare_extraction
    from .extract import extract_pdf

    fixtures = Path(fixtures_dir)
    manifest = json.loads((fixtures / "manifest.json").read_text(encoding="utf-8"))
    wanted = set(case_ids) if case_ids is not None else None
    entries: list[dict] = []
    detected: dict[str, int] = {}
    stages_correct = 0
    controls_pass = 0
    for case in manifest["cases"]:
        case_id = case["case_id"]
        if wanted is not None and case_id not in wanted:
            continue
        bundle = json.loads(
            (fixtures / "bundles" / f"{case_id}.trace.json").read_text(
                encoding="utf-8"))
        _, honest = extract_pdf(str(fixtures / "pdfs" / bundle["document"]["file_name"]))
        extraction_diffs = [
            d.to_dict()
            for d in compare_extraction(honest, bundle["stages"].get("extraction"))
        ]
        for verdict in analyze_bundle(bundle, honest):
            entries.append(build_view_entry(
                case_id=case_id, result=verdict.to_dict(), bundle=bundle,
                honest_records=honest, extraction_diffs=extraction_diffs))
            if verdict.citation_id == "cite-fault":
                if verdict.fault_type is not None:
                    detected[verdict.fault_type] = \
                        detected.get(verdict.fault_type, 0) + 1
                if verdict.first_fault_stage == case["first_fault_stage"]:
                    stages_correct += 1
            elif verdict.citation_id == "cite-control" \
                    and verdict.verdict == "PASS":
                controls_pass += 1
    counts = {
        "entries": len(entries),
        "cases": len({e["case_id"] for e in entries}),
        "detected_by_fault_type": detected,
        "first_fault_stage_correct": stages_correct,
        "control_pass": controls_pass,
    }
    return entries, counts


def build_report_document(
    entries: list[dict],
    *,
    title: str = "PageTrace — 四栏联动报告",
    pdf_dir: str | None = None,
) -> dict:
    """The JSON document embedded in the report page.

    ``pdf_dir`` is an optional URL prefix (relative to the report
    file) for the local PDFs, used to build the truth column's
    ``#page=<viewer_page1>`` links (§9.2). ``None`` means no PDF
    links are rendered — the report never invents a location.
    """
    total = len(entries)
    passed = sum(1 for e in entries if e["verdict"] == "PASS")
    failed = sum(1 for e in entries if e["verdict"].startswith("FAIL"))
    unknown = sum(1 for e in entries
                  if e["verdict"].startswith("UNKNOWN"))
    ambiguous = sum(1 for e in entries if e["verdict"] == "AMBIGUOUS")
    needs_review = sum(
        1 for e in entries if e["verdict"] == "NEEDS_MANUAL_REVIEW")
    by_fault: dict[str, int] = {}
    for entry in entries:
        if entry["fault_type"] is not None:
            by_fault[entry["fault_type"]] = \
                by_fault.get(entry["fault_type"], 0) + 1
    return {
        "title": title,
        "schema": REPORT_SCHEMA,
        "bundle_schema": BUNDLE_SCHEMA,
        "tool": {"name": "pagetrace", "version": TOOL_VERSION},
        "pdf_dir": pdf_dir,
        "summary": {
            "total_citations": total,
            "pass_count": passed,
            "fail_count": failed,
            "unknown_count": unknown,
            "ambiguous_count": ambiguous,
            "needs_manual_review_count": needs_review,
            "by_fault_type": by_fault,
        },
        "entries": entries,
    }


def embedded_json(document: dict) -> str:
    """Canonical JSON for the ``<script type="application/json">`` block.

    Sorted keys, no redundant whitespace, and ``<`` / ``>`` / ``&``
    escaped so a quote containing ``</script>`` can never break out
    of the embedding element.
    """
    text = json.dumps(document, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return (text.replace("&", "\\u0026")
                .replace("<", "\\u003c")
                .replace(">", "\\u003e"))


def _asset_text(name: str) -> str:
    return (ASSETS_DIR / name).read_text(encoding="utf-8")


def render_html(
    entries: list[dict],
    *,
    title: str = "PageTrace — 四栏联动报告",
    pdf_dir: str | None = None,
) -> str:
    """Render the full standalone report page for ``entries``.

    The page references ``assets/report.css`` and
    ``assets/report.js`` (written next to it by :func:`write_report`)
    and embeds the report document as JSON. Opening the file with
    ``file://`` is sufficient; nothing is fetched at runtime.
    """
    document = build_report_document(entries, title=title, pdf_dir=pdf_dir)
    summary = document["summary"]
    data = embedded_json(document)
    esc_title = html.escape(title, quote=True)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc_title}</title>
<link rel="stylesheet" href="assets/report.css">
</head>
<body>
<header class="page-header">
  <h1>{esc_title}</h1>
  <p class="header-meta">单页离线 HTML · 无 CDN、远程字体、分析脚本或外部请求 · 数据来自真实 pagetrace.report/v1 运行结果（非 mock）</p>
  <p class="header-meta">bundle schema：{BUNDLE_SCHEMA} · 报告 schema：{REPORT_SCHEMA} · 工具 pagetrace {TOOL_VERSION} · 状态颜色见 PROJECT_BOOK §9.3，状态同时以文字标出，不只靠颜色</p>
  <p class="header-meta" id="report-summary">共 {summary["total_citations"]} 条引用 · PASS {summary["pass_count"]} · FAIL {summary["fail_count"]} · UNKNOWN {summary["unknown_count"]} · AMBIGUOUS {summary["ambiguous_count"]} · 需人工复核 {summary["needs_manual_review_count"]}</p>
</header>

<main>
  <section class="controls" aria-label="过滤与操作">
    <label>故障类型
      <select id="filter-fault">
        <option value="">全部</option>
        <option value="PAGE_OFFSET">页码偏移 PAGE_OFFSET</option>
        <option value="PAGE_METADATA_MISSING">元数据缺失 PAGE_METADATA_MISSING</option>
        <option value="DUPLICATE_TEXT_AMBIGUITY">重复文本歧义 DUPLICATE_TEXT_AMBIGUITY</option>
        <option value="UNLOCATABLE">无法定位 UNLOCATABLE</option>
      </select>
    </label>
    <label>首错阶段
      <select id="filter-stage">
        <option value="">全部</option>
        <option value="extraction">抽取 extraction</option>
        <option value="chunking">分片 chunking</option>
        <option value="indexing">索引 indexing</option>
        <option value="display">展示 display</option>
      </select>
    </label>
    <label>状态
      <select id="filter-status">
        <option value="">全部</option>
        <option value="pass">PASS（绿）</option>
        <option value="fail">FAIL（红）</option>
        <option value="amber">未确认 / 歧义 / 无法定位（琥珀）</option>
      </select>
    </label>
    <button type="button" id="download-json">下载完整 report.json</button>
    <button type="button" id="copy-json">复制当前引用 JSON 证据</button>
  </section>

  <p id="selected-summary" class="selected-summary" aria-live="polite"></p>

  <section aria-label="引用列表">
    <h2>引用列表（点击一条，四栏同步联动）</h2>
    <div id="citation-list" class="citation-list" role="group" aria-label="引用"></div>
  </section>

  <section aria-label="四栏联动视图">
    <h2>四栏联动视图</h2>
    <p class="hint">点击任意一栏中的页行，可在四栏同步高亮同一物理页（0-based 索引）。“✓ 正确来源”行是真值来源页；“✕ 与真值不符”是该阶段观测到的漂移。</p>
    <div class="columns">
      <article class="column" id="col-truth" aria-label="PDF 真值栏">
        <h3>① PDF 真值</h3>
        <p class="col-note" id="col-truth-note"></p>
        <div class="table-scroll">
        <table>
          <thead><tr><th>页（索引 0-based / 页号 1-based / label）</th><th>抽取状态</th><th>来源标记</th><th>本地 PDF 链接</th></tr></thead>
          <tbody id="col-truth-body"></tbody>
        </table>
        </div>
      </article>

      <article class="column" id="col-extraction" aria-label="抽取栏">
        <h3>② 抽取</h3>
        <p class="col-note" id="col-extraction-note"></p>
        <div class="table-scroll">
        <table>
          <thead><tr><th>页（索引 0-based / 页号 1-based）</th><th>文本状态</th><th>文本 hash</th><th>命中</th><th>差异</th></tr></thead>
          <tbody id="col-extraction-body"></tbody>
        </table>
        </div>
      </article>

      <article class="column" id="col-chunk-index" aria-label="分片与索引栏">
        <h3>③ 分片与索引</h3>
        <p class="col-note" id="col-chunk-note"></p>
        <h4>分片 chunk</h4>
        <div class="table-scroll">
        <table>
          <thead><tr><th>chunk id</th><th>source page 集合</th><th>文本 hash</th><th>差异</th></tr></thead>
          <tbody id="col-chunk-body"></tbody>
        </table>
        </div>
        <h4>索引 index</h4>
        <div class="table-scroll">
        <table>
          <thead><tr><th>index record id</th><th>source page 集合</th><th>保留的页元数据</th></tr></thead>
          <tbody id="col-index-body"></tbody>
        </table>
        </div>
      </article>

      <article class="column" id="col-citation" aria-label="最终引用栏">
        <h3>④ 最终引用</h3>
        <div id="col-citation-body"></div>
      </article>
    </div>
  </section>

  <section aria-label="错误页码对照表">
    <h2>对照表：错误页码 → 首错阶段 → 正确来源位置</h2>
    <div class="table-scroll">
    <table class="comparison">
      <thead><tr><th>引用</th><th>错误页码（观测值）</th><th>首错阶段</th><th>正确来源位置</th><th>verdict</th></tr></thead>
      <tbody id="comparison-body"></tbody>
    </table>
    </div>
  </section>

  <section aria-label="阶段差异">
    <h2>阶段差异（stage diffs）</h2>
    <div id="stage-diff-list"></div>
  </section>

  <section aria-label="原始观测 JSON">
    <h2>原始观测 JSON</h2>
    <details>
      <summary>展开当前引用的完整 JSON（可复制）</summary>
      <pre id="raw-json"></pre>
    </details>
  </section>
</main>

<footer>
  <p>PageTrace 离线报告：本页只呈现 pagetrace.report/v1 的真实运行结果，不改算法门槛、不阻断 S0；若表现不清晰，保留 JSON 输出并重做 UI，不让 UI 缺陷影响 S0 核心。</p>
</footer>

<script id="report-data" type="application/json">{data}</script>
<script src="assets/report.js"></script>
</body>
</html>
"""


def write_report(
    output_dir: str | Path,
    entries: list[dict],
    *,
    title: str = "PageTrace — 四栏联动报告",
    pdf_dir: str | None = None,
) -> dict:
    """Write ``report.html`` + ``assets/report.css|js`` to ``output_dir``.

    Returns paths and SHA-256 hashes. Rendering is deterministic:
    writing the same entries twice yields byte-identical files.
    """
    out = Path(output_dir)
    assets_out = out / "assets"
    assets_out.mkdir(parents=True, exist_ok=True)
    html_text = render_html(entries, title=title, pdf_dir=pdf_dir)
    html_path = out / "report.html"
    html_path.write_text(html_text, encoding="utf-8")
    written: dict[str, dict] = {}
    for name in ("report.css", "report.js"):
        target = assets_out / name
        target.write_text(_asset_text(name), encoding="utf-8")
        written[name] = {
            "path": str(target),
            "sha256": hashlib.sha256(
                target.read_bytes()).hexdigest(),
        }
    return {
        "report_html": str(html_path),
        "report_html_sha256": hashlib.sha256(
            html_path.read_bytes()).hexdigest(),
        "report_html_bytes": html_path.stat().st_size,
        "assets": written,
        "entries": len(entries),
    }
