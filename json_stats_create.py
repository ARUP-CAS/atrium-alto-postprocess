#!/usr/bin/env python3
"""
json_stats_create.py

Purpose:
This script scans a given input folder for JSON OCR-output files. It can scan
both the root of the folder and one level of subdirectories, mirroring
alto_stats_create.py's walk.

(#31) As of page_split.py's split_json_document(), a generic JSON document is
split into pages up front just like ALTO, so this script's input is
post-split, per-page JSON (`<file>-<page>.json`) — no different in shape from
what alto_stats_create.py already scans. Unlike ALTO XML, a generic JSON OCR
export has no external element-counting tool (there is no "alto-tools -s"
equivalent), so this produces one CSV row per JSON file: file/page derived
from the split filename (mirrors alto_stats_create._process_single_xml's
`basename.split(".")[0].split("-")`), textlines/illustrations/graphics=0 (no
structural equivalent exists for JSON), and strings=the number of text leaves
extract_JSON_2_TXT.py would pull out of that file (reusing its TARGET_KEYS
whitelist walk, so the count matches what will actually be extracted).

This CSV has the same columns as the ALTO stats CSV (file, page, textlines,
illustrations, graphics, strings, path), so it's a drop-in input for the same
downstream stages (extract_JSON_2_TXT.py, classify_TEXT.py, aggregate_STAT.py)
without any changes to those scripts.

Usage:
    python json_stats_create.py <input_folder> [-o <output_csv>]
"""

import argparse
import json
import os

import pandas as pd

from atrium_paradata import ParadataLogger
from extract_JSON_2_TXT import TARGET_KEYS, _yield_json_text_by_keys


def _process_single_json(json_path, fname):
    """
    Process one JSON file: parse it and build the result record.

    Returns:
        (dict, None)  on success — the record dict and no skip reason.
        (None, str)   on failure — no record and a human-readable skip reason.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return None, f"could not parse JSON: {e}"

    n_strings = sum(1 for _ in _yield_json_text_by_keys(data, TARGET_KEYS))

    # --- (D7) Derive file ID and page ID from the split filename ---
    # e.g. "doc123-1.json" -> file="doc123", page="1" — same convention as
    # alto_stats_create._process_single_xml, since page_split.py now names
    # split JSON pages identically to split ALTO pages.
    base = os.path.basename(fname).split(".")[0]  # "doc123-1"
    parts = base.split("-")  # ["doc123", "1"]
    file_id = parts[0]  # "doc123"
    page = parts[1] if len(parts) > 1 else ""  # "1"

    rec = {
        "file": file_id,
        "page": page,
        "textlines": 0,
        "illustrations": 0,
        "graphics": 0,
        "strings": n_strings,
        "path": json_path,
    }
    return rec, None


def process_json_files(directory_path):
    """
    Processes all JSON files found directly within a given directory.

    Args:
        directory_path (str): The folder to scan for .json files.

    Returns:
        tuple[list[dict], int, list[tuple[str, str]]]:
            - list of per-file result dicts
            - total number of JSON files found
            - list of (json_path, reason) pairs that failed (skipped)
    """
    json_files = [
        (os.path.join(directory_path, fname), fname)
        for fname in os.listdir(directory_path)
        if fname.lower().endswith(".json")
    ]

    _total_inputs = len(json_files)
    results = []
    _skips = []

    for json_path, fname in json_files:
        rec, reason = _process_single_json(json_path, fname)
        if reason is not None:
            _skips.append((json_path, reason))
        else:
            results.append(rec)

    return results, _total_inputs, _skips


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder", help="Folder containing JSON OCR files or subfolders with them")
    parser.add_argument("-o", "--output", default="json_stats.csv", help="Output CSV file path")
    args = parser.parse_args(argv)

    if os.path.exists(args.output):
        os.remove(args.output)

    subdirs = [
        os.path.join(args.input_folder, d)
        for d in os.listdir(args.input_folder)
        if os.path.isdir(os.path.join(args.input_folder, d))
    ]

    first = True

    _logger = ParadataLogger(
        program="alto-postprocess",
        config={
            "script": "json_stats_create",
            "input_dir": str(args.input_folder),
            "output_csv": str(args.output),
        },
        paradata_dir="paradata",
        output_types=["csv"],
        config_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup"),
    )
    _total_inputs = 0

    try:
        for scan_dir in [*subdirs, args.input_folder]:
            stats, doc_inputs, doc_skips = process_json_files(scan_dir)
            _total_inputs += doc_inputs
            _logger.log_success("csv", count=len(stats))
            for sk_path, reason in doc_skips:
                _logger.log_skip(sk_path, reason)

            if stats:
                df = pd.DataFrame(stats)
                if first:
                    df.to_csv(args.output, index=False, header=True)
                    first = False
                else:
                    df.to_csv(args.output, index=False, header=False, mode="a")
                print(f"Processed {len(stats)} files from {scan_dir}")

        print("Done.")
    finally:
        _logger.finalize(input_total=_total_inputs)


if __name__ == "__main__":
    main()
