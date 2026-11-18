/* P026 PageTrace — T005 four-column linked interaction prototype.
 *
 * Offline only: no network requests, no CDN, no remote fonts. All demo data
 * is embedded below (generated from frozen T002/T003/T004 evidence by
 * tests/prototypes/build_prototype_data.py — never re-implements verdict
 * logic). Open prototypes/report-prototype.html directly from disk.
 *
 * Deep link: report-prototype.html#case=<case_id> preselects a citation,
 * e.g. #case=du-chk-01. Used for stepwise screenshots.
 */
"use strict";

/* BEGIN GENERATED DATA (build_prototype_data.py) */
const PROTOTYPE_CASES = [
  {
    "candidate_source_pages0": [
      2
    ],
    "case_id": "po-ext-01",
    "chunks": [
      {
        "chunk_id": "c-fault",
        "source_page_indices0": [
          3
        ],
        "text_sha256": "dd42af760f4fa8e8d23ceb4916a3b139ae49d02943df90df72036a44326e765a"
      },
      {
        "chunk_id": "c-control",
        "source_page_indices0": [
          4
        ],
        "text_sha256": "47347e11b6283796e7a69eef2d4c2923e596659425e925154874c4d04be2512b"
      }
    ],
    "citation_id": "cite-fault",
    "citation_page_basis": "PDF_NUMBER_1",
    "correct_pdf_page_number1": [
      3
    ],
    "correct_viewer_page1": [
      3
    ],
    "display": {
      "citation_id": "cite-fault",
      "citation_page_basis": "PDF_NUMBER_1",
      "citation_page_value": 4,
      "viewer_page1": 4
    },
    "document": {
      "file_name": "po-ext-01.pdf",
      "page_count": 5,
      "sha256": "97d1f68a573e09c9b6fc519dde6d37ee25158ee4f6673488770e2debef7cb9cf"
    },
    "expected_source_pages0": [
      2
    ],
    "extraction": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "8e534a38b1b68025beddfecd7bd757e6145157ba251ef3ff8dc802a63c34d9a7",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": "9030819870f0541f2263033a61e15a5fb764788cc2bd2015740bc47d87818b5c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": "3aa9712445bbab6b7d69ca0368e349c42514e92959aa7c97e48dfa82b1bfc6e1",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "6c896df0e9848a00ce560aa27d919dcef24dd26ad7221884746d08d96c4c01b0",
        "text_state": "TEXT"
      }
    ],
    "fault_type": "PAGE_OFFSET",
    "first_fault_stage": "extraction",
    "index_records": [
      {
        "pdf_page_label": "4",
        "record_id": "v-fault",
        "source_page_indices0": [
          3
        ]
      },
      {
        "pdf_page_label": "5",
        "record_id": "v-control",
        "source_page_indices0": [
          4
        ]
      }
    ],
    "locate_fault_quote": {
      "candidate_source_pages0": [
        2
      ],
      "expected_candidate_source_pages0": [
        2
      ],
      "match": true,
      "span_status": "single_page"
    },
    "observed_page_value": 4,
    "quote_sha256": "dd42af760f4fa8e8d23ceb4916a3b139ae49d02943df90df72036a44326e765a",
    "quote_text": "关键引文po-ext-01：页码漂移误导定位。",
    "stage_diffs": [
      {
        "downstream_value": "9030819870f0541f2263033a61e15a5fb764788cc2bd2015740bc47d87818b5c",
        "field": "text_sha256",
        "kind": "hash_mismatch",
        "note": "extraction text_sha256 for page 2 does not match the honest extraction (text of another page attached?)",
        "pdf_page_index0": 2,
        "stage": "extraction",
        "upstream_value": "3aa9712445bbab6b7d69ca0368e349c42514e92959aa7c97e48dfa82b1bfc6e1"
      },
      {
        "downstream_value": "3aa9712445bbab6b7d69ca0368e349c42514e92959aa7c97e48dfa82b1bfc6e1",
        "field": "text_sha256",
        "kind": "hash_mismatch",
        "note": "extraction text_sha256 for page 3 does not match the honest extraction (text of another page attached?)",
        "pdf_page_index0": 3,
        "stage": "extraction",
        "upstream_value": "9030819870f0541f2263033a61e15a5fb764788cc2bd2015740bc47d87818b5c"
      },
      {
        "downstream_value": "9030819870f0541f2263033a61e15a5fb764788cc2bd2015740bc47d87818b5c",
        "field": "text_sha256",
        "kind": "offset",
        "note": "cite-fault: extraction text_sha256 for page 2 does not match the honest extraction (text of another page attached?)",
        "pdf_page_index0": null,
        "stage": "extraction",
        "upstream_value": "3aa9712445bbab6b7d69ca0368e349c42514e92959aa7c97e48dfa82b1bfc6e1"
      }
    ],
    "truth_pages": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "8e534a38b1b68025beddfecd7bd757e6145157ba251ef3ff8dc802a63c34d9a7",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": "3aa9712445bbab6b7d69ca0368e349c42514e92959aa7c97e48dfa82b1bfc6e1",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": "9030819870f0541f2263033a61e15a5fb764788cc2bd2015740bc47d87818b5c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "6c896df0e9848a00ce560aa27d919dcef24dd26ad7221884746d08d96c4c01b0",
        "text_state": "TEXT"
      }
    ],
    "variant": "plus-one-shift",
    "verdict": "FAIL_PAGE_OFFSET"
  },
  {
    "candidate_source_pages0": [
      2
    ],
    "case_id": "mm-ext-01",
    "chunks": [
      {
        "chunk_id": "c-fault",
        "source_page_indices0": [
          2
        ],
        "text_sha256": "ce394d433fb3025ef7569b238ff4acb335ccdd729ab4da209287f47582cc6a0c"
      },
      {
        "chunk_id": "c-control",
        "source_page_indices0": [
          4
        ],
        "text_sha256": "d709e1ebc4c946f9d81b558df58bb5285611bdfa78752a4db85ba27b7ca8bf62"
      }
    ],
    "citation_id": "cite-fault",
    "citation_page_basis": "PDF_NUMBER_1",
    "correct_pdf_page_number1": [
      3
    ],
    "correct_viewer_page1": [
      3
    ],
    "display": {
      "citation_id": "cite-fault",
      "citation_page_basis": "PDF_NUMBER_1",
      "citation_page_value": 3,
      "viewer_page1": 3
    },
    "document": {
      "file_name": "mm-ext-01.pdf",
      "page_count": 5,
      "sha256": "50470bd0249d80aef1d433456c7a30648d510134af54546a613d71b5aa37a95b"
    },
    "expected_source_pages0": [
      2
    ],
    "extraction": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "b908bb56e6a97529665b8183dd613b83b0f793c88b54617c2fec042e9f0f9c8c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": null,
        "text_state": "ERROR"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": null,
        "text_state": "IMAGE_ONLY"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "b30bcd3afce23c9e32c21078d68e8b0d1d5cb638f0f76f5aad7b2420544757b0",
        "text_state": "TEXT"
      }
    ],
    "fault_type": "PAGE_METADATA_MISSING",
    "first_fault_stage": "extraction",
    "index_records": [
      {
        "pdf_page_label": "3",
        "record_id": "v-fault",
        "source_page_indices0": [
          2
        ]
      },
      {
        "pdf_page_label": "5",
        "record_id": "v-control",
        "source_page_indices0": [
          4
        ]
      }
    ],
    "locate_fault_quote": {
      "candidate_source_pages0": [
        2
      ],
      "expected_candidate_source_pages0": [
        2
      ],
      "match": true,
      "span_status": "single_page"
    },
    "observed_page_value": 3,
    "quote_sha256": "ce394d433fb3025ef7569b238ff4acb335ccdd729ab4da209287f47582cc6a0c",
    "quote_text": "关键引文mm-ext-01：页码漂移误导定位。",
    "stage_diffs": [
      {
        "downstream_value": "ERROR",
        "field": "text_state",
        "kind": "missing",
        "note": "extraction text_state for page 2 is 'ERROR', honest extraction says 'TEXT'",
        "pdf_page_index0": 2,
        "stage": "extraction",
        "upstream_value": "TEXT"
      },
      {
        "downstream_value": "ERROR",
        "field": "text_state",
        "kind": "missing",
        "note": "cite-fault: extraction text_state for page 2 is 'ERROR', honest extraction says 'TEXT'",
        "pdf_page_index0": null,
        "stage": "extraction",
        "upstream_value": "TEXT"
      }
    ],
    "truth_pages": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "b908bb56e6a97529665b8183dd613b83b0f793c88b54617c2fec042e9f0f9c8c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": null,
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": null,
        "text_state": "IMAGE_ONLY"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "b30bcd3afce23c9e32c21078d68e8b0d1d5cb638f0f76f5aad7b2420544757b0",
        "text_state": "TEXT"
      }
    ],
    "variant": "record-text-state-error",
    "verdict": "FAIL_METADATA_MISSING"
  },
  {
    "candidate_source_pages0": [
      2,
      4
    ],
    "case_id": "du-chk-01",
    "chunks": [
      {
        "chunk_id": "c-fault",
        "source_page_indices0": [
          2
        ],
        "text_sha256": "d4f312e79f1b155bdceea984dc0255a58c8142270a8235c376cf467fdaa4d873"
      },
      {
        "chunk_id": "c-control",
        "source_page_indices0": [
          4
        ],
        "text_sha256": "7867bada735b51c57024ee3b0781964325a4600b3942615fc15baee21805b787"
      }
    ],
    "citation_id": "cite-fault",
    "citation_page_basis": "PDF_NUMBER_1",
    "correct_pdf_page_number1": [
      3,
      5
    ],
    "correct_viewer_page1": [
      3,
      5
    ],
    "display": {
      "citation_id": "cite-fault",
      "citation_page_basis": "PDF_NUMBER_1",
      "citation_page_value": 3,
      "viewer_page1": 3
    },
    "document": {
      "file_name": "du-chk-01.pdf",
      "page_count": 5,
      "sha256": "5449bd32a5c224c1997470ed41f20998b06733d090eab92ed7fc07501d2ae79f"
    },
    "expected_source_pages0": [
      2,
      4
    ],
    "extraction": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "8e534a38b1b68025beddfecd7bd757e6145157ba251ef3ff8dc802a63c34d9a7",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": "2975051e81aa19f99b410168fff1128805d1642d18127099dd0912713ecccb70",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": null,
        "text_state": "IMAGE_ONLY"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "e1cba8416a4df5ea385360a3dc34b681f8488fde5e7473d4c09dc4cd934ead10",
        "text_state": "TEXT"
      }
    ],
    "fault_type": "DUPLICATE_TEXT_AMBIGUITY",
    "first_fault_stage": "chunking",
    "index_records": [
      {
        "pdf_page_label": "3",
        "record_id": "v-fault",
        "source_page_indices0": [
          2
        ]
      },
      {
        "pdf_page_label": "5",
        "record_id": "v-control",
        "source_page_indices0": [
          4
        ]
      }
    ],
    "locate_fault_quote": {
      "candidate_source_pages0": [
        2,
        4
      ],
      "expected_candidate_source_pages0": [
        2,
        4
      ],
      "match": true,
      "span_status": "single_page"
    },
    "observed_page_value": 3,
    "quote_sha256": "d4f312e79f1b155bdceea984dc0255a58c8142270a8235c376cf467fdaa4d873",
    "quote_text": "重复句du-chk-01：本句在多页出现，须保留全部候选页。",
    "stage_diffs": [
      {
        "downstream_value": [
          2
        ],
        "field": "source_page_indices0",
        "kind": "reduced",
        "note": "cite-fault: chunking reduced the multi-page candidate set [2, 4] to [2]; no single page may be forced",
        "pdf_page_index0": null,
        "stage": "chunking",
        "upstream_value": [
          2,
          4
        ]
      }
    ],
    "truth_pages": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "8e534a38b1b68025beddfecd7bd757e6145157ba251ef3ff8dc802a63c34d9a7",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": "2975051e81aa19f99b410168fff1128805d1642d18127099dd0912713ecccb70",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": null,
        "text_state": "IMAGE_ONLY"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "e1cba8416a4df5ea385360a3dc34b681f8488fde5e7473d4c09dc4cd934ead10",
        "text_state": "TEXT"
      }
    ],
    "variant": "reduce-to-first",
    "verdict": "FAIL_AMBIGUOUS"
  },
  {
    "candidate_source_pages0": [],
    "case_id": "un-ext-01",
    "chunks": [
      {
        "chunk_id": "c-fault",
        "source_page_indices0": [
          2
        ],
        "text_sha256": null
      },
      {
        "chunk_id": "c-control",
        "source_page_indices0": [
          4
        ],
        "text_sha256": "daa968f93c1e8ad6dd947de71388dcb6c393b1c1376ed0bcbb8970c0ca508aca"
      }
    ],
    "citation_id": "cite-fault",
    "citation_page_basis": "PDF_NUMBER_1",
    "correct_pdf_page_number1": null,
    "correct_viewer_page1": null,
    "display": {
      "citation_id": "cite-fault",
      "citation_page_basis": "PDF_NUMBER_1",
      "citation_page_value": 3,
      "viewer_page1": 3
    },
    "document": {
      "file_name": "un-ext-01.pdf",
      "page_count": 5,
      "sha256": "ae451bd6f4a4a616c57af583c91f7b6f04a92407dbcb375c6aef91bda2b0be07"
    },
    "expected_source_pages0": [
      2
    ],
    "extraction": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": "08295a7372c87b496dcf3a1a79499f081e28ae35a8b1f9eb8a65710a235d3b78",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "b908bb56e6a97529665b8183dd613b83b0f793c88b54617c2fec042e9f0f9c8c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": null,
        "text_state": "IMAGE_ONLY"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": "ed26ef8fed99f1819beb13b4e4735987258c67a2c3a9e7508caa31aa5daa822c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "5f97285c224c706e2db17aabd5519c0c5c4096bde9c095ec0ae5cfeb1271c679",
        "text_state": "TEXT"
      }
    ],
    "fault_type": "UNLOCATABLE",
    "first_fault_stage": "extraction",
    "index_records": [
      {
        "pdf_page_label": "3",
        "record_id": "v-fault",
        "source_page_indices0": [
          2
        ]
      },
      {
        "pdf_page_label": "5",
        "record_id": "v-control",
        "source_page_indices0": [
          4
        ]
      }
    ],
    "locate_fault_quote": {
      "candidate_source_pages0": [],
      "expected_candidate_source_pages0": [],
      "match": true,
      "span_status": "not_found"
    },
    "observed_page_value": 3,
    "quote_sha256": "b18b0cf5742e80748f980c63b58f38c23fb1d7cd8f8264cf6bbecedf81309764",
    "quote_text": "关键引文un-ext-01：页码漂移误导定位。",
    "stage_diffs": [
      {
        "downstream_value": [],
        "field": "candidate_source_pages0",
        "kind": "not_found",
        "note": "cite-fault: quote not found in the extractable text layer; the trace-claimed page(s) [2] are IMAGE_ONLY (scanned / raster pages, no text layer)",
        "pdf_page_index0": null,
        "stage": "extraction",
        "upstream_value": null
      }
    ],
    "truth_pages": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": "08295a7372c87b496dcf3a1a79499f081e28ae35a8b1f9eb8a65710a235d3b78",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "b908bb56e6a97529665b8183dd613b83b0f793c88b54617c2fec042e9f0f9c8c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": null,
        "text_state": "IMAGE_ONLY"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": "ed26ef8fed99f1819beb13b4e4735987258c67a2c3a9e7508caa31aa5daa822c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "5f97285c224c706e2db17aabd5519c0c5c4096bde9c095ec0ae5cfeb1271c679",
        "text_state": "TEXT"
      }
    ],
    "variant": "image-only-page",
    "verdict": "FAIL_UNLOCATABLE"
  },
  {
    "candidate_source_pages0": [
      4
    ],
    "case_id": "po-ext-01-control",
    "chunks": [
      {
        "chunk_id": "c-control",
        "source_page_indices0": [
          4
        ],
        "text_sha256": "47347e11b6283796e7a69eef2d4c2923e596659425e925154874c4d04be2512b"
      }
    ],
    "citation_id": "cite-control",
    "citation_page_basis": "PDF_NUMBER_1",
    "correct_pdf_page_number1": [
      5
    ],
    "correct_viewer_page1": [
      5
    ],
    "display": {
      "citation_id": "cite-control",
      "citation_page_basis": "PDF_NUMBER_1",
      "citation_page_value": 5,
      "viewer_page1": 5
    },
    "document": {
      "file_name": "po-ext-01.pdf",
      "page_count": 5,
      "sha256": "97d1f68a573e09c9b6fc519dde6d37ee25158ee4f6673488770e2debef7cb9cf"
    },
    "expected_source_pages0": [
      4
    ],
    "extraction": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "8e534a38b1b68025beddfecd7bd757e6145157ba251ef3ff8dc802a63c34d9a7",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": "9030819870f0541f2263033a61e15a5fb764788cc2bd2015740bc47d87818b5c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": "3aa9712445bbab6b7d69ca0368e349c42514e92959aa7c97e48dfa82b1bfc6e1",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "6c896df0e9848a00ce560aa27d919dcef24dd26ad7221884746d08d96c4c01b0",
        "text_state": "TEXT"
      }
    ],
    "fault_type": null,
    "first_fault_stage": null,
    "index_records": [
      {
        "pdf_page_label": "5",
        "record_id": "v-control",
        "source_page_indices0": [
          4
        ]
      }
    ],
    "locate_fault_quote": {
      "candidate_source_pages0": [
        4
      ],
      "cross_page_spans": [],
      "match": true,
      "span_status": "single_page",
      "split_pages0": [],
      "true_source_pages0": [
        4
      ]
    },
    "observed_page_value": 5,
    "quote_sha256": "47347e11b6283796e7a69eef2d4c2923e596659425e925154874c4d04be2512b",
    "quote_text": "对照引文po-ext-01：本页引用页码正确无误。",
    "stage_diffs": [],
    "truth_pages": [
      {
        "pdf_page_index0": 0,
        "pdf_page_label": "1",
        "text_sha256": null,
        "text_state": "EMPTY"
      },
      {
        "pdf_page_index0": 1,
        "pdf_page_label": "2",
        "text_sha256": "8e534a38b1b68025beddfecd7bd757e6145157ba251ef3ff8dc802a63c34d9a7",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 2,
        "pdf_page_label": "3",
        "text_sha256": "9030819870f0541f2263033a61e15a5fb764788cc2bd2015740bc47d87818b5c",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 3,
        "pdf_page_label": "4",
        "text_sha256": "3aa9712445bbab6b7d69ca0368e349c42514e92959aa7c97e48dfa82b1bfc6e1",
        "text_state": "TEXT"
      },
      {
        "pdf_page_index0": 4,
        "pdf_page_label": "5",
        "text_sha256": "6c896df0e9848a00ce560aa27d919dcef24dd26ad7221884746d08d96c4c01b0",
        "text_state": "TEXT"
      }
    ],
    "variant": "control",
    "verdict": "PASS"
  }
];
/* END GENERATED DATA */

