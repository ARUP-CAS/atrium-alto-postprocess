#!/usr/bin/env python3
"""
tools/build_annotation_pack.py
==============================
Turn the witnessed-string queue into something an archivist can actually work
through, stratified by DISAGREEMENT rather than by frequency.

Why not frequency order
-----------------------
`short_garbage_witness_report.py --distinct` sorts most-frequent-first, which is
right for "how much does each decision buy" and wrong for "where is the expert's
judgement worth most". Most high-frequency rows are ones where the pipeline and
the corpus evidence already agree; re-confirming those spends the scarcest
resource in this issue on the cheapest question.

Cross-tabulating the two on the delivered queue (5,005 strings / 20,078 lines,
full-collection lexicon) shows where the disagreement actually lives:

    categ_current       fully recoverable        partial          none
    Clear              526 str / 13,044     281 / 345      414 / 1,005
    Noisy              165 / 301            101 / 112      214 / 231
    Trash              743 / 1,791          356 / 367    2,205 / 2,882

Two cells are the whole point:

* **`Trash` + fully recoverable** (743 strings / 1,791 lines) — text the pipeline
  discarded that the corpus can reconstruct. `1 fraament okraie` is "1 fragment
  okraje"; `Eouus caballus` is `Equus caballus`; `http://www.arub.cz` is an
  institutional URL. This issue has spent months on garbage reaching `Clear`;
  this is the mirror, and nothing in the thread measures it.
* **`Clear` + no recoverability** (414 / 1,005) — Dana's original concern. Noisier
  than it looks, which is why the evidence columns travel with it: the cell holds
  `sektlll` and `IOIAL`, and also `Kaukasus`, `Feuersteinspan` and
  `Schuhleistenkeilbruchstueck`, which are correct German archaeological terms too
  rare for a corpus-derived lexicon.

Design rules, each of which this issue learned the hard way
----------------------------------------------------------
**No proposed label ever reaches the answer column.** The evidence columns inform;
`gold_categ` stays empty. Issue #30 has built a circular objective three times --
a self-referential sweep, an exposure ratio scored against `categ`, an A/B verdict
ranked by a metric that preferred the worst arm -- and a pre-filled label accepted
by default would be the fourth.

**`categ_current` is hidden except where it is the question.** Showing the
pipeline's answer to the person checking the pipeline biases agreement upward. Tab
B is the exception: there the disagreement between two of its own answers is the
thing being adjudicated.

**A suggestion carries its mechanism.** `diacritics` is a near-certain correction;
`edit1` may be coincidence (`Linum`/`ilium` are one edit apart and both real
Latin). Collapsing the two throws away the only thing separating evidence from
noise.

**Nothing here is a verdict.** A string can be perfectly recoverable and still be
unusable in the output — `ppole` recovers to `pole` and is in fact an abbreviation
for *popelnicová pole*, not a scan error at all (@david-spacil, 2026-09-19). What
belongs in `Trash` versus `Noisy` is the archive's call, and this tool exists to
put the evidence in front of the person making it.

Usage
-----
    # after ocr_neighbours.py --annotate has added the evidence columns
    python tools/build_annotation_pack.py \\
        --queue issue30_out/04_witness_distinct_evidence.csv \\
        --corpus data_samples/DOC_LINE_CATEG \\
        --out-dir issue30_out/pack

Writes one CSV per tab plus a README. CSV rather than xlsx so it has no
dependency beyond the standard library; open it in any spreadsheet.

Exit codes
----------
  0  Pack written.
  2  Bad arguments, missing input, or a queue without the evidence columns.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

TOOL_VERSION = "1.0"

#: Columns the queue must already carry. `ocr_neighbours.py --annotate` adds the
#: last three; without them this tool would be sorting rows by nothing.
REQUIRED = ("text", "occurrences", "categ_current", "nearest_attested", "recoverability")

#: Tab A is the finding nobody was looking for, so it goes first.
TABS = {
    "A_discarded_but_recoverable": "Trash-side: the pipeline discarded it, the corpus can reconstruct it",
    "B_clear_but_unrecoverable": "Clear-side: the pipeline kept it, the corpus cannot place it",
    "C_clear_and_recoverable": "Clear-side: recoverable, includes abbreviations and conventions",
    "D_trash_and_unrecoverable": "Trash-side: both agree — a SAMPLE for spot-checking, not an enumeration",
}

#: How many of tab D to sample. It is 2,205 strings the pipeline and the evidence
#: agree about; enumerating them buys almost nothing, and a sample large enough to
#: catch a systematic error is the useful version.
DEFAULT_D_SAMPLE = 150

#: Occurrences at or above this put a family on the high-leverage list regardless
#: of which cell it falls in.
DEFAULT_LEVERAGE = 100


def dominant_categ(mix: str) -> str:
    """The commonest category in a `Clear:539|Trash:4` mix, or `?`."""
    best, best_n = "?", -1
    for part in (mix or "").split("|"):
        name, _, count = part.partition(":")
        try:
            n = int(count)
        except ValueError:
            continue
        if n > best_n:
            best, best_n = name, n
    return best


def is_split(mix: str) -> bool:
    """True when the pipeline gave this identical string more than one answer."""
    return "|" in (mix or "")


def band(recoverability: str) -> str:
    """`full` / `partial` / `none` / `unknown` for one row."""
    if not recoverability:
        return "unknown"
    try:
        v = float(recoverability)
    except ValueError:
        return "unknown"
    if v >= 0.99:
        return "full"
    return "partial" if v > 0 else "none"


def family_key(text: str) -> str:
    """Group `ppole`, `ppole -` and `ppole?` into one decision.

    Strips case, collapses whitespace and drops leading/trailing digits and
    punctuation. The variants are shown together on the row, because the variation
    pattern is itself evidence: seeing three spellings of one label says "form
    field" louder than any single one of them.
    """
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    t = re.sub(r"^[\d\W_]+", "", t)
    return re.sub(r"[\d\W_]+$", "", t)


def assign_tab(row: dict) -> str:
    categ = dominant_categ(row.get("categ_current", ""))
    b = band(row.get("recoverability", ""))
    if categ == "Trash":
        return "A_discarded_but_recoverable" if b == "full" else "D_trash_and_unrecoverable"
    # Clear and Noisy are both "the pipeline kept it".
    return "B_clear_but_unrecoverable" if b == "none" else "C_clear_and_recoverable"


def load_page_context(corpus: Path, wanted: set[tuple[str, str, str]], text_column: str) -> dict:
    """Pull +/-2 lines around each wanted locator. Returns {(file,page,line): str}.

    One pass per document, and only for documents that contain a wanted locator.
    Absent corpus or unreadable file yields no context rather than an error: the
    pack is still usable without it, just less so.
    """
    if not corpus or not corpus.exists():
        return {}
    by_doc: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for f, p, ln in wanted:
        by_doc[f].add((p, ln))

    out: dict[tuple[str, str, str], str] = {}
    files = sorted(corpus.glob("*.csv")) if corpus.is_dir() else [corpus]
    for path in files:
        stem = path.stem
        if stem not in by_doc:
            continue
        try:
            with open(path, newline="", encoding="utf-8", errors="replace") as fh:
                rows = list(csv.DictReader(fh))
        except OSError:
            continue
        per_page: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            per_page[str(r.get("page_num", ""))].append(r)
        for page, line in by_doc[stem]:
            seq = per_page.get(page, [])
            idx = next((i for i, r in enumerate(seq) if str(r.get("line_num", "")) == line), None)
            if idx is None:
                continue
            lo, hi = max(0, idx - 2), min(len(seq), idx + 3)
            window = []
            for i in range(lo, hi):
                body = str(seq[i].get("original_text") or seq[i].get(text_column) or "").strip()
                window.append(f">>{body}<<" if i == idx else body)
            out[(stem, page, line)] = " / ".join(w for w in window if w)
    return out


def build_pack(rows: list[dict], context: dict, d_sample: int, leverage: int, seed: int) -> dict:
    """Group into families, assign tabs, and return {tab: [row]}."""
    families: dict[str, dict] = {}
    for r in rows:
        key = family_key(r["text"])
        try:
            occ = int(r.get("occurrences") or 0)
        except ValueError:
            occ = 0
        fam = families.setdefault(
            key,
            {
                "variants": [],
                "lines_settled": 0,
                "mix": Counter(),
                "evidence": "",
                "recoverability": r.get("recoverability", ""),
                "note": r.get("recoverability_note", ""),
                "clauses": r.get("clauses", ""),
                "locator": (
                    str(r.get("example_file", "")),
                    str(r.get("example_page_num", "")),
                    str(r.get("example_line_num", "")),
                ),
                "split": False,
            },
        )
        fam["variants"].append(r["text"])
        fam["lines_settled"] += occ
        for part in (r.get("categ_current") or "").split("|"):
            name, _, count = part.partition(":")
            try:
                fam["mix"][name] += int(count)
            except ValueError:
                pass
        if is_split(r.get("categ_current", "")):
            fam["split"] = True
        if r.get("nearest_attested") and not fam["evidence"]:
            fam["evidence"] = r["nearest_attested"]

    tabs: dict[str, list[dict]] = {name: [] for name in TABS}
    for fam in families.values():
        mix = "|".join(f"{c}:{n}" for c, n in fam["mix"].most_common())
        probe = {"categ_current": mix, "recoverability": fam["recoverability"]}
        tab = assign_tab(probe)
        out = {
            "text": fam["variants"][0],
            "variants": " | ".join(sorted(set(fam["variants"]))[:6]),
            "lines_settled": fam["lines_settled"],
            "nearest_attested": fam["evidence"],
            "recoverability": fam["recoverability"],
            "recoverability_note": fam["note"],
            "clauses": fam["clauses"],
            "page_context": context.get(fam["locator"], ""),
            "high_leverage": "yes" if fam["lines_settled"] >= leverage else "",
            "gold_categ": "",
            "confidence": "",
            "note": "",
        }
        # Tab B is the only place the pipeline's own answer is shown: there the
        # disagreement IS the question. Everywhere else it would anchor.
        if tab == "B_clear_but_unrecoverable" or fam["split"]:
            out["categ_current"] = mix
        tabs[tab].append(out)

    for name in tabs:
        tabs[name].sort(key=lambda r: -r["lines_settled"])

    # D is agreement; sample it rather than enumerate it.
    if d_sample and len(tabs["D_trash_and_unrecoverable"]) > d_sample:
        rng = random.Random(seed)
        pool = tabs["D_trash_and_unrecoverable"]
        keep = pool[: min(20, len(pool))]  # the largest, which are worth seeing
        rest = rng.sample(pool[len(keep) :], d_sample - len(keep))
        tabs["D_trash_and_unrecoverable"] = keep + rest
    return tabs


def write_pack(tabs: dict, out_dir: Path, d_total: int, seed: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    order = [
        "text",
        "variants",
        "lines_settled",
        "high_leverage",
        "nearest_attested",
        "recoverability",
        "recoverability_note",
        "clauses",
        "page_context",
        "categ_current",
        "gold_categ",
        "confidence",
        "note",
    ]
    for name, rows in tabs.items():
        fields = [c for c in order if any(c in r for r in rows)] or order
        with open(out_dir / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    readme = out_dir / "README.md"
    readme.write_text(
        f"""# Annotation pack — issue #30

