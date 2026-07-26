#!/usr/bin/env python3
"""
page_split.py

Purpose:
This script takes a multi-page document as input and splits it into multiple
single-page files, ordered plain-text-adjacent stage 1 of the pipeline for
BOTH input formats it supports:

- ALTO XML: a document-level `<file>.alto.xml` (multiple `<Page>` elements
  under one `<Layout>`) is split into one `<base>-<page>.alto.xml` per page
  (``split_alto_xml``). Each output file keeps the full header and style
  information from the original file, but the <Layout> section only contains
  the data for a single page.
- Generic JSON OCR/Doc-AI output (#31): a document-level JSON file is split
  into one `<base>-<page>.json` per page (``split_json_document``), detecting
  the page boundary heuristically since OCR/Doc-AI engines don't agree on how
  multi-page documents are represented (see that function's docstring).

Usage:
    python page_split.py <input_directory> <output_directory>
"""

import argparse
import configparser
import hashlib
import json
import os
import xml.etree.ElementTree as ET  # For parsing and creating XML

import document_hook
from atrium_paradata import ParadataLogger

DOCUMENT_CONFIG_PATH = os.getenv("LANGID_CONFIG", os.path.join("setup", "config.txt"))


def _doc_id_from_filename(filename: str, fmt: str) -> str:
    """Mirror split_alto_xml's/split_json_document's own base_name derivation,
    without depending on their internals — used only to key the document record.
    """
    stem = os.path.splitext(filename)[0]
    return stem.replace(".alto", "") if fmt == "xml" else stem


def _sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _assert_no_doctype(input_file_path):
    """Reject any input containing a DOCTYPE declaration.

    (#5) ALTO documents may be untrusted, and legitimate ALTO never carries a
    DOCTYPE. The previous approach attached expat handlers via
    ``ET.XMLParser().parser`` — but the C-accelerated XMLParser exposes no such
    attribute (verified on CPython 3.12), so the ``except AttributeError``
    fallback silently disabled the hardening and internal entities were still
    expanded into the output. Scanning for a DOCTYPE before parsing fails
    closed: no entity declarations can exist without one, which rules out
    entity-expansion ("billion laughs") inputs entirely.
    """
    content = open(input_file_path, "rb").read()
    if b"<!doctype" in content.lower():
        raise ET.ParseError(f"DOCTYPE is not allowed in ALTO inputs: {input_file_path}")


def split_alto_xml(input_file_path, output_dir):
    """
    Splits a single multi-page ALTO XML file into single-page files.

    Returns:
        int: The number of pages written (0 if no pages were found).
    """
    namespace = {"alto": "http://www.loc.gov/standards/alto/ns-v3#"}
    ET.register_namespace("", "http://www.loc.gov/standards/alto/ns-v3#")

    # --- Parse the Input XML (DOCTYPE rejected up front, see #5) ---
    _assert_no_doctype(input_file_path)
    tree = ET.parse(input_file_path)
    root = tree.getroot()

    description = root.find("alto:Description", namespace)
    styles = root.find("alto:Styles", namespace)

    pages = root.findall(".//alto:Page", namespace)

    if not pages:
        print(f"  -> No <Page> elements found in {input_file_path}. Skipping.")
        return 0

    base_name = os.path.splitext(os.path.basename(input_file_path))[0].replace(".alto", "")

    page_output_dir = os.path.join(output_dir, base_name)
    os.makedirs(page_output_dir, exist_ok=True)

    print(f"  -> Found {len(pages)} page(s). Splitting...")
    for i, page in enumerate(pages, 1):
        page_number = page.get("PHYSICAL_IMG_NR", str(i))
        output_filename = f"{base_name}-{page_number}.alto.xml"
        output_filepath = os.path.join(page_output_dir, output_filename)

        new_root = ET.Element(root.tag, root.attrib)
        if description is not None:
            new_root.append(description)
        if styles is not None:
            new_root.append(styles)

        new_layout = ET.SubElement(new_root, "Layout")
        new_layout.append(page)

        new_tree = ET.ElementTree(new_root)
        new_tree.write(output_filepath, encoding="UTF-8", xml_declaration=True)

    print(f"  -> Successfully split into {len(pages)} file(s) in '{page_output_dir}'.")
    return len(pages)


