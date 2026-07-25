#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Generator, Set

# Whitelist of informative text keys
TARGET_KEYS: Set[str] = {
    "content",
    "text",
    "string",
    "textline",
    "line",
    "word",
    "lines",
    "words",
    "strings",
    "textlines",
    "textstring",
    "textstrings",
    "contents",
    "data",
    "texts",
    "pagetext",
    "page_text",
    "text_string",
    "text_line",
    "text_strings",
    "page_texts",
    "text_lines",
}


def _yield_json_text_by_keys(data: Any, target_keys: Set[str], current_key: str = None) -> Generator[str, None, None]:
    """Recursively yields text from string leaves if their parent key is in the target_keys."""
    if isinstance(data, dict):
        for k, v in data.items():
            yield from _yield_json_text_by_keys(v, target_keys, current_key=k)
    elif isinstance(data, list):
        for item in data:
            yield from _yield_json_text_by_keys(item, target_keys, current_key=current_key)
    elif isinstance(data, str):
        text = data.strip()
        if text and current_key and current_key.lower() in target_keys:
            yield text


def process_json_to_txt(input_file: Path, output_file: Path, join_char: str = "\n") -> None:
    """Reads a JSON file and writes its ordered plain text to the output file."""
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    extracted_leaves = list(_yield_json_text_by_keys(data, TARGET_KEYS))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(join_char.join(extracted_leaves))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract ordered plain text from JSON OCR output.")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Path to the input JSON file.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Path to the output TXT file.")
    parser.add_argument("--join-char", type=str, default="\n", help="Character used to join extracted text nodes.")

    args = parser.parse_args()

    try:
        process_json_to_txt(args.input, args.output, args.join_char)
        print(f"Successfully extracted text to {args.output}")
    except Exception as e:
        print(f"Error processing {args.input}: {e}", file=sys.stderr)
        sys.exit(1)
