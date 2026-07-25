import json
from pathlib import Path

from extract_JSON_2_TXT import process_json_to_txt


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
