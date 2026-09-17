#!/usr/bin/env python3
"""
tools/build_token_lexicon.py
============================
Build the corpus's own dictionary: a token -> DOCUMENT-FREQUENCY table for the
``rule_short_garbage`` vocabulary signal (issue #30, D14).

Why this exists
---------------
Issue #30 ends in the same place from both sides. ``_has_strong_garbage_evidence()``
is ``False`` on the entire short diacritic-free population, so the merged gate
suspended the rule there rather than narrowing it; ``_has_shape_garbage_evidence()``
narrows it back, but only for the half that is separable BY SHAPE. The residue --
``edelite``, ``vfetennl k.`` -- is spelled exactly the way a word is spelled. Both
the issue thread and the in-tree notes conclude the same thing: separating it
needs a lexicon, not another character test.

The obvious lexicons are not usable here. The Czech ones (korektor and friends)
are CC BY-NC-SA, and this pipeline's output would inherit the clause. A Latin
binomial list would cover ``Equus caballus`` and miss ``Reg.Bez.Aussig.``; a German
one the reverse. And every one of them would be wrong in the same way about the
same thing -- none contains the site codes, context labels and excavation
shorthand that make up most of this corpus's short lines.

The corpus is its own best dictionary, and it is already on disk:

    A token that appears in many DISTINCT DOCUMENTS is vocabulary.
    A token that appears in one is what that scan did to some ink.

DOCUMENT frequency, not line frequency: OCR noise repeats freely inside the scan
that produced it -- the same misread header on forty pages -- and almost never
across scans produced years apart by different operators. Counting lines would
let one badly-scanned document vote its own garbage into the dictionary; counting
documents makes that take forty independent documents agreeing.

And it is a property of the DATA, not of the classifier. Nothing here reads
``categ``, ``quality_score`` or any other pipeline output. That is deliberate and
it is the whole point: this issue has already built one circular objective by
scoring trials against the pipeline's own labels, and a lexicon filtered by
"lines we called Clear" would be the same mistake wearing a different hat.

What it is not
--------------
Not a word list, and it must not be read as one. It is an attestation count.
``Poaceae`` scoring 40 does not mean ``Poaceae`` is Czech; it means forty separate
archaeobotanical reports contain that string, which is the only claim the witness
needs in order to stop convicting it. Symmetrically, absence is weak evidence and
is treated as such -- see ``SHORT_GARBAGE_LEXICON_CONVICT``, which ships false.

Output
------
A TSV with a ``#`` provenance header, then ``token<TAB>document_frequency``, sorted
by descending frequency then token. Tokens only -- no line text, no document
names, no counts per document -- so the artefact can be shared and diffed without
a redaction pass, the same discipline ``tools/issue30_perplex_report.py`` follows.

Tokenisation is imported from ``text_util``, never reimplemented. Four separate
harness divergences in this repository came from a tool carrying its own copy of
logic that then moved; the table has to be built with the same ``_split_subtokens``
and ``_STRIP_CHARS`` the predicate looks tokens up with, or lookups silently miss.

Usage
-----
    # Build over a DOC_LINE_CATEG corpus
    python tools/build_token_lexicon.py /path/to/DOC_LINE_CATEG -o tools/gold/token_df.tsv

    # Then point the predicate at it (setup/config.txt, [TEXT_UTILS])
    SHORT_GARBAGE_LEXICON_PATH   = tools/gold/token_df.tsv
    SHORT_GARBAGE_LEXICON_MIN_DF = 3

    # Inspect what a specific token scored without loading the whole table
    python tools/build_token_lexicon.py <corpus> --lookup malakofauna oueussd Poaceae

Exit codes
----------
  0  Table written (or lookup completed).
  2  Bad arguments / missing path.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import text_util as tu  # noqa: E402

# A long OCR line can exceed the csv module's default field limit, and dying
# halfway through a multi-million-line corpus with an opaque error helps nobody.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

TOOL_VERSION = "1.0"

#: Minimum alphabetic characters for a token to be counted at all. Matched to
#: SHORT_GARBAGE_WITNESS_MIN_ALPHA: the predicate never looks up anything shorter,
#: so storing them would only inflate the table.
DEFAULT_MIN_ALPHA = 4


def iter_tokens(text: str):
    """Yield lookup-normalised tokens from one line, exactly as the predicate does.

    Mirrors ``text_util.shape_garbage_clauses``: split on whitespace, then on
    ``. - –`` via ``_split_subtokens``, strip ``_STRIP_CHARS``, lowercase. Any
    divergence here is a table whose keys the predicate cannot find, which fails
    silently as "no vocabulary support" -- i.e. as a witness that convicts more,
    which is the direction that costs real lines.
    """
    for word in text.split():
        for sub in tu._split_subtokens(word):
            core = sub.strip(tu._STRIP_CHARS)
            if core:
                yield core.lower()


def build(
    corpus: Path,
    min_alpha: int = DEFAULT_MIN_ALPHA,
    text_column: str = "text",
    progress_every: int = 250_000,
    quiet: bool = False,
) -> tuple[dict[str, int], dict[str, int]]:
    """Count distinct documents per token over a DOC_LINE_CATEG directory or CSV.

    Returns ``(document_frequency, stats)``.

    Memory: one ``set`` of tokens per document, discarded at the end of that
    document, plus the running counter. A 12.7M-line corpus builds in a few
    minutes on one core with no GPU and no model.
    """
    files = sorted(corpus.glob("*.csv")) if corpus.is_dir() else [corpus]
    if not files:
        raise FileNotFoundError(f"no CSV files found in {corpus}")

    df_counts: dict[str, int] = defaultdict(int)
    stats = {"documents": 0, "lines": 0, "tokens_seen": 0, "files_unreadable": 0}

    for n, path in enumerate(files, 1):
        seen_in_doc: set[str] = set()
        try:
            with open(path, newline="", encoding="utf-8", errors="replace") as fh:
                reader = csv.DictReader(fh)
                if reader.fieldnames is None or text_column not in reader.fieldnames:
                    stats["files_unreadable"] += 1
                    continue
                for row in reader:
                    stats["lines"] += 1
                    for token in iter_tokens(str(row.get(text_column) or "")):
                        stats["tokens_seen"] += 1
                        if sum(c.isalpha() for c in token) < min_alpha:
                            continue
                        seen_in_doc.add(token)
        except OSError:
            stats["files_unreadable"] += 1
            continue

        # One document, one vote per token, however many times it occurs in it.
        for token in seen_in_doc:
            df_counts[token] += 1
        stats["documents"] += 1

        if not quiet and progress_every and stats["lines"] >= progress_every and n % 50 == 0:
            print(
                f"  … {n:,}/{len(files):,} documents, {stats['lines']:,} lines, {len(df_counts):,} distinct tokens",
                file=sys.stderr,
            )

    return dict(df_counts), stats


def write_table(
    df_counts: dict[str, int],
    out_path: Path,
    corpus: Path,
    stats: dict[str, int],
    min_alpha: int,
    min_df_note: int,
) -> int:
    """Write the TSV. Returns the number of rows written."""
    rows = sorted(df_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(f"# token document-frequency table — tools/build_token_lexicon.py v{TOOL_VERSION}\n")
        fh.write(f"# built: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
        fh.write(f"# corpus: {corpus}\n")
        fh.write(f"# documents: {stats['documents']}  lines: {stats['lines']}\n")
        fh.write(f"# min_alpha: {min_alpha}  distinct_tokens: {len(rows)}\n")
        fh.write(
            f"# intended SHORT_GARBAGE_LEXICON_MIN_DF: {min_df_note} "
            f"(rows at or above it: {sum(1 for _, v in rows if v >= min_df_note)})\n"
        )
        fh.write("# columns: token<TAB>document_frequency\n")
        fh.write("#\n")
        fh.write("# Attestation counts, NOT a claim that any row is a word of any language.\n")
        fh.write("# Contains no line text and no document identifiers.\n")
        for token, count in rows:
            fh.write(f"{token}\t{count}\n")
    return len(rows)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="build_token_lexicon.py",
        description="Build a token/document-frequency table for the #30 vocabulary signal.",
        epilog="Emits tokens and counts only — no line text, no document names.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("corpus", metavar="PATH", help="DOC_LINE_CATEG directory, or a single CSV.")
    ap.add_argument("-o", "--output", metavar="TSV", help="Where to write the table.")
    ap.add_argument(
        "--min-alpha",
        type=int,
        default=DEFAULT_MIN_ALPHA,
        metavar="N",
        help=(
            f"Skip tokens with fewer than N alphabetic characters (default {DEFAULT_MIN_ALPHA}, "
            "matching SHORT_GARBAGE_WITNESS_MIN_ALPHA — the predicate never looks up anything shorter)."
        ),
    )
    ap.add_argument(
        "--min-df",
        type=int,
        default=3,
        metavar="N",
        help=(
            "Recorded in the header as the intended SHORT_GARBAGE_LEXICON_MIN_DF and used for the "
            "summary. The table itself keeps every count, so the threshold stays a config decision "
            "and re-tuning it does not mean rebuilding (default 3)."
        ),
    )
    ap.add_argument("--text-column", default="text", metavar="COL", help="Column to tokenise (default: text).")
    ap.add_argument(
        "--lookup",
        nargs="+",
        metavar="TOKEN",
        help="Print the document frequency of these tokens instead of writing a table.",
    )
    ap.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output.")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus = Path(args.corpus)
    if not corpus.exists():
        print(f"error: path not found: {corpus}", file=sys.stderr)
        return 2
    if not args.output and not args.lookup:
        print("error: pass -o/--output to write a table, or --lookup to query without writing.", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"Building token document-frequency over {corpus} …", file=sys.stderr)

    try:
        df_counts, stats = build(
            corpus,
            min_alpha=args.min_alpha,
            text_column=args.text_column,
            quiet=args.quiet,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        f"\n=== token lexicon: {stats['documents']:,} document(s), {stats['lines']:,} line(s) ===",
        file=sys.stderr,
    )
    total = len(df_counts)
    print(f"  distinct tokens (>= {args.min_alpha} letters): {total:,}", file=sys.stderr)
    if total:
        at_threshold = sum(1 for v in df_counts.values() if v >= args.min_df)
        hapax = sum(1 for v in df_counts.values() if v == 1)
        print(
            f"  attested in >= {args.min_df} document(s):      {at_threshold:,} ({100.0 * at_threshold / total:.1f}%)",
            file=sys.stderr,
        )
        # The hapax share is the interesting diagnostic: it is roughly the size of
        # the population an unattested-token rule would reach, and a corpus where
        # it is small is a corpus where that rule has little to do.
        print(
            f"  seen in exactly one document:      {hapax:,} ({100.0 * hapax / total:.1f}%)  — where the residue lives",
            file=sys.stderr,
        )
    if stats["files_unreadable"]:
        print(
            f"  ! {stats['files_unreadable']} file(s) skipped (unreadable, or no {args.text_column!r} column)",
            file=sys.stderr,
        )

    if args.lookup:
        print(f"\n  {'token':<32} {'documents':>10}   verdict at min_df={args.min_df}")
        for raw in args.lookup:
            for token in iter_tokens(raw) or [raw.lower()]:
                count = df_counts.get(token, 0)
                verdict = "attested" if count >= args.min_df else "UNATTESTED"
                print(f"  {token:<32} {count:>10}   {verdict}")
        return 0

    written = write_table(
        df_counts,
        Path(args.output),
        corpus,
        stats,
        min_alpha=args.min_alpha,
        min_df_note=args.min_df,
    )
    print(f"\nTable written → {args.output} ({written:,} rows)", file=sys.stderr)
    print(
        "\nTo use it, set in setup/config.txt [TEXT_UTILS]:\n"
        f"  SHORT_GARBAGE_LEXICON_PATH   = {args.output}\n"
        f"  SHORT_GARBAGE_LEXICON_MIN_DF = {args.min_df}\n"
        "The veto is inert until SHORT_GARBAGE_WITNESS_ENABLE is also true.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
