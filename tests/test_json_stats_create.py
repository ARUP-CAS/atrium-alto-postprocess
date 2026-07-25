import json

import pytest

from json_stats_create import _process_single_json, main, process_json_files


def test_json_stats_cli_help(capsys):
    with pytest.raises(SystemExit) as e:  # argparse exits 0 on --help
        main(["--help"])
    assert e.value.code == 0
    assert "input_folder" in capsys.readouterr().out


def test_json_stats_missing_args(capsys):
    with pytest.raises(SystemExit) as e:  # missing required positional → exit 2
        main([])
    assert e.value.code == 2
    assert "required" in capsys.readouterr().err.lower()


def test_process_single_json_valid_file(tmp_path):
    mock_json = {"page": {"lines": [{"textline": "Hello World"}, {"textline": "Second line"}]}}
    json_path = tmp_path / "doc1.json"
    json_path.write_text(json.dumps(mock_json), encoding="utf-8")

    rec, reason = _process_single_json(str(json_path), "doc1.json")

    assert reason is None
    assert rec["file"] == "doc1"
    assert rec["page"] == 1
    assert rec["textlines"] == 0
    assert rec["illustrations"] == 0
    assert rec["graphics"] == 0
    assert rec["strings"] == 2
    assert rec["path"] == str(json_path)


def test_process_single_json_malformed_file_is_skipped(tmp_path):
    json_path = tmp_path / "broken.json"
    json_path.write_text("{not valid json", encoding="utf-8")

    rec, reason = _process_single_json(str(json_path), "broken.json")

    assert rec is None
    assert reason is not None


def test_process_json_files_walks_directory(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"text": "A"}), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"text": "B"}), encoding="utf-8")
    (tmp_path / "not_json.txt").write_text("ignored", encoding="utf-8")

    results, total, skips = process_json_files(str(tmp_path))

    assert total == 2
    assert skips == []
    assert {r["file"] for r in results} == {"a", "b"}
    assert all(r["page"] == 1 for r in results)


def test_process_json_files_reports_skips(tmp_path):
    (tmp_path / "good.json").write_text(json.dumps({"text": "OK"}), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{broken", encoding="utf-8")

    results, total, skips = process_json_files(str(tmp_path))

    assert total == 2
    assert len(results) == 1
    assert len(skips) == 1
    assert skips[0][0].endswith("bad.json")


def test_main_writes_csv_with_alto_compatible_columns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc1.json").write_text(
        json.dumps({"lines": [{"text": "One"}, {"text": "Two"}, {"text": "Three"}]}), encoding="utf-8"
    )
    out_csv = tmp_path / "out.csv"

    main([str(tmp_path), "-o", str(out_csv)])

    content = out_csv.read_text(encoding="utf-8")
    header = content.splitlines()[0]
    for col in ["file", "page", "textlines", "illustrations", "graphics", "strings", "path"]:
        assert col in header
    assert "doc1,1,0,0,0,3" in content
