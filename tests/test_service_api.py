from unittest.mock import patch

from fastapi.testclient import TestClient

from service.text_api import app

client = TestClient(app)


def test_info_endpoint():
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "quality_categories" in data
    assert "Clear" in data["quality_categories"]


def test_info_version_matches_para_config():
    """The API version must come from para_config.txt [tool], never hardcoded."""
    import configparser
    from pathlib import Path

    config = configparser.ConfigParser()
    config.read(Path(__file__).resolve().parent.parent / "setup" / "para_config.txt", encoding="utf-8")
    expected = config.get("tool", "version").lstrip("v")

    response = client.get("/info")
    assert response.status_code == 200
    assert response.json()["version"] == expected
    assert app.version == expected


@patch("service.text_api.text_manager.process_text_file", create=True)
def test_process_text_auto_routing(mock_process):
    """Ensure text uploads correctly route to the text_manager text processor."""
    mock_process.return_value = {
        "type": "plain_text",
        "cleaned_lines": [{"line_num": 1, "text": "Mocked Line", "category": "Clear"}],
    }

    content = b"Mock line content"
    files = {"file": ("document.txt", content, "text/plain")}
    data = {"task_type": "auto"}

    response = client.post("/process", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["type"] == "plain_text"
    assert res_data["cleaned_lines"][0]["category"] == "Clear"
    assert res_data["filename"] == "document.txt"


@patch("service.text_api.text_manager.process_alto", create=True)
def test_process_alto_explicit_routing(mock_process):
    """Ensure ALTO XML uploads hit the alto pipeline specifically."""
    mock_process.return_value = {"type": "alto_xml", "cleaned_lines": []}

    content = b"<alto></alto>"
    files = {"file": ("document.xml", content, "application/xml")}
    data = {"task_type": "alto"}

    response = client.post("/process", files=files, data=data)
    assert response.status_code == 200
    assert response.json()["type"] == "alto_xml"


@patch("service.text_api.text_manager.process_json", create=True)
def test_process_json_auto_routing(mock_process):
    """Ensure .json uploads auto-detect to task_type='json' and route to process_json."""
    mock_process.return_value = {
        "type": "json",
        "cleaned_lines": [{"line_num": 1, "text": "Mocked JSON Line", "category": "Clear"}],
    }

    content = b'{"text": "Mocked JSON Line"}'
    files = {"file": ("document.json", content, "application/json")}
    data = {"task_type": "auto"}

    response = client.post("/process", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["type"] == "json"
    assert res_data["cleaned_lines"][0]["category"] == "Clear"
    assert res_data["filename"] == "document.json"


@patch("service.text_api.text_manager.process_json", create=True)
def test_process_json_explicit_routing(mock_process):
    """Ensure task_type='json' routes to process_json regardless of filename."""
    mock_process.return_value = {"type": "json", "cleaned_lines": []}

    content = b'{"text": "irrelevant"}'
    files = {"file": ("upload.dat", content, "application/octet-stream")}
    data = {"task_type": "json"}

    response = client.post("/process", files=files, data=data)
    assert response.status_code == 200
    assert response.json()["type"] == "json"


def test_info_lists_json_as_supported_format():
    response = client.get("/info")
    assert response.status_code == 200
    assert any("JSON" in fmt for fmt in response.json()["supported_formats"])


def test_process_unrecognized_extension_still_rejected():
    """Auto-detect must still 400 on formats outside alto/text/json (#8)."""
    files = {"file": ("document.pdf", b"%PDF-1.4", "application/pdf")}
    data = {"task_type": "auto"}

    response = client.post("/process", files=files, data=data)
    assert response.status_code == 400
