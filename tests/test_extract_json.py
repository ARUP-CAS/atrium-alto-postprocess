import json
from pathlib import Path

from extract_JSON_2_TXT import extract_single_page, process_json_to_txt


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
