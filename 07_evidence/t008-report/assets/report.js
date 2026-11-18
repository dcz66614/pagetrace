/* P026 PageTrace — T008 production four-column linked report.
 *
 * Offline only: no network requests, no CDN, no remote fonts. All data is
 * embedded in the page by report_html.py as JSON in #report-data; this
 * script only renders it. Open report.html directly from disk (file://).
 *
 * Deep link: report.html#case=<entry_id> preselects a citation, where
 * entry_id is "<case_id>/<citation_id>", e.g. #case=du-chk-01/cite-fault.
 *
 * Status mapping — PROJECT_BOOK §9.3. Verdict text is always shown next
 * to the colour, so status is never colour-only. AMBIGUOUS / UNLOCATABLE
 * / UNKNOWN_* / NEEDS_MANUAL_REVIEW are amber and must never render
 * as PASS; only the exact verdict PASS is green.
 */
"use strict";

const REPORT = JSON.parse(document.getElementById("report-data").textContent);
const ENTRIES = REPORT.entries || [];
const PDF_DIR = REPORT.pdf_dir || null;

const STATUS_META = {
  "PASS": { "cls": "status-pass", "label": "PASS", "tone": "pass" },
  "FAIL_PAGE_OFFSET": { "cls": "status-fail", "label": "FAIL — 页码偏移", "tone": "fail" },
  "FAIL_METADATA_MISSING": { "cls": "status-fail", "label": "FAIL — 元数据缺失", "tone": "fail" },
  "FAIL_AMBIGUOUS": { "cls": "status-amber", "label": "FAIL — 歧义未确认", "tone": "amber" },
  "FAIL_UNLOCATABLE": { "cls": "status-amber", "label": "FAIL — 无法定位", "tone": "amber" },
  "UNKNOWN_TRACE_MISSING": { "cls": "status-amber", "label": "UNKNOWN — 阶段快照缺失", "tone": "amber" },
  "UNKNOWN_PAGE_BASIS": { "cls": "status-amber", "label": "UNKNOWN — 页码基准未知", "tone": "amber" },
  "AMBIGUOUS": { "cls": "status-amber", "label": "AMBIGUOUS — 未确认", "tone": "amber" },
  "NEEDS_MANUAL_REVIEW": { "cls": "status-amber", "label": "NEEDS_MANUAL_REVIEW — 需人工复核", "tone": "amber" },
  "UNKNOWN": { "cls": "status-amber", "label": "UNKNOWN — 未确认", "tone": "amber" },
  "SKIPPED": { "cls": "status-skipped", "label": "SKIPPED — 已跳过", "tone": "skipped" }
};

const STAGE_LABELS = {
  extraction: "抽取 extraction",
  chunking: "分片 chunking",
  indexing: "索引 indexing",
  display: "展示 display"
};

const FAULT_LABELS = {
  PAGE_OFFSET: "页码偏移 PAGE_OFFSET",
  PAGE_METADATA_MISSING: "元数据缺失 PAGE_METADATA_MISSING",
  DUPLICATE_TEXT_AMBIGUITY: "重复文本歧义 DUPLICATE_TEXT_AMBIGUITY",
  UNLOCATABLE: "无法定位 UNLOCATABLE"
};

const TEXT_STATE_LABELS = {
  TEXT: "TEXT 有文本层",
  EMPTY: "EMPTY 空白页",
  IMAGE_ONLY: "IMAGE_ONLY 图像页无文本层",
  ERROR: "ERROR 抽取异常"
};

const state = { selectedEntryId: null, selectedPageIndex0: null };

function $(id) { return document.getElementById(id); }

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function shortHash(value) {
  return value ? String(value).slice(0, 12) + "…" : "—";
}

function pages1(indices0) {
  if (!indices0 || indices0.length === 0) return "—";
  return indices0.map((i) => "p." + (i + 1)).join("，");
}

function numbers1(numbers) {
  if (!numbers || numbers.length === 0) return "—";
  return numbers.map((n) => "p." + n).join("，");
}

function metaFor(verdict) {
  return STATUS_META[verdict] || STATUS_META.UNKNOWN;
}

function badge(verdict) {
  const meta = metaFor(verdict);
  return `<span class="badge ${meta.cls}">${esc(meta.label)}</span>`;
}

function findEntry(entryId) {
  return ENTRIES.find((e) => e.entry_id === entryId) || ENTRIES[0];
}