/* Status mapping — PROJECT_BOOK §9.3. Verdict text is always shown next to
 * the colour, so status is never colour-only. AMBIGUOUS / UNLOCATABLE /
 * UNKNOWN are amber and must never render as PASS. */
const STATUS_META = {
  "PASS": { "cls": "status-pass", "label": "PASS", "tone": "pass" },
  "FAIL_PAGE_OFFSET": { "cls": "status-fail", "label": "FAIL — 页码偏移", "tone": "fail" },
  "FAIL_METADATA_MISSING": { "cls": "status-fail", "label": "FAIL — 元数据缺失", "tone": "fail" },
  "FAIL_AMBIGUOUS": { "cls": "status-amber", "label": "FAIL — 歧义未确认", "tone": "amber" },
  "FAIL_UNLOCATABLE": { "cls": "status-amber", "label": "FAIL — 无法定位", "tone": "amber" },
  "UNKNOWN": { "cls": "status-amber", "label": "UNKNOWN — 未确认", "tone": "amber" },
  "SKIPPED": { "cls": "status-skipped", "label": "SKIPPED — 已跳过", "tone": "skipped" }
};

const STAGE_LABELS = {
  "extraction": "抽取 extraction",
  "chunking": "分片 chunking",
  "indexing": "索引 indexing",
  "display": "展示 display"
};