# ── (#31) Generic JSON page splitting ───────────────────────────────────────
#
# Real OCR/Doc-AI engines fall into two structural families for representing
# multi-page documents (no vendor-specific parsers — see 31.plan.md):
#
#   Family A — a nested "pages" array (Azure Document Intelligence, docTR,
#   Google Document AI, most PDF-text-layer dumps): one JSON per document, a
#   top-level (or one-level-nested) key holds an ordered list of page dicts.
#
#   Family B — a flat element list tagged with a per-item page field (AWS
#   Textract): no nesting, a single flat list where every item carries a
#   field pointing back to its page.
#
#   Family C — already one file per page (pero-ocr, OCR.space, and today's
#   pipeline default). Used as the fallback when neither A nor B fires, so
#   existing single-page JSON behaviour is fully preserved.

# Family A: top-level (or one-level-nested) key whose value is a non-empty list of dicts.
PAGE_LIST_KEYS = {"pages", "page_results", "parsedresults", "page_list", "document_pages", "documentpages"}

# Field checked inside each candidate page-dict / flat-list element (Family A page numbering,
# and Family B grouping key).
PAGE_NUMBER_FIELD_KEYS = {
    "pagenumber",
    "page_number",
    "page_num",
    "page",
    "pageid",
    "page_id",
    "pageno",
    "page_no",
    "physical_img_nr",
}


def _is_dict_list(value):
    """True if value is a non-empty list where every item is a dict."""
    return isinstance(value, list) and len(value) > 0 and all(isinstance(item, dict) for item in value)


def _get_field_ci(d, keys):
    """Case-insensitive lookup of the first key in `d` matching one of `keys`
    (already-lowercase). Returns the value, or None if no key matches."""
    for k, v in d.items():
        if isinstance(k, str) and k.lower() in keys:
            return v
    return None


def _find_family_a(data):
    """(D5) Depth <= 2 scan: top-level, or nested one level under a
    dict-valued top-level key. Returns (container_parent, key, page_list) for
    the first PAGE_LIST_KEYS match whose value is a non-empty list of dicts,
    by depth-then-declaration-order (top-level before nested, first-seen key
    order) — or None if nothing matches.
    """
    if not isinstance(data, dict):
        return None

    for k, v in data.items():
        if isinstance(k, str) and k.lower() in PAGE_LIST_KEYS and _is_dict_list(v):
            return data, k, v

    for _k, v in data.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(k2, str) and k2.lower() in PAGE_LIST_KEYS and _is_dict_list(v2):
                    return v, k2, v2

    return None


def _tagged_group(lst):
    """(D6) Try each PAGE_NUMBER_FIELD_KEYS candidate as a grouping field for
    a flat list of dicts. Returns (field_name, {value: [items]}) for the
    first field where a strict majority of items carry it (D6: fewer than
    half carrying the tag is not evidence of a multi-page document either)
    AND it has more than one distinct value — or None if no field qualifies.
    Group order follows first-seen value order.
    """
    n = len(lst)
    for field in PAGE_NUMBER_FIELD_KEYS:
        tagged = [(item, _get_field_ci(item, {field})) for item in lst]
        tagged = [(item, val) for item, val in tagged if val is not None]
        if len(tagged) * 2 <= n:  # not a strict majority
            continue

        distinct = []
        for _, val in tagged:
            if val not in distinct:
                distinct.append(val)
        if len(distinct) <= 1:
            continue

        groups = {val: [item for item, v in tagged if v == val] for val in distinct}
        return field, groups

    return None


def _find_family_b(data):
    """(D6) Depth <= 2 scan (same shape as Family A's) for any flat list of
    dicts that qualifies under `_tagged_group`. Returns
    (container_parent, key, list, tag_field, groups), or None.
    """
    if not isinstance(data, dict):
        return None

    candidates = []
    for k, v in data.items():
        if _is_dict_list(v):
            candidates.append((data, k, v))
    for _k, v in data.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if _is_dict_list(v2):
                    candidates.append((v, k2, v2))

    for parent, key, lst in candidates:
        result = _tagged_group(lst)
        if result is not None:
            tag_field, groups = result
            return parent, key, lst, tag_field, groups

    return None


