"""
document_hook.py — repo-local glue between this repo's stage scripts and the
hub-canonical `atrium_document.py` paired-hook model (issue #13 / atrium-project#13).

Unlike `atrium_document.py`/`atrium_document.schema.json` themselves, this module is
NOT hub-canonical and is not copied byte-identical across the tool repos (no
para-drift enforcement here) — the grouping logic below is specific to how THIS
repo's stage scripts batch many documents' pages into a single run, which the hub
module has no opinion on.

Enablement is config-driven, not a per-script flag: a single `[DOCUMENT].JSON_DIR`
setting (or `DOCUMENT_JSON_DIR` env override) turns the hook on for every stage at
once, pointing them all at the same directory of `<doc_id>.document.json` files. Left
empty (the default), every function below is a no-op — standalone runs are
unaffected, matching rule 3 of the accretion contract.

Ownership note: every write here uses PROGRAM_NAME = "alto-postprocess", the single
name `atrium_document.BLOCK_OWNERS` recognises for this repo's blocks — NOT each
stage's own ParadataLogger `program` string (`langID-classify`, `langID-aggregate`,
...). Normalising those paradata program names is a separate, still-open item (see
`agent_dev_logs/digests/13.digest.md` §Open/next) and is deliberately untouched here.
"""

from __future__ import annotations

import logging
import os
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from atrium_document import DocumentRecord

logger = logging.getLogger(__name__)

PROGRAM_NAME = "alto-postprocess"


def resolve_document_json_dir(configured: Optional[str] = None) -> str:
    """`DOCUMENT_JSON_DIR` env var wins, then the `[DOCUMENT].JSON_DIR` config value.

    Empty string means disabled — every helper below then does nothing.
    """
    return os.getenv("DOCUMENT_JSON_DIR") or (configured or "")


def document_path(document_json_dir: str, doc_id: str) -> str:
    return os.path.join(document_json_dir, f"{doc_id}.document.json")


def paradata_ref_for(logger) -> str:
    """Best-effort path to the paradata JSON this stage's ParadataLogger will emit.

    A plain function of the logger's own attributes, so callers that run inside a
    multiprocessing worker (which never sees the logger object itself — it isn't
    passed across the process boundary) can compute it once in the parent process
    and pass the resulting string down instead.
    """
    return os.path.join(logger.paradata_dir, f"{logger.run_id}_{logger.program}.json")


def write_document_block(
    document_json_dir: str,
    doc_id: str,
    run_id: Optional[str],
    paradata_ref: str = "",
    *,
    source: Optional[Dict[str, Any]] = None,
    set_blocks: Optional[Dict[str, Any]] = None,
    merge_blocks: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> None:
    """Open `<doc_id>.document.json` under `document_json_dir` (if configured and if
    it already exists), apply this stage's own contribution, and write it back in
    place. A missing baseline is safe (rule 3): the record then holds just this
    stage's part. No-ops entirely when `document_json_dir` is falsy.
    """
    if not document_json_dir:
        return
    if not any([source, set_blocks, merge_blocks]):
        return

    path = document_path(document_json_dir, doc_id)
    with DocumentRecord.open(
        doc_id,
        PROGRAM_NAME,
        baseline=path,
        run_id=run_id,
        paradata_ref=paradata_ref,
        out_dir=document_json_dir,
    ) as doc:
        if source:
            doc.set_source(**source)
        for block, payload in (set_blocks or {}).items():
            doc.set_block(block, payload)
        for block, records in (merge_blocks or {}).items():
            if records:
                doc.merge_block(block, records)


def group_tasks_by_doc(tasks: Iterable[Sequence[Any]]) -> "OrderedDict[str, List[Any]]":
    """Group (file_id, page_id, ...) task tuples by file_id, preserving the page
    order each task list was built in (the extraction CSV's row order).
    """
    by_doc: "OrderedDict[str, List[Any]]" = OrderedDict()
    for task in tasks:
        file_id, page_id = str(task[0]), task[1]
        by_doc.setdefault(file_id, []).append(page_id)
    return by_doc


def read_page_text(output_text_dir: str, file_id: str, page_id: Any) -> Optional[str]:
    """Read back one page's extracted text, mirroring classify_TEXT.py's own lookup
    (hyphen filename first, underscore fallback for older layouts).
    """
    base = os.path.join(str(output_text_dir), str(file_id))
    for sep in ("-", "_"):
        candidate = os.path.join(base, f"{file_id}{sep}{page_id}.txt")
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                return fh.read()
    return None


def pages_and_content_from_text(
    output_text_dir: str,
    file_id: str,
    page_ids: Sequence[Any],
    engine: str,
    force_single_page: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Build the `pages[].ocr` records + the doc-level `content.text` for one
    document from its already-written page .txt files. Pages whose text could not
    be read back are skipped rather than guessed at.

    `content.text` is always the full document (every readable page concatenated,
    in source-page order, joined on a blank line) regardless of `force_single_page` —
    that flag is purely a `pages[]` assembly policy (issue #37 / D4): it does not
    change what text is extracted, only how many `pages[]` rows describe it.

    force_single_page=False (default): one `pages[]` row per source page, as before.
    force_single_page=True: every source page for this document collapses into a
    SINGLE `pages[]` row (`page: "1"`), whose `ocr.source_pages` lists the original
    page labels in the order they were concatenated — so the mapping back to
    individual source pages is preserved rather than lost.
    """
    page_records: List[Dict[str, Any]] = []
    texts: List[str] = []
    source_pages: List[str] = []
    for page_id in page_ids:
        text = read_page_text(output_text_dir, file_id, page_id)
        if text is None:
            continue
        source_pages.append(str(page_id))
        texts.append(text)
        if not force_single_page:
            page_records.append({"page": str(page_id), "ocr": {"engine": engine}})
    joined = "\n\n".join(t for t in texts if t)

    if force_single_page and source_pages:
        page_records = [
            {
                "page": "1",
                "ocr": {
                    "engine": engine,
                    "source_pages": source_pages,
                    "force_single_page": True,
                },
            }
        ]

    return page_records, {"text": joined or None}


def quality_band(clear: int, noisy: int, trash: int) -> str:
    """Reduce a page's Clear/Noisy/Trash line counts (already computed by
    aggregate_STAT.py) to the schema's three-way `quality_band` enum. Deterministic
    plurality vote; ties favour the more optimistic band (Clear over Noisy over
    Trash), matching how a human skimming the counts would call a close page.
    """
    if clear >= noisy and clear >= trash:
        return "Clear"
    if noisy >= trash:
        return "Noisy"
    return "Trash"