const FAULT_LABELS = {
  "PAGE_OFFSET": "页码偏移 PAGE_OFFSET",
  "PAGE_METADATA_MISSING": "元数据缺失 PAGE_METADATA_MISSING",
  "DUPLICATE_TEXT_AMBIGUITY": "重复文本歧义 DUPLICATE_TEXT_AMBIGUITY",
  "UNLOCATABLE": "无法定位 UNLOCATABLE"
};

const TEXT_STATE_LABELS = {
  "TEXT": "TEXT 有文本层",
  "EMPTY": "EMPTY 空白页",
  "IMAGE_ONLY": "IMAGE_ONLY / NO_TEXT_LAYER 图像页无文本层",
  "ERROR": "ERROR 抽取异常"
};

let selectedCaseId = null;
let selectedPageIndex0 = null;

function $(id) { return document.getElementById(id); }

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function shortHash(value) {
  return value ? String(value).slice(0, 12) + "…" : "—";
}

function pageList1(indices0) {
  if (!indices0 || indices0.length === 0) return "—";
  return indices0.map(function (i) { return "p." + (i + 1); }).join("，");
}

function pageListNumber1(numbers1) {
  if (!numbers1 || numbers1.length === 0) return "—";
  return numbers1.map(function (n) { return "p." + n; }).join("，");
}