Four files, split by where the pipeline and the corpus evidence **disagree**. Fill
`gold_categ` only: `Clear` / `Noisy` / `Trash` / `Non-text` / `Empty`. **Leave
anything uncertain blank** — blank is skipped, never guessed. `confidence` and
`note` are free text and optional.

One row is one decision covering `lines_settled` lines. `variants` shows the
spellings it covers.

| file | rows | what it is |
|---|---:|---|
| `A_discarded_but_recoverable.csv` | {len(tabs["A_discarded_but_recoverable"])} | The pipeline threw it away; the corpus can reconstruct it. `1 fraament okraie` is "1 fragment okraje". **Start here** — nothing in this issue has measured this class. |
| `B_clear_but_unrecoverable.csv` | {len(tabs["B_clear_but_unrecoverable"])} | The pipeline kept it; the corpus cannot place it. The original concern. Shows `categ_current` because the disagreement is the question. |
| `C_clear_and_recoverable.csv` | {len(tabs["C_clear_and_recoverable"])} | Kept and reconstructable — abbreviations, conventions, form labels. |
| `D_trash_and_unrecoverable.csv` | {len(tabs["D_trash_and_unrecoverable"])} | Both agree it is garbage. A **sample** of {d_total} (seed {seed}), for spot-checking only. |