function visibleEntries() {
  const fault = $("filter-fault").value;
  const stage = $("filter-stage").value;
  const status = $("filter-status").value;
  return ENTRIES.filter((entry) => {
    if (fault && String(entry.fault_type) !== fault) return false;
    if (stage && entry.first_fault_stage !== stage) return false;
    if (status && metaFor(entry.verdict).tone !== status) return false;
    return true;
  });
}

function renderCitationList() {
  const list = visibleEntries();
  const box = $("citation-list");
  if (list.length === 0) {
    box.innerHTML = '<p class="empty-note">没有符合过滤条件的引用。</p>';
    return;
  }
  box.innerHTML = list.map((entry) => {
    const meta = metaFor(entry.verdict);
    const selected = entry.entry_id === state.selectedEntryId;
    const fault = entry.fault_type
      ? esc(FAULT_LABELS[entry.fault_type] || entry.fault_type)
      : "对照 PASS";
    return `<button type="button" class="citation-item${selected ? " selected" : ""}"` +
      ` data-entry-id="${esc(entry.entry_id)}"` +
      ` aria-pressed="${selected ? "true" : "false"}">` +
      `<span class="citation-id">${esc(entry.entry_id)}</span>` +
      `<span class="citation-fault">${fault}</span>` +
      `<span class="badge ${meta.cls}">${esc(meta.label)}</span>` +
      `<span class="citation-quote">${esc(entry.quote_text)}</span>` +
      `</button>`;
  }).join("");
}

function rowClass(entry, index0, kind) {
  const classes = ["page-row"];
  if (kind === "truth" && entry.correct_pdf_page_number1 &&
      entry.correct_pdf_page_number1.includes(index0 + 1)) {
    classes.push("row-correct");
  }
  if (kind === "extraction" && entry.candidate_source_pages0 &&
      entry.candidate_source_pages0.includes(index0)) {
    classes.push("row-candidate");
  }
  if (state.selectedPageIndex0 === index0) classes.push("row-selected");
  return classes.join(" ");
}

function truthLink(entry, index0) {
  if (!PDF_DIR || !entry.document || !entry.document.file_name) return "—";
  const href = PDF_DIR.replace(/\/$/, "") + "/" +
    encodeURIComponent(entry.document.file_name) + "#page=" + (index0 + 1);
  return `<a href="${esc(href)}">#page=${index0 + 1}</a>`;
}

function paintTruth(entry) {
  $("col-truth-body").innerHTML = entry.truth_pages.map((page) => {
    const index0 = page.pdf_page_index0;
    const isCorrect = entry.correct_pdf_page_number1 &&
      entry.correct_pdf_page_number1.includes(index0 + 1);
    return `<tr class="${rowClass(entry, index0, "truth")}" data-page-index="${index0}">` +
      `<td>p.${index0 + 1} · 索引 ${index0} · label ${esc(page.pdf_page_label)}</td>` +
      `<td>${esc(TEXT_STATE_LABELS[page.text_state] || page.text_state)}</td>` +
      `<td>${isCorrect ? '<span class="tag tag-correct">✓ 正确来源</span>' : "—"}</td>` +
      `<td>${truthLink(entry, index0)}</td></tr>`;
  }).join("");
  $("col-truth-note").textContent = "文件 " + entry.document.file_name +
    " · 共 " + entry.document.page_count + " 页 · SHA-256 " +
    String(entry.document.sha256).slice(0, 16) + "…";
}

function paintExtraction(entry) {
  const diffByPage = {};
  (entry.extraction_diffs || []).forEach((diff) => {
    if (diff.pdf_page_index0 != null) diffByPage[diff.pdf_page_index0] = diff;
  });
  $("col-extraction-body").innerHTML = entry.extraction.map((page) => {
    const index0 = page.pdf_page_index0;
    const diff = diffByPage[index0];
    const isCandidate = entry.candidate_source_pages0 &&
      entry.candidate_source_pages0.includes(index0);
    return `<tr class="${rowClass(entry, index0, "extraction")}" data-page-index="${index0}">` +
      `<td>p.${index0 + 1} · 索引 ${index0}</td>` +
      `<td>${esc(TEXT_STATE_LABELS[page.text_state] || page.text_state)}</td>` +
      `<td><code title="${esc(page.text_sha256 || "")}">${esc(shortHash(page.text_sha256))}</code></td>` +
      `<td>${isCandidate ? '<span class="tag tag-candidate">引用命中候选</span>' : "—"}</td>` +
      `<td>${diff ? `<span class="tag tag-diff" title="字段 ${esc(diff.field)}">✕ 与真值不符</span>` : "—"}</td>` +
      `</tr>`;
  }).join("");
  const located = entry.candidate_source_pages0 || [];
  $("col-extraction-note").textContent =
    "候选页(0-based) " + pages1(located) +
    " · 引用命中 " + (located.length > 0 ? "是" : "否（未在文本层找到）");
}