function statusMeta(verdict) {
  return STATUS_META[verdict] || STATUS_META["UNKNOWN"];
}

function statusBadge(verdict) {
  const meta = statusMeta(verdict);
  return '<span class="badge ' + meta.cls + '">' + esc(meta.label) + "</span>";
}

function entryById(caseId) {
  for (const entry of PROTOTYPE_CASES) {
    if (entry.case_id === caseId) return entry;
  }
  return PROTOTYPE_CASES[0];
}

function filteredCases() {
  const fault = $("filter-fault").value;
  const stage = $("filter-stage").value;
  const status = $("filter-status").value;
  return PROTOTYPE_CASES.filter(function (entry) {
    if (fault && String(entry.fault_type) !== fault) return false;
    if (stage && entry.first_fault_stage !== stage) return false;
    if (status) {
      const tone = statusMeta(entry.verdict).tone;
      if (tone !== status) return false;
    }
    return true;
  });
}

function renderCitationList() {
  const list = filteredCases();
  const box = $("citation-list");
  if (list.length === 0) {
    box.innerHTML = '<p class="empty-note">没有符合过滤条件的引用。</p>';
    return;
  }
  box.innerHTML = list.map(function (entry) {
    const meta = statusMeta(entry.verdict);
    const selected = entry.case_id === selectedCaseId;
    const fault = entry.fault_type ? esc(FAULT_LABELS[entry.fault_type]) : "对照 PASS";
    return '<button type="button" class="citation-item' + (selected ? " selected" : "") + '"' +
      ' data-case-id="' + esc(entry.case_id) + '"' +
      ' aria-pressed="' + (selected ? "true" : "false") + '">' +
      '<span class="citation-id">' + esc(entry.case_id) + " · " + esc(entry.citation_id) + "</span>" +
      '<span class="citation-fault">' + fault + "</span>" +
      '<span class="badge ' + meta.cls + '">' + esc(meta.label) + "</span>" +
      '<span class="citation-quote">' + esc(entry.quote_text) + "</span>" +
      "</button>";
  }).join("");
  box.querySelectorAll(".citation-item").forEach(function (button) {
    button.addEventListener("click", function () {
      selectCase(button.getAttribute("data-case-id"));
    });
  });
}

