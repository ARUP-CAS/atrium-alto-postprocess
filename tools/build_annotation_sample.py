#!/usr/bin/env python3
"""Turn the distinct-string queue into an annotation ask that can be PROJECTED.

Issue #30, H3. ``tools/build_annotation_pack.py`` splits the queue by *where the
pipeline and the corpus disagree*, which is the right cut for understanding what
is in it. This tool makes the different cut the flag decision needs: how many
decisions buy how much of the answer, and what is left over.

The problem it solves
---------------------
Every figure in issue #30 rests on 15 changed gold rows, because the existing
gold reaches 23 of the 20,078 lines the shape witness can convict. The plan's
answer was three separate asks -- H1 (all 5,005 strings), H2 (the 2,424-row
pack) and H3 ("sample ~200 singletons") -- and H2 turns out to be a re-cut of
the same 5,005 strings rather than a second population, so the three overlap
without saying so.

What the queue actually looks like, measured on the delivered
``07f_distinct_evidence.csv`` (5,005 strings, 4,807 spelling families, 20,078
lines):

* **Only 1,584 of the 4,807 families can produce a false positive at all.** The
  other 3,223 are already ``Trash``; the witness re-confirms them, so a label
  there cannot change the flag decision. Annotating in raw frequency order spends
  most of the budget on those.
* **Of the 15,041 at-risk lines, 11,671 are one family** (``ppole``). A census of
  the top 60 at-risk families plus every self-contradictory one -- 93 decisions
  -- reaches **94.8%** of at-risk exposure.
* **The remainder is 1,506 families averaging 1.1 lines each.** Enumerating that
  is 1,506 decisions for one twentieth of the answer. Sampling it is 200, at
  +/-6.9 points.

So the ask is a CENSUS of the head plus a SAMPLE of the tail, and the sample is
only worth taking if the frame is recorded well enough to project from. That is
what this tool writes out: each sampled row carries the stratum it was drawn
from and the weight that stratum projects at, so the result is arithmetic rather
than a second judgement call.

What it deliberately does not do
--------------------------------
It does not label anything, rank anything by likely answer, or drop rows it
thinks are obvious. Every ``gold_categ`` is blank. A queue that proposes answers
is a queue that gets agreed with, and this issue has already produced four
measurements that were confidently wrong.

It also does not read ``categ`` to decide what to ASK -- only to decide what is
*at risk*, which is a statement about the population under test, not about the
truth. The circular-objective mistake (digest R3) was scoring against the
pipeline's own answer; splitting the queue by the pipeline's answer so the
annotator's time goes where a label can change something is a different thing,
and the split is printed so it can be checked.

Usage
-----
::

    # The standard ask: census of the head, stratified sample of the tail
    python tools/build_annotation_sample.py \
        --queue issue30_out/04_witness_distinct.csv \
        --out-dir issue30_ask

    # Bigger sample when the budget allows; the frame records which was used
    python tools/build_annotation_sample.py --queue ... --out-dir ... \
        --census 100 --sample 300

Reads the same columns ``build_annotation_pack.py`` requires, and reuses its
``dominant_categ`` / ``band`` / ``family_key`` / ``is_split`` helpers rather than
re-implementing them -- a second copy of that vocabulary is a second thing to
drift, which is the argument already made for ``SHAPE_GARBAGE_CLAUSES`` and for
``build_token_lexicon.py``'s tokenisation import.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.build_annotation_pack import (  # noqa: E402
    band,
    dominant_categ,
    family_key,
    is_split,
)

TOOL_VERSION = "1.0"

#: Categories that mean "the pipeline is currently keeping this line". Only these
#: can turn into a NEW conviction when the witness is armed, so only these can
#: produce the Clear-loss the adoption gate rejects on.
AT_RISK = ("Clear", "Noisy")

#: Default census depth. On the delivered queue 60 families reach 87.8% of
#: at-risk exposure and 100 reach 88.8% -- the curve is flat past ~40, which is
#: the argument for stopping and sampling rather than continuing down it. The
#: self-contradictory families join regardless, taking the census to 93 rows and
#: 94.8%.
DEFAULT_CENSUS = 60

#: Default tail sample. 200 gives a 95% half-width of +/-6.9 points on the tail's
#: error rate -- against the 15 rows the whole flag decision currently rests on.
DEFAULT_SAMPLE = 200

DEFAULT_SEED = 30

#: Written to every output file. `lines_settled` is what one decision is worth.
OUT_COLUMNS = (
    "text",
    "variants",
    "lines_settled",
    "tranche",
    "stratum",
    "sampling_weight",
    "clauses",
    "categ_current",
    "nearest_attested",
    "recoverability",
    "gold_categ",
    "confidence",
    "note",
)


def _rows(queue: Path) -> list[dict]:
    with queue.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = {"text", "occurrences", "categ_current"} - set(reader.fieldnames or ())
        if missing:
            raise SystemExit(f"{queue}: missing required column(s) {sorted(missing)}")
        return list(reader)


def _int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def collapse_families(rows: list[dict]) -> list[dict]:
    """One decision per spelling family, the unit `build_annotation_pack` uses.

    `ppole`, `ppole -` and `ppole?` are one judgement about one form label. The
    variants stay visible on the row because the variation pattern is itself
    evidence.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[family_key(row.get("text", ""))].append(row)

    families = []
    for members in grouped.values():
        members.sort(key=lambda r: -_int(r.get("occurrences", "0")))
        head = members[0]
        lines = sum(_int(m.get("occurrences", "0")) for m in members)
        mix: dict[str, int] = defaultdict(int)
        for m in members:
            for part in (m.get("categ_current") or "").split("|"):
                name, _, count = part.partition(":")
                if name:
                    mix[name] += _int(count)
        merged = "|".join(f"{k}:{v}" for k, v in sorted(mix.items(), key=lambda kv: -kv[1]))
        clauses = sorted({c for m in members for c in (m.get("clauses") or "").split(",") if c})
        families.append(
            {
                "text": head.get("text", ""),
                "variants": " | ".join(dict.fromkeys(m.get("text", "") for m in members)),
                "lines_settled": lines,
                "clauses": ",".join(clauses),
                "categ_current": merged,
                "nearest_attested": head.get("nearest_attested", ""),
                "recoverability": head.get("recoverability", ""),
            }
        )
    families.sort(key=lambda f: (-f["lines_settled"], f["text"]))
    return families