def _replace_container_value(data, parent, key, new_value):
    """Return a shallow-copied `data` with `key` in the (possibly nested)
    `parent` dict replaced by `new_value`. Sibling keys at every level are
    preserved untouched — this is the "header" (Description/Styles-equivalent)
    that each split-out page keeps.
    """
    if parent is data:
        doc = dict(data)
        doc[key] = new_value
        return doc

    new_parent = dict(parent)
    new_parent[key] = new_value
    return {k: (new_parent if v is parent else v) for k, v in data.items()}


def _write_json_page(page_output_dir, base_name, page_number, doc):
    output_filepath = os.path.join(page_output_dir, f"{base_name}-{page_number}.json")
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)


def split_json_document(input_file_path, output_dir):
    """
    Splits a single JSON OCR/Doc-AI document into single-page JSON files.

    Detection order:
      1. Family A — a nested page-list container (D1-D3, D5).
      2. Family B — a flat list tagged with a per-item page field (D6).
      3. Family C — neither pattern found: fallback to today's behaviour.
    """
    with open(input_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    base_name = os.path.splitext(os.path.basename(input_file_path))[0]
    page_output_dir = os.path.join(output_dir, base_name)
    os.makedirs(page_output_dir, exist_ok=True)

    # 1. Family A (Azure, docTR, Google Doc AI)
    family_a = _find_family_a(data)
    if family_a is not None:
        parent, key, page_list = family_a
        for i, page_obj in enumerate(page_list, 1):
            page_number = _get_field_ci(page_obj, PAGE_NUMBER_FIELD_KEYS)
            page_number = str(page_number) if page_number is not None else str(i)
            doc = _replace_container_value(data, parent, key, page_obj)
            _write_json_page(page_output_dir, base_name, page_number, doc)
        return len(page_list)

    # 2. Family B (AWS Textract)
    family_b = _find_family_b(data)
    if family_b is not None:
        parent, key, _lst, _tag_field, groups = family_b
        for page_number, items in groups.items():
            doc = _replace_container_value(data, parent, key, items)
            _write_json_page(page_output_dir, base_name, str(page_number), doc)
        return len(groups)

    # 3. Family C fallback (pero-ocr, OCR.space)
    _write_json_page(page_output_dir, base_name, "1", data)
    return 1


# def split_json_document(input_file_path, output_dir):
#     """
#     Splits a single JSON OCR/Doc-AI document into single-page JSON files,
#     mirroring split_alto_xml()'s contract exactly (same naming pattern,
#     same directory shape, same int page-count return) — see 31.plan.md.
#
#     Detection order (never assume, never break today's single-page fixtures):
#       1. Family A — a nested page-list container (D1-D3, D5).
#       2. Family B — a flat list tagged with a per-item page field (D6).
#       3. Family C — neither pattern found: today's behaviour, one output
#          file, page number "1", full document unchanged (D4).
#
#     Returns:
#         int: The number of pages written (always >= 1; a JSON document has
#         no "no pages found" case the way an ALTO file can have none).
#     """
#     with open(input_file_path, "r", encoding="utf-8") as f:
#         data = json.load(f)
#
#     base_name = os.path.splitext(os.path.basename(input_file_path))[0]
#     page_output_dir = os.path.join(output_dir, base_name)
#     os.makedirs(page_output_dir, exist_ok=True)
#
#     family_a = _find_family_a(data)
#     if family_a is not None:
#         parent, key, page_list = family_a
#         print(f"  -> Found {len(page_list)} page(s) (nested list). Splitting...")
#         for i, page_obj in enumerate(page_list, 1):
#             page_number = _get_field_ci(page_obj, PAGE_NUMBER_FIELD_KEYS)
#             page_number = str(page_number) if page_number is not None else str(i)
#             doc = _replace_container_value(data, parent, key, page_obj)
#             _write_json_page(page_output_dir, base_name, page_number, doc)
#         print(f"  -> Successfully split into {len(page_list)} file(s) in '{page_output_dir}'.")
#         return len(page_list)
#
#     family_b = _find_family_b(data)
#     if family_b is not None:
#         parent, key, _lst, _tag_field, groups = family_b
#         print(f"  -> Found {len(groups)} page(s) (tagged flat list). Splitting...")
#         for page_number, items in groups.items():
#             doc = _replace_container_value(data, parent, key, items)
#             _write_json_page(page_output_dir, base_name, str(page_number), doc)
#         print(f"  -> Successfully split into {len(groups)} file(s) in '{page_output_dir}'.")
#         return len(groups)
#
#     # Family C fallback (D4): neither pattern found, route through the same
#     # writer as a single page — preserves 100% of current behaviour.
#     print("  -> No multi-page pattern detected. Writing as single page.")
#     _write_json_page(page_output_dir, base_name, "1", data)
#     return 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Split multi-page ALTO XML or generic JSON OCR files into single-page files.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("input_dir", help="Path to the directory containing ALTO XML or JSON files to process.")
    parser.add_argument("output_dir", help="Path to the directory where split files will be saved.")
    args = parser.parse_args(argv)

    _doc_cfg = configparser.ConfigParser()
    _doc_cfg.read(DOCUMENT_CONFIG_PATH)
    document_json_dir = document_hook.resolve_document_json_dir(_doc_cfg.get("DOCUMENT", "JSON_DIR", fallback=""))

    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory not found at '{args.input_dir}'")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Output will be saved to '{os.path.abspath(args.output_dir)}'\n")

    all_files = sorted(os.listdir(args.input_dir))

    # (#31) output_types is format-aware: only declare the formats actually
    # present in input_dir, instead of hardcoding "xml". Falls back to
    # ["xml"] when the directory has neither, preserving prior behaviour.
    _formats_present = []
    if any(fname.lower().endswith(".xml") for fname in all_files):
        _formats_present.append("xml")
    if any(fname.lower().endswith(".json") for fname in all_files):
        _formats_present.append("json")
    if not _formats_present:
        _formats_present = ["xml"]

    _logger = ParadataLogger(
        program="alto-postprocess",
        config={
            "script": "page_split",
            "input_dir": str(args.input_dir),
            "output_dir": str(args.output_dir),
        },
        paradata_dir="paradata",
        output_types=_formats_present,
        config_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup"),
    )

    # (#10) Track documents (the unit of input) and pages (the unit of output)
    # separately. input_files_total counts source documents; the per-page count
    # feeds the per-format output total for throughput; successfully_processed
    # is the number of documents successfully split — so it can never exceed
    # inputs.
    _total_inputs = 0
    _docs_ok = 0

    try:
        for filename in all_files:
            lower_name = filename.lower()
            if lower_name.endswith(".xml"):
                fmt, split_fn = "xml", split_alto_xml
            elif lower_name.endswith(".json"):
                fmt, split_fn = "json", split_json_document
            else:
                continue

            input_file_path = os.path.join(args.input_dir, filename)
            print(f"Processing '{filename}'...")
            _total_inputs += 1
            try:
                page_count = split_fn(input_file_path, args.output_dir)
                _logger.log_success(fmt, count=page_count)  # pages produced
                if page_count > 0:
                    _docs_ok += 1
                    # (atrium-project#13) page_split is the first stage to see the
                    # original input, so it is the natural first writer of `source`
                    # — set_source() is itself a no-op if a baseline already has one.
                    doc_id = _doc_id_from_filename(filename, fmt)
                    document_hook.write_document_block(
                        document_json_dir,
                        doc_id,
                        _logger,
                        source={
                            "sha256": _sha256_of(input_file_path),
                            "filename": filename,
                            "media_type": "application/alto+xml" if fmt == "xml" else "application/json",
                            "page_count": page_count,
                        },
                    )
            except Exception as e:
                _logger.log_skip(str(filename), str(e))
    finally:
        _logger.finalize(input_total=_total_inputs, processed_total=_docs_ok)


if __name__ == "__main__":
    main()