function rowClassesForPage(entry, index0, opts) {
  const classes = ["page-row"];
  if (opts.correct && entry.correct_pdf_page_number1 &&
      entry.correct_pdf_page_number1.indexOf(index0 + 1) !== -1) {
    classes.push("row-correct");
  }
  if (opts.candidate && entry.candidate_source_pages0 &&
      entry.candidate_source_pages0.indexOf(index0) !== -1) {
    classes.push("row-candidate");
  }
  if (selectedPageIndex0 === index0) classes.push("row-selected");
  return classes.join(" ");
}

function renderTruthColumn(entry) {
  const rows = entry.truth_pages.map(function (page) {
    const index0 = page.pdf_page_index0;
    const isCorrect = entry.correct_pdf_page_number1 &&
      entry.correct_pdf_page_number1.indexOf(index0 + 1) !== -1;
    const pdfLink = "../04_source/source/fixtures/pdfs/" + esc(entry.document.file_name) +
      "#page=" + (index0 + 1);
    return "<tr class=\"" + rowClassesForPage(entry, index0, { correct: true }) + "\" data-page-index=\"" + index0 + "\">" +
      "<td>p." + (index0 + 1) + " · 索引 " + index0 + " · label " + esc(page.pdf_page_label) + "</td>" +
      "<td>" + esc(TEXT_STATE_LABELS[page.text_state] || page.text_state) + "</td>" +
      "<td>" + (isCorrect ? '<span class="tag tag-correct">✓ 正确来源</span>' : "—") + "</td>" +
      "<td><a href=\"" + pdfLink + "\">#page=" + (index0 + 1) + "</a></td>" +
      "</tr>";
  }).join("");
  $("col-truth-body").innerHTML = rows;
  $("col-truth-note").textContent = "文件 " + entry.document.file_name +
    " · 共 " + entry.document.page_count + " 页 · SHA-256 " +
    String(entry.document.sha256).slice(0, 16) + "…";
}