def stratum_of(family: dict) -> str:
    """`<side>/<recoverability band>` -- the two axes that split this population.

    `side` is what a label can change; `band` is the evidence the annotator is
    being shown. Stratifying on both keeps the sample from being swamped by the
    unrecoverable-Trash cell, which is 2,190 of the 4,945 tail strings and the
    one where a label changes the least.
    """
    side = "at_risk" if dominant_categ(family["categ_current"]) in AT_RISK else "confirms_trash"
    return f"{side}/{band(family.get('recoverability', ''))}"


def _apportion(sizes: dict[str, int], total: int, population: int) -> dict[str, int]:
    """Proportional allocation that sums to ``total`` exactly (largest remainder)."""
    if not population or total <= 0:
        return {name: 0 for name in sizes}
    exact = {name: total * n / population for name, n in sizes.items()}
    alloc = {name: min(sizes[name], int(v)) for name, v in exact.items()}
    remaining = total - sum(alloc.values())
    order = sorted(sizes, key=lambda name: (-(exact[name] - int(exact[name])), name))
    while remaining > 0:
        progressed = False
        for name in order:
            if remaining <= 0:
                break
            if alloc[name] < sizes[name]:
                alloc[name] += 1
                remaining -= 1
                progressed = True
        if not progressed:  # every stratum exhausted; the tail is smaller than the ask
            break
    return alloc


