"""
tests/test_document_hook.py — tests for the LIVE document_hook.py surface
(write_document_block / resolve_document_json_dir / paradata_ref_for), which
every stage script (page_split, aggregate_STAT, classify_TEXT, the four
extract_*) actually calls.

Previously this file tested `write_document_record()`/`update_document_record()`
— two functions that bypassed DocumentRecord entirely, wrote keys from the
superseded aggregator draft (`assembled.source_run_ids`, `assembled.mode`), and
were never called from anywhere except these tests. They have been deleted
(issue #13 alignment audit, P2.1) since the real, wired-up path below already
does the job correctly. `test_no_baseline_creates_standalone`'s mocked logger
also assigned `logger.run_id = ...`, which no longer works now that `run_id` is
a read-only property on the real ParadataLogger.
"""

import os

from atrium_document import load_document
from document_hook import (
    document_path,
    paradata_ref_for,
    resolve_document_json_dir,
    write_document_block,
)


class _FakeLogger:
    def __init__(self, run_id, program, paradata_dir="paradata"):
        self.run_id = run_id
        self.program = program
        self.paradata_dir = paradata_dir


def test_resolve_document_json_dir_env_wins(monkeypatch):
    monkeypatch.setenv("DOCUMENT_JSON_DIR", "/from/env")
    assert resolve_document_json_dir("/from/config") == "/from/env"


def test_resolve_document_json_dir_falls_back_to_config(monkeypatch):
    monkeypatch.delenv("DOCUMENT_JSON_DIR", raising=False)
    assert resolve_document_json_dir("/from/config") == "/from/config"


def test_resolve_document_json_dir_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DOCUMENT_JSON_DIR", raising=False)
    assert resolve_document_json_dir(None) == ""
    assert resolve_document_json_dir("") == ""


def test_paradata_ref_for():
    logger = _FakeLogger(run_id="260731-101112", program="alto-postprocess", paradata_dir="paradata")
    assert paradata_ref_for(logger) == os.path.join("paradata", "260731-101112_alto-postprocess.json")


def test_write_document_block_noop_when_dir_falsy(monkeypatch, tmp_path):
    # Rule 3 / enablement: a falsy document_json_dir must return immediately,
    # before any filesystem access — verified by running from an empty cwd.
    monkeypatch.chdir(tmp_path)
    result = write_document_block("", "CTX01", run_id="r1", set_blocks={"content": {"text": "hi"}})
    assert result is None
    assert list(tmp_path.iterdir()) == []


def test_write_document_block_merges_without_erasing_co_owned_fields(tmp_path):
    doc_dir = str(tmp_path)

    # page-classification writes first: category + category_confidence on page 1.
    from atrium_document import DocumentRecord

    with DocumentRecord("CTX01", "page-classification", out_dir=doc_dir) as doc:
        doc.merge_block("pages", [{"page": "1", "category": "Text", "category_confidence": 0.97}])

    # alto-postprocess contributes via the live hook — quality fields on the SAME page row.
    write_document_block(
        doc_dir,
        "CTX01",
        run_id="r2",
        paradata_ref="paradata/r2_alto-postprocess.json",
        merge_blocks={"pages": [{"page": "1", "quality_score": 0.98, "quality_band": "Clear"}]},
    )

    record = load_document(document_path(doc_dir, "CTX01"))
    assert len(record["pages"]) == 1
    page = record["pages"][0]
    # Both contributions must survive on the same row.
    assert page["category"] == "Text"
    assert page["category_confidence"] == 0.97
    assert page["quality_score"] == 0.98
    assert page["quality_band"] == "Clear"


def test_write_document_block_set_blocks_uses_set_block(tmp_path):
    doc_dir = str(tmp_path)
    write_document_block(
        doc_dir,
        "CTX02",
        run_id="r1",
        set_blocks={"content": {"text": "full document text"}},
    )
    record = load_document(document_path(doc_dir, "CTX02"))
    assert record["content"] == {"text": "full document text"}
    assert record["assembled"]["blocks"]["content"]["program"] == "alto-postprocess"


def test_write_document_block_records_source_once(tmp_path):
    doc_dir = str(tmp_path)
    write_document_block(
        doc_dir,
        "CTX03",
        run_id="r1",
        source={"sha256": "a" * 64, "filename": "CTX03.alto.xml", "origin": "ABBYY-ALTO"},
    )
    # A later write must not overwrite an existing source (set_source is first-writer-wins).
    write_document_block(
        doc_dir,
        "CTX03",
        run_id="r2",
        source={"sha256": "b" * 64, "filename": "other.xml", "origin": "digital-born-pdf"},
    )
    record = load_document(document_path(doc_dir, "CTX03"))
    assert record["source"]["sha256"] == "a" * 64