function renderExtractionColumn(entry) {
  const diffPages = {};
  entry.stage_diffs.forEach(function (diff) {
    if (diff.stage === "extraction" && diff.pdf_page_index0 != null) {
      diffPages[diff.pdf_page_index0] = diff;
    }
  });
  const rows = entry.extraction.map(function (page) {
    const index0 = page.pdf_page_index0;
    const diff = diffPages[index0];
    const isCandidate = entry.candidate_source_pages0 &&
      entry.candidate_source_pages0.indexOf(index0) !== -1;
    return "<tr class=\"" + rowClassesForPage(entry, index0, { candidate: true }) + "\" data-page-index=\"" + index0 + "\">" +
      "<td>p." + (index0 + 1) + " · 索引 " + index0 + "</td>" +
      "<td>" + esc(TEXT_STATE_LABELS[page.text_state] || page.text_state) + "</td>" +
      "<td><code title=\"" + esc(page.text_sha256 || "") + "\">" + esc(shortHash(page.text_sha256)) + "</code></td>" +
      "<td>" + (isCandidate ? '<span class="tag tag-candidate">引用命中候选</span>' : "—") + "</td>" +
      "<td>" + (diff ? '<span class="tag tag-diff" title="字段 ' + esc(diff.field) + '">✕ 与真值不符</span>' : "—") + "</td>" +
      "</tr>";
  }).join("");
  $("col-extraction-body").innerHTML = rows;
  const located = entry.locate_fault_quote;
  $("col-extraction-note").textContent = "定位状态 " + esc(located.span_status) +
    " · 候选页(0-based) " + pageList1(entry.candidate_source_pages0) +
    " · 引用命中 " + (located.match ? "是" : "否");
}