## Reading the evidence

`nearest_attested` gives the closest word in the archive's own vocabulary and
**how** it was reached:

* `diacritics` — accents restored. Near-certain.
* `confusion` — a known scanner confusion (`j`/`i`, `rn`/`m`). Strong.
* `edit1` — one character different. **May be coincidence**: `Linum`/`ilium` are
  one edit apart and both real Latin.

`recoverability` is the share of a row's words that are attested or one step from
attested. **It is asymmetric.** High means probably real text. **Zero means only
that this corpus has nothing to say** — `Kaukasus` and
`Schuhleistenkeilbruchstueck` score zero and are perfectly good words.

Nothing here proposes an answer, and recoverable does not mean usable: `ppole`
recovers to `pole` and is an abbreviation for *popelnicová pole*, not a scan error.
Whether a damaged-but-readable line is still worth keeping is the judgement being
asked for.

*Generated by `tools/build_annotation_pack.py` v{TOOL_VERSION}. Nothing you write
changes the pipeline; the labels are joined back separately and inspected first.*
""",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="build_annotation_pack.py",
        description="Stratify the witness queue by pipeline/evidence disagreement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--queue", required=True, metavar="CSV", help="Output of ocr_neighbours.py --annotate.")
    ap.add_argument("--out-dir", required=True, metavar="DIR", help="Where to write the pack.")
    ap.add_argument("--corpus", metavar="DIR", help="DOC_LINE_CATEG, for page context. Optional.")
    ap.add_argument("--text-column", default="text", metavar="COL")
    ap.add_argument("--d-sample", type=int, default=DEFAULT_D_SAMPLE, metavar="N", help="Rows to keep from tab D.")
    ap.add_argument("--leverage", type=int, default=DEFAULT_LEVERAGE, metavar="N", help="lines_settled to flag.")
    ap.add_argument("--seed", type=int, default=30, metavar="N", help="Sampling seed, recorded in the README.")
    args = ap.parse_args(argv)

    queue = Path(args.queue)
    if not queue.exists():
        print(f"error: path not found: {queue}", file=sys.stderr)
        return 2
    with open(queue, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            print(
                f"error: {queue} is missing {', '.join(missing)}.\n"
                "       Run it through `ocr_neighbours.py --annotate` first — without the\n"
                "       evidence columns this tool would be sorting rows by nothing.",
                file=sys.stderr,
            )
            return 2
        rows = list(reader)
    if not rows:
        print(f"error: {queue} has no rows", file=sys.stderr)
        return 2

    wanted = {
        (str(r.get("example_file", "")), str(r.get("example_page_num", "")), str(r.get("example_line_num", "")))
        for r in rows
        if r.get("example_file")
    }
    context = load_page_context(Path(args.corpus), wanted, args.text_column) if args.corpus else {}
    if args.corpus and not context:
        print("note: no page context resolved — check --corpus points at the right batch", file=sys.stderr)

    tabs = build_pack(rows, context, args.d_sample, args.leverage, args.seed)
    d_total = sum(1 for r in rows if assign_tab(r) == "D_trash_and_unrecoverable")
    write_pack(tabs, Path(args.out_dir), d_total, args.seed)

    print(f"\nwrote {len(TABS)} tabs to {args.out_dir}")
    for name, label in TABS.items():
        n = len(tabs[name])
        lines = sum(r["lines_settled"] for r in tabs[name])
        print(f"  {name:<32} {n:>5} rows / {lines:>6} lines   {label}")
    print("\n  `gold_categ` is empty on every row, by design. Nothing here proposes an answer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