def build(families: list[dict], census: int, sample: int, seed: int) -> dict:
    at_risk = [f for f in families if f["stratum"].startswith("at_risk")]
    contested = [f for f in families if is_split(f["categ_current"])]

    head = at_risk[:census]
    head_keys = {f["text"] for f in head}
    # Every self-contradictory family joins the census whatever its size: each one
    # resolves a documented case of the pipeline giving identical text two
    # different answers, so it is the highest value per decision in the queue.
    extra = [f for f in contested if f["text"] not in head_keys]

    tail = [f for f in at_risk[census:] if f["text"] not in {f2["text"] for f2 in extra}]

    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for f in tail:
        by_stratum[f["stratum"]].append(f)

    total_tail = len(tail)
    rng = random.Random(seed)
    drawn: list[dict] = []
    frame = []
    # Largest-remainder apportionment rather than per-stratum rounding, so the
    # sample is exactly the size that was asked for. Rounding each stratum
    # independently loses or gains a row or two, and a frame that promises 200
    # and delivers 199 is a frame someone has to check before trusting.
    allocation = _apportion({k: len(v) for k, v in by_stratum.items()}, sample, total_tail)
    for name in sorted(by_stratum):
        pool = sorted(by_stratum[name], key=lambda f: f["text"])
        take = min(len(pool), allocation.get(name, 0))
        picked = rng.sample(pool, take) if take else []
        weight = (len(pool) / take) if take else 0.0
        for f in picked:
            f = dict(f)
            f["sampling_weight"] = f"{weight:.4f}"
            drawn.append(f)
        frame.append(
            {
                "stratum": name,
                "strings_in_stratum": len(pool),
                "lines_in_stratum": sum(f["lines_settled"] for f in pool),
                "sampled": take,
                "sampling_weight": round(weight, 4),
                "half_width_95pct_points": (round(1.96 * math.sqrt(0.25 / take) * 100, 1) if take else None),
            }
        )

    for f in head:
        f["tranche"] = "census_head"
        f["sampling_weight"] = "1.0"
    for f in extra:
        f["tranche"] = "census_contested"
        f["sampling_weight"] = "1.0"
    for f in drawn:
        f["tranche"] = "sample_tail"

    return {
        "census": head + extra,
        "sample": drawn,
        "frame": frame,
        "at_risk_strings": len(at_risk),
        "at_risk_lines": sum(f["lines_settled"] for f in at_risk),
        "census_lines": sum(f["lines_settled"] for f in head + extra),
        "tail_strings": total_tail,
        "tail_lines": sum(f["lines_settled"] for f in tail),
        "total_strings": len(families),
        "total_lines": sum(f["lines_settled"] for f in families),
        "seed": seed,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(OUT_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**{c: "" for c in OUT_COLUMNS}, **row})


