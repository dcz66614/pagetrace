"""P026 T010 — ``pagetrace.bundle/v1`` parser: parse, validate, preserve raw.

What this module does
---------------------
* Parse a bundle from a dict, a JSON string/bytes, or a file path.
* Validate it in two layers:

  1. **Schema layer** (``contracts.validate_bundle_schema``): the frozen
     ``pagetrace.bundle/v1`` JSON Schema — exact ``schema`` const, field
     types, ``additionalProperties: false`` everywhere (unknown fields
     rejected, policy ``"reject"``), ``UNKNOWN`` basis forces
     ``viewer_page1`` null, ``sha256`` pattern, ``page_count`` 1–500.
  2. **Runtime layer** (cross-field rules the schema cannot express,
     ``docs/PAGE_SEMANTICS.md`` §5): ``missing_stages`` must list exactly
     the stages with no snapshot; ``source_page_indices0`` must be
     sorted (schema enforces uniqueness only); every index / viewer
     page must be inside ``[0, page_count-1]`` / ``[1, page_count]``
     (R-05, never clamped); extraction indices must be unique and in
     order; non-null ``citation_page_value`` must agree in type and
     range with its basis (R-08); duplicate ids are rejected;
     ``document.file_name`` must be a bare file name with no directory
     or absolute path (R-11, FIX-R1 P1-R1-04 — POSIX, Windows drive,
     UNC and relative-directory forms all rejected, and the offending
     value is never echoed in an error message).

  All runtime violations are collected and reported together in one
  :class:`BundleValidationError` (``.errors``), never silently fixed.

What this module deliberately does NOT do
------------------------------------------
* **No implicit 0/1-based conversion.** Raw ``citation_page_value`` /
  ``citation_page_basis`` / ``viewer_page1`` are stored verbatim.
  Conversion happens only through the explicit, named helpers in
  ``contracts`` (``to_number1`` / ``to_index0`` / ``resolve_citation_to_index0``)
  and only when a caller asks for it.
* **No fault judgement.** A bundle whose stages disagree (an offset
  display value, a missing chunk record, a null viewer page, a
  dangling ``chunk_id`` reference) is *fault data for the analyser*,
  not a malformed bundle — the T002 fixtures prove it: e.g.
  ``mm-chk-05`` cites a chunk record that is absent, ``mm-dsp-10``
  has no display record for its fault citation, ``mm-dsp-11`` has a
  null display value/viewer. The parser accepts all of that and
  exposes it (``unresolved_chunk_refs``, ``unresolved_index_refs``,
  ``citations_without_display``, ``missing_extraction_pages``) so the
  analyser (T004 ``verdicts`` / ``compare_stages``) can blame the
  right stage. Only *structural* breakage is rejected.
* **No label arithmetic** (R-03). Labels are looked up in the label
  map built from the extraction records; a label with no map entry is
  unresolvable, never parsed as a number.
* **No hash guessing.** :meth:`TraceBundle.verify_document_hash`
  compares ``document.sha256`` against the exact PDF bytes supplied by
  the caller and raises ``INPUT_HASH_MISMATCH`` on disagreement; the
  parser never reads a PDF itself and never trusts a file name.

Missing vs empty vs zero (R-07)
--------------------------------
* A stage key absent from ``stages`` **and** listed in
  ``missing_stages`` → genuinely missing (``is_stage_present`` False).
* A stage key present with ``[]`` → present-but-empty; recorded in
  ``empty_stages`` and never counted as "checked and clean".
* A stage key absent but **not** listed (or listed but present) →
  validation error: the bundle lies about what it contains.
* ``source_page_indices0 == []`` → verified-empty set, kept as ``[]``.
* Page value ``0`` → the legitimate first physical page, never "missing".
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from pagetrace.contracts import (
    STAGES,
    BundleValidationError,
    PageSemanticsError,
    SchemaValidationError,
    UnresolvableLabelError,
    label_to_index0,
    resolve_citation_to_index0,
    sha256_hex,
    to_viewer1,
    validate_bundle_schema,
    validate_source_pages0,
)

__all__ = [
    "TraceBundle",
    "is_bare_file_name",
    "parse_bundle",
    "parse_bundle_json",
    "load_bundle",
    "load_bundle_file",
]

_INPUT_HASH_MISMATCH = "INPUT_HASH_MISMATCH"

#: FIX-R1 (P1-R1-04, R-11): ``document.file_name`` is a bare file name
#: only. The same rule lives in the bundle schema
#: (``contracts/pagetrace.bundle.v1.schema.json``, ``file_name.pattern``)
#: and is re-checked at runtime here, so a bundle is rejected even if
#: the schema layer is ever bypassed. Rejects POSIX absolute paths
#: (``/home/...``), Windows drive paths (``C:\\...``, ``C:/...``,
#: drive-relative ``C:...``), UNC paths (``\\\\server\\share\\...``,
#: ``//server/share/...``) and any relative directory form
#: (``sub/file.pdf``, ``../file.pdf``, ``..\\file.pdf``), plus the bare
#: directory references ``.`` and ``..``. A name containing ``:`` after
#: the first character (e.g. ``ab:c.pdf``) is not a drive letter and is
#: allowed; control characters are never allowed in a file name.
_BARE_FILE_NAME_RE = re.compile(r"^(?![A-Za-z]:)(?!\.{1,2}$)[^/\\]+$")


def is_bare_file_name(value: Any) -> bool:
    """True iff *value* is a bare PDF file name (R-11, no directories).

    Non-strings, empty strings, names containing ``/`` or ``\\``, names
    starting with a Windows drive letter (``C:``), ``.`` / ``..``, and
    names containing control characters are all rejected.
    """
    if not isinstance(value, str) or not value:
        return False
    if any(ord(ch) < 0x20 for ch in value):
        return False
    return _BARE_FILE_NAME_RE.match(value) is not None


def _redact_file_name(message: str, file_name: Any) -> str:
    """Remove a raw ``file_name`` value from an error message, if present.

    A rejected absolute path must never be echoed back to the terminal:
    the validation error names the rule, never the offending value
    (§13 path minimisation). Non-string values cannot leak a path.
    """
    if isinstance(file_name, str) and file_name and file_name in message:
        return message.replace(file_name, "[redacted file_name]")
    return message


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class TraceBundle:
    """A parsed, validated ``pagetrace.bundle/v1`` bundle.

    ``raw`` is a deep copy of the input as given — the parser never
    mutates it, and every accessor returns a copy, so downstream code
    cannot corrupt the preserved original values. ``to_dict()`` returns
    another deep copy of the same raw document.
    """

    def __init__(self, data: dict):
        if not isinstance(data, dict):
            raise SchemaValidationError(
                f"bundle must be a JSON object, got {type(data).__name__}")
        # R-11 pre-check (FIX-R1, P1-R1-04): reject a non-bare
        # document.file_name BEFORE the schema layer runs, so the
        # jsonschema error text can never echo the offending absolute
        # path back to the caller. The message names the rule only,
        # never the value. The schema pattern enforces the same rule;
        # _runtime_errors() below re-checks it as defence in depth.
        document = data.get("document")
        file_name = (document.get("file_name")
                     if isinstance(document, dict) else None)
        if file_name is not None and not is_bare_file_name(file_name):
            raise BundleValidationError(
                "document.file_name must be a bare file name (no "
                "directory, no absolute path)",
                errors=["document.file_name must be a bare file name "
                        "(no directory, no absolute path)"],
            )
        # Schema layer first (exact version, types, unknown fields).
        try:
            validate_bundle_schema(data)
        except SchemaValidationError as exc:
            # Belt and braces: never let a raw file_name value leak
            # through a schema error message (e.g. a pattern failure
            # quoting the offending instance).
            clean = _redact_file_name(str(exc), file_name)
            clean_errors = [_redact_file_name(e, file_name)
                            for e in getattr(exc, "errors", [])]
            raise SchemaValidationError(clean, errors=clean_errors) from exc
        # Runtime layer: collect every cross-field violation, then raise once.
        errors = self._runtime_errors(data)
        if errors:
            raise BundleValidationError(
                f"bundle fails runtime validation ({len(errors)} error(s)): "
                + "; ".join(errors),
                errors=errors,
            )
        self._raw: dict = copy.deepcopy(data)
        self._build_indexes()

    # -- runtime validation -------------------------------------------------

    @staticmethod
    def _runtime_errors(data: dict) -> list[str]:
        errors: list[str] = []
        stages: dict = data.get("stages", {})
        page_count: int = data["document"]["page_count"]
        missing: list = stages.get("missing_stages", [])

        # R-11 (FIX-R1, P1-R1-04): document.file_name must be a bare
        # file name — no '/', no '\\', no drive letter, no UNC prefix,
        # not '.' / '..'. Runtime re-check of the schema pattern, so
        # the rule holds even if the schema layer is bypassed. The
        # message never echoes the offending value (§13).
        document = data.get("document")
        file_name = (document.get("file_name")
                     if isinstance(document, dict) else None)
        if file_name is not None and not is_bare_file_name(file_name):
            errors.append(
                "document.file_name must be a bare file name (no "
                "directory, no absolute path)")

        # missing_stages must list exactly the stages with no snapshot.
        for stage in STAGES:
            present = stage in stages
            listed = stage in missing
            if present and listed:
                errors.append(
                    f"stages.missing_stages lists {stage!r} but a "
                    f"{stage!r} snapshot is present")
            if not present and not listed:
                errors.append(
                    f"stage {stage!r} has no snapshot but is not listed "
                    "in stages.missing_stages")

        # Extraction: indices unique, in order, in range; one record per
        # page is the contract's description, but a gap is fault data
        # (PAGE_METADATA_MISSING), not a malformed bundle — gaps are
        # exposed via missing_extraction_pages, not rejected here.
        extraction = stages.get("extraction")
        if isinstance(extraction, list):
            seen: set[int] = set()
            prev: int | None = None
            for rec in extraction:
                idx = rec.get("pdf_page_index0")
                if not _is_int(idx):
                    errors.append(
                        f"extraction pdf_page_index0 must be an integer, "
                        f"got {idx!r}")
                    continue
                if not 0 <= idx <= page_count - 1:
                    errors.append(
                        f"extraction pdf_page_index0={idx} out of range "
                        f"[0, {page_count - 1}]")
                if idx in seen:
                    errors.append(
                        f"extraction pdf_page_index0={idx} appears twice")
                seen.add(idx)
                if prev is not None and idx <= prev:
                    errors.append(
                        "extraction records must be in pdf_page_index0 "
                        f"order, got {prev} before {idx}")
                prev = idx

        # Chunking / indexing: source_page_indices0 sorted, in range;
        # duplicate record ids rejected.
        for stage, id_field in (("chunking", "chunk_id"),
                                ("indexing", "record_id")):
            records = stages.get(stage)
            if not isinstance(records, list):
                continue
            seen_ids: set[str] = set()
            for rec in records:
                rid = rec.get(id_field)
                if rid in seen_ids:
                    errors.append(
                        f"{stage} {id_field}={rid!r} appears twice")
                seen_ids.add(rid)
                try:
                    validate_source_pages0(rec.get("source_page_indices0"),
                                           page_count)
                except PageSemanticsError as exc:
                    errors.append(f"{stage} {id_field}={rid!r}: {exc}")

        # Display: viewer_page1 in range when present; value/basis type
        # and range agreement (R-08 / R-05) when the value is present.
        # A null value / null viewer is a missing-metadata signal, not a
        # structural error — it is preserved, never defaulted.
        display = stages.get("display")
        if isinstance(display, list):
            seen_citations: set[str] = set()
            for rec in display:
                cid = rec.get("citation_id")
                if cid in seen_citations:
                    errors.append(
                        f"display citation_id={cid!r} appears twice")
                seen_citations.add(cid)
                viewer = rec.get("viewer_page1")
                if viewer is not None:
                    if not _is_int(viewer):
                        errors.append(
                            f"display citation {cid!r}: viewer_page1 must "
                            f"be an integer or null, got {viewer!r}")
                    elif not 1 <= viewer <= page_count:
                        errors.append(
                            f"display citation {cid!r}: viewer_page1={viewer} "
                            f"out of range [1, {page_count}]")
                value = rec.get("citation_page_value")
                basis = rec.get("citation_page_basis")
                if value is not None:
                    if basis in ("PDF_INDEX_0", "PDF_NUMBER_1"):
                        if not _is_int(value):
                            errors.append(
                                f"display citation {cid!r}: citation_page_value "
                                f"must be an integer for basis {basis}, "
                                f"got {value!r}")
                        elif basis == "PDF_INDEX_0" and not (
                                0 <= value <= page_count - 1):
                            errors.append(
                                f"display citation {cid!r}: citation_page_value="
                                f"{value} out of range [0, {page_count - 1}] "
                                "for basis PDF_INDEX_0")
                        elif basis == "PDF_NUMBER_1" and not (
                                1 <= value <= page_count):
                            errors.append(
                                f"display citation {cid!r}: citation_page_value="
                                f"{value} out of range [1, {page_count}] "
                                "for basis PDF_NUMBER_1")
                    elif basis == "PDF_LABEL":
                        if not isinstance(value, str):
                            errors.append(
                                f"display citation {cid!r}: citation_page_value "
                                f"must be a string for basis PDF_LABEL, "
                                f"got {value!r}")

        # Citations: duplicate citation_id rejected. Dangling chunk /
        # index references are fault data, exposed, not rejected.
        seen_citations = set()
        for cit in data.get("citations", []):
            cid = cit.get("citation_id")
            if cid in seen_citations:
                errors.append(f"citation_id={cid!r} appears twice")
            seen_citations.add(cid)
        return errors

    # -- indexes built from the validated raw document ----------------------

    def _build_indexes(self) -> None:
        data = self._raw
        self._stages: dict = data["stages"]
        self._citations: list[dict] = data["citations"]
        self.citation_by_id: dict[str, dict] = {
            c["citation_id"]: c for c in self._citations}
        self.chunk_by_id: dict[str, dict] = {
            c["chunk_id"]: c
            for c in self._stages.get("chunking", []) or []}
        self.index_by_id: dict[str, dict] = {
            r["record_id"]: r
            for r in self._stages.get("indexing", []) or []}
        self.display_by_citation_id: dict[str, dict] = {
            r["citation_id"]: r
            for r in self._stages.get("display", []) or []}
        self.extraction_by_index: dict[int, dict] = {
            r["pdf_page_index0"]: r
            for r in self._stages.get("extraction", []) or []}
        # Label map from extraction records (lookup only, R-03). A label
        # shared by several pages is ambiguous: keep the first page and
        # record the ambiguity instead of guessing.
        self.label_map: dict[str, int] = {}
        self.ambiguous_labels: list[str] = []
        for rec in self._stages.get("extraction", []) or []:
            label = rec.get("pdf_page_label")
            if label is None:
                continue
            idx = rec["pdf_page_index0"]
            if label in self.label_map and self.label_map[label] != idx:
                if label not in self.ambiguous_labels:
                    self.ambiguous_labels.append(label)
            else:
                self.label_map.setdefault(label, idx)
        # Informational gaps (fault data, not validation errors).
        present_extraction = set(self.extraction_by_index)
        self.missing_extraction_pages: list[int] = [
            i for i in range(self.page_count) if i not in present_extraction
        ] if self.is_stage_present("extraction") else list(range(self.page_count))
        self.unresolved_chunk_refs: list[str] = sorted({
            c["chunk_id"] for c in self._citations
            if c.get("chunk_id") is not None
            and c["chunk_id"] not in self.chunk_by_id})
        self.unresolved_index_refs: list[str] = sorted({
            c["index_record_id"] for c in self._citations
            if c.get("index_record_id") is not None
            and c["index_record_id"] not in self.index_by_id})
        self.citations_without_display: list[str] = sorted(
            cid for cid in self.citation_by_id
            if cid not in self.display_by_citation_id)

    # -- identity / document --------------------------------------------------

    @property
    def raw(self) -> dict:
        """Deep copy of the bundle exactly as parsed (raw values preserved)."""
        return copy.deepcopy(self._raw)

    @property
    def schema(self) -> str:
        return self._raw["schema"]

    @property
    def case_id(self) -> str:
        return self._raw["case_id"]

    @property
    def document(self) -> dict:
        return copy.deepcopy(self._raw["document"])

    @property
    def file_name(self) -> str:
        return self._raw["document"]["file_name"]

    @property
    def document_sha256(self) -> str:
        return self._raw["document"]["sha256"]

    @property
    def page_count(self) -> int:
        return self._raw["document"]["page_count"]

    # -- stages: present / missing / empty (R-07) ----------------------------

    @property
    def missing_stages(self) -> list[str]:
        """Stages with no snapshot at all, exactly as listed (explicit)."""
        return list(self._stages["missing_stages"])

    @property
    def present_stages(self) -> list[str]:
        """Stages that have a snapshot key (even if the array is empty)."""
        return [s for s in STAGES if s in self._stages]

    @property
    def empty_stages(self) -> list[str]:
        """Present stages whose snapshot array is empty.

        An empty array is NOT "checked and clean": callers must treat
        these stages as carrying no evidence, never as a pass.
        """
        return [s for s in STAGES
                if isinstance(self._stages.get(s), list)
                and self._stages[s] == []]

    def is_stage_present(self, stage: str) -> bool:
        """True iff *stage* has a snapshot (empty array still counts)."""
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage!r}; expected one of {STAGES}")
        return stage in self._stages

    def is_stage_missing(self, stage: str) -> bool:
        """True iff *stage* is listed in ``missing_stages``."""
        return stage in self.missing_stages

    @property
    def stages(self) -> dict:
        return copy.deepcopy(self._stages)

    # -- records ---------------------------------------------------------------

    @property
    def citations(self) -> list[dict]:
        return copy.deepcopy(self._citations)

    def citation(self, citation_id: str) -> dict | None:
        rec = self.citation_by_id.get(citation_id)
        return copy.deepcopy(rec) if rec is not None else None

    def chunk_record(self, chunk_id: str) -> dict | None:
        rec = self.chunk_by_id.get(chunk_id)
        return copy.deepcopy(rec) if rec is not None else None

    def index_record(self, record_id: str) -> dict | None:
        rec = self.index_by_id.get(record_id)
        return copy.deepcopy(rec) if rec is not None else None

    def display_record(self, citation_id: str) -> dict | None:
        rec = self.display_by_citation_id.get(citation_id)
        return copy.deepcopy(rec) if rec is not None else None

    def extraction_record(self, pdf_page_index0: int) -> dict | None:
        rec = self.extraction_by_index.get(pdf_page_index0)
        return copy.deepcopy(rec) if rec is not None else None

    # -- raw values, verbatim ---------------------------------------------------

    def raw_citation_page_value(self, citation_id: str) -> Any:
        """Raw ``citation_page_value`` exactly as emitted (int/str/None).

        Never converted, never defaulted. Raises ``KeyError`` for an
        unknown citation and ``PageSemanticsError`` when the citation
        has no display record at all (missing, not zero).
        """
        rec = self.display_by_citation_id.get(citation_id)
        if rec is None:
            raise PageSemanticsError(
                f"citation {citation_id!r} has no display record: "
                "no page value exists to return (missing, not 0)")
        return copy.deepcopy(rec["citation_page_value"])

    def raw_citation_page_basis(self, citation_id: str) -> str:
        rec = self.display_by_citation_id.get(citation_id)
        if rec is None:
            raise PageSemanticsError(
                f"citation {citation_id!r} has no display record")
        return rec["citation_page_basis"]

    # -- explicit conversions (caller-asked only, never implicit) ---------------

    def resolve_citation_to_index0(self, citation_id: str) -> int:
        """Resolve a citation's display value to canonical index0.

        Uses the display record's own basis (never re-inferred) and the
        extraction label map. Raises :class:`UnknownBasisError` for
        ``UNKNOWN`` (R-04), :class:`UnresolvableLabelError` for a label
        with no map entry (R-03), and :class:`PageSemanticsError` when
        the value is null or the display record is absent.
        """
        rec = self.display_by_citation_id.get(citation_id)
        if rec is None:
            raise PageSemanticsError(
                f"citation {citation_id!r} has no display record")
        return resolve_citation_to_index0(
            rec["citation_page_value"], rec["citation_page_basis"],
            self.page_count, label_map=self.label_map)

    def correct_viewer_page1(self, citation_id: str) -> int:
        """Correct viewer target (1-based) for a citation: index0 + 1 (R-01)."""
        return to_viewer1(self.resolve_citation_to_index0(citation_id),
                          self.page_count)

    def label_to_index0(self, label: str) -> int:
        """Look a PDF page label up in the extraction label map (R-03)."""
        if label in self.ambiguous_labels:
            raise UnresolvableLabelError(
                f"label {label!r} maps to several pages; ambiguous, not guessed")
        return label_to_index0(label, self.label_map)

    # -- document hash (PROJECT_BOOK §6.3: INPUT_HASH_MISMATCH) -----------------

    def verify_document_hash(self, pdf_bytes: bytes) -> None:
        """Compare ``document.sha256`` with the SHA-256 of *pdf_bytes*.

        Raises :class:`BundleValidationError` with code
        ``INPUT_HASH_MISMATCH`` on disagreement; returns ``None`` on match.
        """
        actual = sha256_hex(pdf_bytes)
        if actual != self.document_sha256:
            raise BundleValidationError(
                f"document sha256 mismatch for {self.file_name!r}: bundle "
                f"claims {self.document_sha256}, actual PDF bytes hash to "
                f"{actual} (INPUT_HASH_MISMATCH)",
                errors=[f"document.sha256: expected {self.document_sha256}, "
                        f"got {actual}"],
                code=_INPUT_HASH_MISMATCH,
            )

    def verify_document_hash_file(self, pdf_path: str | Path) -> None:
        """Like :meth:`verify_document_hash`, reading the PDF from disk."""
        with open(pdf_path, "rb") as fh:
            self.verify_document_hash(fh.read())

    def document_hash_matches(self, pdf_bytes: bytes) -> bool:
        """True iff ``document.sha256`` equals the hash of *pdf_bytes*."""
        return sha256_hex(pdf_bytes) == self.document_sha256

    # -- serialisation -----------------------------------------------------------

    def to_dict(self) -> dict:
        """Deep copy of the bundle document (raw values preserved)."""
        return copy.deepcopy(self._raw)

    def to_json(self) -> str:
        """Canonical JSON rendering (sorted keys, UTF-8, 2-space indent)."""
        return json.dumps(self._raw, ensure_ascii=False, sort_keys=True,
                          indent=2)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"TraceBundle(case_id={self.case_id!r}, "
                f"page_count={self.page_count}, "
                f"missing_stages={self.missing_stages!r})")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def parse_bundle(data: dict) -> TraceBundle:
    """Parse and validate a bundle dict. Raises on any violation."""
    return TraceBundle(data)


def parse_bundle_json(text: str | bytes) -> TraceBundle:
    """Parse and validate a bundle from a JSON string/bytes.

    Malformed JSON raises :class:`BundleValidationError` (not a bare
    ``json.JSONDecodeError``) so callers handle one error family.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BundleValidationError(
            f"bundle is not valid JSON: {exc}",
            errors=[str(exc)]) from exc
    return TraceBundle(data)