function paintChunkIndex(entry) {
  const chunk = entry.chunk;
  const indexRec = entry.index_record;
  const chunkReduced = entry.stage_diffs.some(
    (d) => d.stage === "chunking" && d.field === "source_page_indices0");
  const indexReduced = entry.stage_diffs.some(
    (d) => d.stage === "indexing" && d.field === "source_page_indices0");
  $("col-chunk-body").innerHTML = chunk
    ? `<tr class="${chunkReduced ? "row-diff" : ""}">` +
      `<td><code>${esc(chunk.chunk_id)}</code></td>` +
      `<td>${pages1(chunk.source_page_indices0)}（0-based）</td>` +
      `<td><code title="${esc(chunk.text_sha256 || "")}">${esc(shortHash(chunk.text_sha256))}</code></td>` +
      `<td>${chunkReduced ? '<span class="tag tag-diff">✕ 候选页被缩减</span>' : "—"}</td></tr>`
    : `<tr><td colspan="4">无分片记录（缺失）</td></tr>`;
  $("col-index-body").innerHTML = indexRec
    ? `<tr class="${indexReduced ? "row-diff" : ""}">` +
      `<td><code>${esc(indexRec.record_id)}</code></td>` +
      `<td>${pages1(indexRec.source_page_indices0)}（0-based）</td>` +
      `<td>label ${esc(indexRec.pdf_page_label)}</td></tr>`
    : `<tr><td colspan="3">无索引记录（缺失）</td></tr>`;
  const chunkNote = chunk
    ? "分片 source 页 " + pages1(chunk.source_page_indices0)
    : "分片记录缺失";
  const indexNote = indexRec
    ? "索引 source 页 " + pages1(indexRec.source_page_indices0)
    : "索引记录缺失";
  $("col-chunk-note").textContent = chunkNote + "；" + indexNote +
    "（分片与索引分别显示，不合并归因）";
}

function paintCitation(entry) {
  const correct = entry.correct_pdf_page_number1;
  const correctText = correct
    ? "PDF 页号(1-based) " + numbers1(correct) +
      " · 浏览器页(viewer) " + numbers1(entry.correct_viewer_page1)
    : "无可确认的正确来源页 — 引文在 PDF 文本层中无法定位";
  const viewer = entry.display && entry.display.viewer_page1 != null
    ? "p." + entry.display.viewer_page1 : "缺失";
  $("col-citation-body").innerHTML =
    "<dl>" +
    "<dt>原始 page value（模型/应用输出）</dt><dd>" +
      (entry.observed_page_value == null
        ? "缺失（无 page value）" : "p." + esc(entry.observed_page_value)) + "</dd>" +
    "<dt>page basis</dt><dd>" + esc(entry.citation_page_basis) + "</dd>" +
    "<dt>最终 viewer page（展示层）</dt><dd>" + esc(viewer) + "</dd>" +
    "<dt>实际应打开的页（正确来源）</dt><dd>" + esc(correctText) + "</dd>" +
    "<dt>verdict</dt><dd>" + badge(entry.verdict) + " <code>" + esc(entry.verdict) + "</code></dd>" +
    "<dt>故障类型</dt><dd>" + (entry.fault_type ? esc(entry.fault_type) : "无（对照）") + "</dd>" +
    "<dt>首错阶段</dt><dd>" + (entry.first_fault_stage ? esc(STAGE_LABELS[entry.first_fault_stage]) : "无") + "</dd>" +
    "<dt>quote SHA-256</dt><dd><code title=\"" + esc(entry.quote_sha256) + "\">" + esc(shortHash(entry.quote_sha256)) + "</code></dd>" +
    "</dl>";
}