def _readme(result: dict, census: int, sample: int) -> str:
    ar_lines = result["at_risk_lines"] or 1
    covered = result["census_lines"] / ar_lines
    whole_tail = sum(f["sampled"] for f in result["frame"])
    hw = 1.96 * math.sqrt(0.25 / whole_tail) * 100 if whole_tail else float("nan")
    lines = [
        "# Issue #30 — annotation ask",
        "",
        f"Built by `tools/build_annotation_sample.py` v{TOOL_VERSION}. Seed {result['seed']}.",
        "",
        "Fill **`gold_categ`** only: `Clear` / `Noisy` / `Trash` / `Non-text` / `Empty`.",
        "Leave anything uncertain **blank** — blank is skipped, never guessed.",
        "`confidence` and `note` are free text and optional.",
        "",
        "One row is one decision. `lines_settled` is how many lines it settles.",
        "",
        "| file | rows | lines settled | what it is |",
        "|---|---:|---:|---|",
        f"| `census.csv` | {len(result['census'])} | {result['census_lines']:,} | "
        "The head of the at-risk population, plus every string the pipeline "
        "currently answers two ways. Complete, not sampled. |",
        f"| `sample.csv` | {len(result['sample'])} | {result['tail_lines']:,} (represented) | "
        "A random sample of the at-risk tail. Each row carries the weight it "
        "projects at. |",
        "",
        "## What each tranche buys",
        "",
        f"* The queue holds **{result['total_strings']:,} strings / {result['total_lines']:,} lines**.",
        f"* **{result['at_risk_strings']:,} strings / {result['at_risk_lines']:,} lines** are *at risk*: the "
        "pipeline currently keeps them, so arming the witness would newly convict them. "
        "The rest are already `Trash`, where a label cannot change the decision.",
        f"* `census.csv` settles **{covered:.1%}** of at-risk exposure in {len(result['census'])} decisions.",
        f"* `sample.csv` estimates the remainder to **±{hw:.1f} percentage points** (95%), "
        f"from {whole_tail} decisions instead of {result['tail_strings']:,}.",
        "",
        "## Sampling frame — keep this file with the answers",
        "",
        "Without it the sample cannot be projected and becomes 200 anecdotes.",
        "",
        "| stratum | strings | lines | sampled | weight | 95% half-width |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["frame"]:
        hw_s = f"±{row['half_width_95pct_points']} pp" if row["half_width_95pct_points"] else "—"
        lines.append(
            f"| `{row['stratum']}` | {row['strings_in_stratum']:,} | {row['lines_in_stratum']:,} "
            f"| {row['sampled']} | {row['sampling_weight']} | {hw_s} |"
        )
    lines += [
        "",
        "`weight` is how many tail strings each sampled row stands for. A stratum "
        "estimate is (labels of one kind ÷ rows sampled); the population estimate "
        "is the stratum estimates recombined by `lines`, not by `strings` — the "
        "strata have very different average line counts.",
        "",
        f"Settings: `--census {census} --sample {sample} --seed {result['seed']}`.",
        "",
        "Nothing here proposes an answer, and nothing you write changes the "
        "pipeline. The labels are joined back separately and inspected first.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", required=True, metavar="CSV", help="The distinct-string queue.")
    ap.add_argument("--out-dir", required=True, metavar="DIR")
    ap.add_argument("--census", type=int, default=DEFAULT_CENSUS, metavar="N", help="At-risk head to enumerate.")
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE, metavar="N", help="Rows to draw from the tail.")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, metavar="N", help="Recorded in the frame.")
    args = ap.parse_args(argv)

    families = collapse_families(_rows(Path(args.queue)))
    for f in families:
        f["stratum"] = stratum_of(f)
    result = build(families, args.census, args.sample, args.seed)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "census.csv", result["census"])
    _write_csv(out / "sample.csv", result["sample"])
    (out / "frame.json").write_text(json.dumps(result["frame"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "README.md").write_text(_readme(result, args.census, args.sample), encoding="utf-8")

    ar = result["at_risk_lines"] or 1
    print(f"queue: {result['total_strings']:,} strings / {result['total_lines']:,} lines")
    print(f"  at risk (Clear/Noisy today): {result['at_risk_strings']:,} strings / {result['at_risk_lines']:,} lines")
    print(
        f"  already Trash (a label cannot move the decision): {result['total_strings'] - result['at_risk_strings']:,}"
    )
    print()
    print(
        f"census.csv  {len(result['census']):>5} decisions -> {result['census_lines']:>7,} lines ({result['census_lines'] / ar:.1%} of at-risk)"
    )
    drawn = sum(f["sampled"] for f in result["frame"])
    hw = 1.96 * math.sqrt(0.25 / drawn) * 100 if drawn else float("nan")
    print(f"sample.csv  {drawn:>5} decisions -> estimates the remaining {result['tail_lines']:,} lines to ±{hw:.1f} pp")
    print()
    print("  The frame in frame.json is what makes the sample projectable. Keep it")
    print("  with the answers; without it the sample is 200 anecdotes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
