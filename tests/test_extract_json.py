import json
from pathlib import Path

import jsonschema
import pytest

import document_hook
from atrium_document import DocumentRecord, load_document
from extract_JSON_2_TXT import _parse_args, extract_single_page, process_json_to_txt

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "atrium_document.schema.json"


def test_extract_json_to_txt(tmp_path: Path):
    # Setup mock JSON
    mock_json = {
        "metadata": {"engine": "TestEngine"},
        "page": {
            "lines": [
                {"textline": "Hello World", "bbox": [0, 0, 10, 10]},
                {"textline": "This is a test.", "bbox": [10, 10, 20, 20]},
            ]
        },
    }

    input_file = tmp_path / "test.json"
    output_file = tmp_path / "test.txt"

    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(mock_json, f)

    # Run processor
    process_json_to_txt(input_file, output_file)

    # Assert
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Hello World" in content
    assert "This is a test." in content
    assert "TestEngine" not in content  # Metadata should be ignored


def test_extract_single_page_writes_alto_compatible_output_path(tmp_path: Path):
    """The CSV-driven worker follows the {file}/{file}-{page}.txt convention
    shared with the ALTO extractors, so classify_TEXT.py needs no changes."""
    mock_json = {"text": "Only line"}
    input_file = tmp_path / "doc7.json"
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(mock_json, f)

    output_dir = tmp_path / "out"
    ok = extract_single_page(("doc7", 1, str(input_file), str(output_dir)))

    assert ok is True
    txt_path = output_dir / "doc7" / "doc7-1.txt"
    assert txt_path.exists()
    assert txt_path.read_text(encoding="utf-8") == "Only line"


def test_extract_single_page_resumes_existing_output(tmp_path: Path):
    """A pre-existing .txt is left untouched (resume support)."""
    output_dir = tmp_path / "out"
    save_dir = output_dir / "doc9"
    save_dir.mkdir(parents=True)
    txt_path = save_dir / "doc9-1.txt"
    txt_path.write_text("already extracted", encoding="utf-8")

    # Point at a nonexistent JSON input — if the worker tried to re-extract
    # it would fail; success here proves the resume short-circuit fired.
    ok = extract_single_page(("doc9", 1, str(tmp_path / "missing.json"), str(output_dir)))

    assert ok is True
    assert txt_path.read_text(encoding="utf-8") == "already extracted"


def test_extract_single_page_reports_failure_on_bad_json(tmp_path: Path):
    input_file = tmp_path / "broken.json"
    input_file.write_text("{not valid", encoding="utf-8")

    ok = extract_single_page(("broken", 1, str(input_file), str(tmp_path / "out")))

    assert ok is False


# ── CLI surface (issue #37 D4: --force-single-page) ──────────────────────────


def test_parse_args_force_single_page_defaults_to_none_when_absent():
    """Absent means 'use the config default', not 'false' — main() must be able
    to distinguish the two so [EXTRACT].FORCE_SINGLE_PAGE_JSON keeps working for
    orchestrated run_pipeline.py invocations that pass no extra CLI flags."""
    args = _parse_args([])
    assert args.force_single_page is None


def test_parse_args_force_single_page_flag_sets_true():
    args = _parse_args(["--force-single-page"])
    assert args.force_single_page is True


def test_parse_args_rejects_unknown_flag():
    with pytest.raises(SystemExit):
        _parse_args(["--not-a-real-flag"])


# ── Accretion contract (issue #37): ownership boundaries + preservation ──────


def test_accretion_preserves_unrelated_metadata_and_co_owned_fields(tmp_path: Path):
    """The json-keys extractor's accretion contribution must only ever touch its
    own `content` block and its own fields inside the field-split `pages` block —
    every other block, and every other tool's fields on a shared `pages` row,
    must come out exactly as they went in (issue #37 D2/D3)."""
    doc_dir = tmp_path / "doc"
    doc_dir.mkdir()

    # A baseline doc.json as it would exist after earlier pipeline stages have
    # already run: page-classification's block, nlp-enrich's entities, and the
    # first-writer-wins `source` block.
    with DocumentRecord("CTX99", "page-classification", out_dir=str(doc_dir)) as doc:
        doc.set_source(sha256="a" * 64, filename="CTX99.json", origin="ocr:generic")
        doc.merge_block("pages", [{"page": "1", "category": "Text", "category_confidence": 0.91}])
        doc.set_block("page_categories", {"1": "Text"})
    with DocumentRecord.open(
        "CTX99", "nlp-enrich", baseline=str(doc_dir / "CTX99.document.json"), out_dir=str(doc_dir)
    ) as doc:
        doc.set_block("entities", [{"surface": "Praha", "type_teitok": "LOC"}])

    baseline_path = doc_dir / "CTX99.document.json"
    baseline_before = load_document(str(baseline_path))

    # Now the json-keys extraction contributes its own share, as main() does.
    txt_dir = tmp_path / "txt"
    txt_dir.mkdir()
    (txt_dir / "CTX99").mkdir()
    (txt_dir / "CTX99" / "CTX99-1.txt").write_text("Extracted page text", encoding="utf-8")

    pages, content = document_hook.pages_and_content_from_text(str(txt_dir), "CTX99", [1], engine="json-keys")
    document_hook.write_document_block(
        str(doc_dir),
        "CTX99",
        run_id="r3",
        paradata_ref="paradata/r3_alto-postprocess.json",
        merge_blocks={"pages": pages},
        set_blocks={"content": content},
    )

    after = load_document(str(baseline_path))

    # Untouched blocks: byte-for-byte (semantically) identical to before this run.
    assert after["source"] == baseline_before["source"]
    assert after["page_categories"] == baseline_before["page_categories"]
    assert after["entities"] == baseline_before["entities"]

    # Co-owned `pages` row: page-classification's fields survive, alto-postprocess's
    # own field is added on the SAME row — neither overwrites the other.
    assert len(after["pages"]) == 1
    row = after["pages"][0]
    assert row["category"] == "Text"
    assert row["category_confidence"] == 0.91
    assert row["ocr"] == {"engine": "json-keys"}

    # This run's own block, freshly written.
    assert after["content"] == {"text": "Extracted page text"}


# ── Schema conformance (issue #37 D5) ─────────────────────────────────────────


@pytest.fixture(scope="module")
def document_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("force_single_page", [False, True])
def test_json_keys_accretion_output_is_schema_valid(tmp_path, document_schema, force_single_page):
    txt_dir = tmp_path / "txt"
    (txt_dir / "CTXschema").mkdir(parents=True)
    (txt_dir / "CTXschema" / "CTXschema-1.txt").write_text("Line one", encoding="utf-8")
    (txt_dir / "CTXschema" / "CTXschema-2.txt").write_text("Line two", encoding="utf-8")

    doc_dir = tmp_path / "doc"
    pages, content = document_hook.pages_and_content_from_text(
        str(txt_dir), "CTXschema", [1, 2], engine="json-keys", force_single_page=force_single_page
    )
    document_hook.write_document_block(
        str(doc_dir),
        "CTXschema",
        run_id="r1",
        paradata_ref="paradata/r1_alto-postprocess.json",
        merge_blocks={"pages": pages},
        set_blocks={"content": content},
    )

    record = load_document(str(doc_dir / "CTXschema.document.json"))
    jsonschema.validate(instance=record, schema=document_schema)