function renderChunkIndexColumn(entry) {
  const chunkDiffs = {};
  const indexDiffs = {};
  entry.stage_diffs.forEach(function (diff) {
    if (diff.stage === "chunking") chunkDiffs[diff.field] = diff;
    if (diff.stage === "indexing") indexDiffs[diff.field] = diff;
  });
  const chunkRows = entry.chunks.map(function (chunk) {
    const reduced = chunk.chunk_id === entry.chunks[0].chunk_id &&
      entry.stage_diffs.some(function (d) {
        return d.stage === "chunking" && d.field === "source_page_indices0";
      });
    return "<tr class=\"" + (reduced ? "row-diff" : "") + "\">" +
      "<td><code>" + esc(chunk.chunk_id) + "</code></td>" +
      "<td>" + pageList1(chunk.source_page_indices0) + "（0-based）</td>" +
      "<td><code title=\"" + esc(chunk.text_sha256 || "") + "\">" + esc(shortHash(chunk.text_sha256)) + "</code></td>" +
      "<td>" + (reduced ? '<span class="tag tag-diff">✕ 候选页被缩减</span>' : "—") + "</td>" +
      "</tr>";
  }).join("");
  const indexRows = entry.index_records.map(function (rec) {
    return "<tr>" +
      "<td><code>" + esc(rec.record_id) + "</code></td>" +
      "<td>" + pageList1(rec.source_page_indices0) + "（0-based）</td>" +
      "<td>label " + esc(rec.pdf_page_label) + "</td>" +
      "</tr>";
  }).join("");
  $("col-chunk-body").innerHTML = chunkRows;
  $("col-index-body").innerHTML = indexRows;
  const chunkNote = chunkDiffs["source_page_indices0"]
    ? "分片差异：上游 " + pageList1(chunkDiffs["source_page_indices0"].upstream_value) +
      " → 下游 " + pageList1(chunkDiffs["source_page_indices0"].downstream_value)
    : "分片与上游一致";
  const indexNote = indexDiffs["source_page_indices0"]
    ? "索引差异：上游 " + pageList1(indexDiffs["source_page_indices0"].upstream_value) +
      " → 下游 " + pageList1(indexDiffs["source_page_indices0"].downstream_value)
    : "索引与分片一致";
  $("col-chunk-note").textContent = chunkNote + "；" + indexNote +
    "（分片与索引分别显示，不合并归因）";
}

function renderCitationColumn(entry) {
  const correct = entry.correct_pdf_page_number1;
  const correctText = correct
    ? "PDF 页号(1-based) " + pageListNumber1(correct) +
      " · 浏览器页(viewer) " + pageListNumber1(entry.correct_viewer_page1)
    : "无可确认的正确来源页 — 引文在 PDF 文本层中无法定位";
  $("col-citation-body").innerHTML =
    "<dl>" +
    "<dt>原始 page value（模型/应用输出）</dt><dd>" +
      (entry.observed_page_value == null ? "缺失（无 page value）" : "p." + esc(entry.observed_page_value)) + "</dd>" +
    "<dt>page basis</dt><dd>" + esc(entry.citation_page_basis) + "</dd>" +
    "<dt>最终 viewer page（展示层）</dt><dd>" +
      (entry.display.viewer_page1 == null ? "缺失" : "p." + esc(entry.display.viewer_page1)) + "</dd>" +
    "<dt>实际应打开的页（正确来源）</dt><dd>" + esc(correctText) + "</dd>" +
    "<dt>verdict</dt><dd>" + statusBadge(entry.verdict) + " <code>" + esc(entry.verdict) + "</code></dd>" +
    "<dt>故障类型</dt><dd>" + (entry.fault_type ? esc(entry.fault_type) : "无（对照）") + "</dd>" +
    "<dt>首错阶段</dt><dd>" + (entry.first_fault_stage ? esc(STAGE_LABELS[entry.first_fault_stage]) : "无") + "</dd>" +
    "<dt>quote SHA-256</dt><dd><code title=\"" + esc(entry.quote_sha256) + "\">" + esc(shortHash(entry.quote_sha256)) + "</code></dd>" +
    "</dl>";
}