def load_bundle(source: str | Path | dict | bytes) -> TraceBundle:
    """Parse a bundle from a dict, JSON text/bytes, or a file path.

    A ``str`` that parses as JSON is treated as JSON text; otherwise it
    is treated as a file path. ``bytes`` are JSON text. ``dict`` is used
    as-is. Missing files raise :class:`BundleValidationError`.
    """
    if isinstance(source, dict):
        return TraceBundle(source)
    if isinstance(source, bytes):
        return parse_bundle_json(source)
    if isinstance(source, Path):
        return load_bundle_file(source)
    if isinstance(source, str):
        stripped = source.lstrip()
        if stripped.startswith("{"):
            return parse_bundle_json(source)
        return load_bundle_file(source)
    raise TypeError(f"cannot load bundle from {type(source).__name__}")


def load_bundle_file(path: str | Path) -> TraceBundle:
    """Parse and validate a bundle JSON file."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BundleValidationError(
            f"cannot read bundle file {path}: {exc}",
            errors=[str(exc)]) from exc
    try:
        return parse_bundle_json(text)
    except SchemaValidationError as exc:
        # Re-raise with the file named, keeping the collected .errors.
        raise SchemaValidationError(f"{path}: {exc}",
                                    errors=getattr(exc, "errors", [])) from exc
    except BundleValidationError as exc:
        raise BundleValidationError(f"{path}: {exc}",
                                    errors=getattr(exc, "errors", []),
                                    code=getattr(exc, "code", None)) from exc