function paintComparison() {
  // One row per visible citation: wrong page -> first fault stage ->
  // correct source location, for the whole filtered set.
  $("comparison-body").innerHTML = visibleEntries().map((entry) => {
    const wrong = entry.observed_page_value == null
      ? "缺失（无 page value）"
      : "p." + entry.observed_page_value + "（basis " + entry.citation_page_basis + "）";
    const correct = entry.correct_pdf_page_number1
      ? "PDF 页号(1-based) " + numbers1(entry.correct_pdf_page_number1) +
        "（物理页索引 0-based " + pages1(entry.correct_pdf_page_number1.map((n) => n - 1)) + "）"
      : "无可确认的正确来源页（引文未在文本层找到）";
    const correctCls = entry.correct_pdf_page_number1 ? "cell-correct" : "cell-unknown";
    return `<tr class="comparison-row" data-entry-id="${esc(entry.entry_id)}">` +
      `<td><code>${esc(entry.entry_id)}</code></td>` +
      `<td class="cell-wrong">${esc(wrong)}</td>` +
      `<td>${entry.first_fault_stage ? esc(STAGE_LABELS[entry.first_fault_stage]) : "无（对照 PASS）"}</td>` +
      `<td class="${correctCls}">${esc(correct)}</td>` +
      `<td>${badge(entry.verdict)}</td></tr>`;
  }).join("");
}

function paintDiffs(entry) {
  const box = $("stage-diff-list");
  if (entry.stage_diffs.length === 0) {
    box.innerHTML = '<p class="empty-note">本条引用在四个阶段均无差异（对照 PASS）。</p>';
    return;
  }
  box.innerHTML = "<ol>" + entry.stage_diffs.map((diff) =>
    "<li><strong>" + esc(STAGE_LABELS[diff.stage] || diff.stage) +
    "</strong> · 字段 <code>" + esc(diff.field) + "</code><br>" +
    esc(diff.note) + "</li>").join("") + "</ol>";
}

function paintAll() {
  const entry = findEntry(state.selectedEntryId);
  state.selectedEntryId = entry.entry_id;
  renderCitationList();
  paintTruth(entry);
  paintExtraction(entry);
  paintChunkIndex(entry);
  paintCitation(entry);
  paintComparison();
  paintDiffs(entry);
  $("raw-json").textContent = JSON.stringify(entry, null, 2);
  $("selected-summary").textContent = "当前选中：" + entry.entry_id +
    " · " + entry.verdict;
  document.querySelectorAll(".page-row").forEach((row) => {
    row.addEventListener("click", () => {
      const index0 = Number(row.getAttribute("data-page-index"));
      state.selectedPageIndex0 =
        state.selectedPageIndex0 === index0 ? null : index0;
      paintAll();
    });
  });
}

function selectEntry(entryId) {
  state.selectedEntryId = entryId;
  state.selectedPageIndex0 = null;
  if (window.history && window.history.replaceState) {
    window.history.replaceState(null, "", "#case=" + encodeURIComponent(entryId));
  }
  paintAll();
}

function downloadReport() {
  const blob = new Blob([JSON.stringify(REPORT, null, 2)],
    { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "pagetrace-report.json";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function init() {
  const match = (window.location.hash || "").match(/case=([^&]+)/);
  const requested = match ? decodeURIComponent(match[1]) : null;
  state.selectedEntryId = requested && findEntry(requested)
    ? requested : (ENTRIES[0] ? ENTRIES[0].entry_id : null);
  ["filter-fault", "filter-stage", "filter-status"].forEach((id) => {
    $(id).addEventListener("change", () => {
      const visible = visibleEntries();
      if (visible.length > 0 &&
          !visible.some((e) => e.entry_id === state.selectedEntryId)) {
        state.selectedEntryId = visible[0].entry_id;
      }
      paintAll();
    });
  });
  $("download-json").addEventListener("click", downloadReport);
  $("copy-json").addEventListener("click", () => {
    const text = JSON.stringify(findEntry(state.selectedEntryId), null, 2);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text);
    } else {
      const area = document.createElement("textarea");
      area.value = text;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }
  });
  $("citation-list").addEventListener("click", (event) => {
    const button = event.target.closest(".citation-item");
    if (button) selectEntry(button.getAttribute("data-entry-id"));
  });
  $("comparison-body").addEventListener("click", (event) => {
    const row = event.target.closest(".comparison-row");
    if (row) selectEntry(row.getAttribute("data-entry-id"));
  });
  paintAll();
}

document.addEventListener("DOMContentLoaded", init);