function renderComparison(entry) {
  const wrongPage = entry.observed_page_value == null
    ? "缺失（无 page value）"
    : "p." + entry.observed_page_value + "（basis " + entry.citation_page_basis + "）";
  const correct = entry.correct_pdf_page_number1
    ? "PDF 页号(1-based) " + pageListNumber1(entry.correct_pdf_page_number1) +
      "（物理页索引 0-based " + pageList1(entry.correct_pdf_page_number1.map(function (n) { return n - 1; })) + "）"
    : "无可确认的正确来源页（UNLOCATABLE — 引文未在文本层找到）";
  const correctCellClass = entry.correct_pdf_page_number1 ? "cell-correct" : "cell-unknown";
  $("comparison-body").innerHTML =
    "<tr>" +
    "<td class=\"cell-wrong\">" + esc(wrongPage) + "</td>" +
    "<td>" + (entry.first_fault_stage ? esc(STAGE_LABELS[entry.first_fault_stage]) : "无（对照 PASS）") + "</td>" +
    "<td class=\"" + correctCellClass + "\">" + esc(correct) + "</td>" +
    "<td>" + statusBadge(entry.verdict) + "</td>" +
    "</tr>";
}

function renderDiffs(entry) {
  const box = $("stage-diff-list");
  if (entry.stage_diffs.length === 0) {
    box.innerHTML = '<p class="empty-note">本条引用在四个阶段均无差异（对照 PASS）。</p>';
    return;
  }
  box.innerHTML = "<ol>" + entry.stage_diffs.map(function (diff) {
    return "<li><strong>" + esc(STAGE_LABELS[diff.stage] || diff.stage) + "</strong> · 字段 <code>" +
      esc(diff.field) + "</code> · " + esc(diff.kind) + "<br>" + esc(diff.note) + "</li>";
  }).join("") + "</ol>";
}

function renderRawJson(entry) {
  $("raw-json").textContent = JSON.stringify(entry, null, 2);
}

function renderAll() {
  const entry = entryById(selectedCaseId);
  selectedCaseId = entry.case_id;
  renderCitationList();
  renderTruthColumn(entry);
  renderExtractionColumn(entry);
  renderChunkIndexColumn(entry);
  renderCitationColumn(entry);
  renderComparison(entry);
  renderDiffs(entry);
  renderRawJson(entry);
  $("selected-summary").textContent = "当前选中：" + entry.case_id + " · " +
    entry.citation_id + " · " + entry.verdict;
  document.querySelectorAll(".page-row").forEach(function (row) {
    row.addEventListener("click", function () {
      const index0 = Number(row.getAttribute("data-page-index"));
      selectedPageIndex0 = selectedPageIndex0 === index0 ? null : index0;
      renderAll();
    });
  });
}

function selectCase(caseId) {
  selectedCaseId = caseId;
  selectedPageIndex0 = null;
  if (window.history && window.history.replaceState) {
    window.history.replaceState(null, "", "#case=" + encodeURIComponent(caseId));
  }
  renderAll();
}

function downloadReport() {
  const entry = entryById(selectedCaseId);
  const blob = new Blob([JSON.stringify(entry, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = entry.case_id + "-report.json";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function init() {
  const hash = window.location.hash || "";
  const match = hash.match(/case=([^&]+)/);
  const requested = match ? decodeURIComponent(match[1]) : null;
  selectedCaseId = requested && entryById(requested) ? requested : PROTOTYPE_CASES[0].case_id;
  ["filter-fault", "filter-stage", "filter-status"].forEach(function (id) {
    $(id).addEventListener("change", function () {
      const visible = filteredCases();
      if (visible.length > 0 && visible.every(function (e) { return e.case_id !== selectedCaseId; })) {
        selectedCaseId = visible[0].case_id;
      }
      renderAll();
    });
  });
  $("download-json").addEventListener("click", downloadReport);
  $("copy-json").addEventListener("click", function () {
    const entry = entryById(selectedCaseId);
    const text = JSON.stringify(entry, null, 2);
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
  renderAll();
}

document.addEventListener("DOMContentLoaded", init);
