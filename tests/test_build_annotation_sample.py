"""
tests/test_build_annotation_sample.py
=====================================
``tools/build_annotation_sample.py`` (issue #30, H3).

Why these tests exist
---------------------
The tool's whole value is that its output can be PROJECTED. A census tranche
that silently drops a row, or a sample whose frame does not describe the draw
that actually happened, produces a number that looks like an estimate and is an
anecdote. That failure is invisible from the output -- which is the exact shape
of the six instrument-level errors this issue has already logged -- so it has to
be pinned here rather than noticed later.

The properties that matter, in order:

1. the census is COMPLETE for what it claims to cover, and contains every
   self-contradictory family whatever its size;
2. the sample is exactly the size the frame says, drawn from exactly the
   population the frame describes, reproducibly from the seed;
3. no row is in both tranches, and no ``gold_categ`` is ever pre-filled.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.build_annotation_sample import (  # noqa: E402
    _apportion,
    build,
    collapse_families,
    main,
    stratum_of,
)

QUEUE_COLUMNS = ("text", "occurrences", "word_count", "clauses", "categ_current", "recoverability")


def _queue(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "queue.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(QUEUE_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({**{c: "" for c in QUEUE_COLUMNS}, **row})
    return path


def _name(prefix: str, i: int) -> str:
    """A distinct family key per row.

    `family_key` strips leading and trailing digits -- deliberately, so `1 ks`
    and `ks 1` are one decision -- so `s0`..`s19` would collapse into ONE family
    and every count below would be 1. Alphabetic suffixes keep them distinct.
    """
    letters = "abcdefghijklmnopqrstuvwxyz"
    return f"{prefix}{letters[i // 26]}{letters[i % 26]}"


def _row(text, occurrences, categ, recoverability="1.00", clauses="vowel_run"):
    return {
        "text": text,
        "occurrences": str(occurrences),
        "word_count": "1",
        "clauses": clauses,
        "categ_current": categ,
        "recoverability": recoverability,
    }


def _families(rows):
    families = collapse_families(rows)
    for f in families:
        f["stratum"] = stratum_of(f)
    return families


# ---------------------------------------------------------------------------
# The unit of decision
# ---------------------------------------------------------------------------


def test_spelling_variants_collapse_into_one_decision(tmp_path):
    """`ppole`, `ppole -` and `ppole?` are one judgement about one form label."""
    rows = [
        _row("ppole", 11562, "Clear:11562"),
        _row("ppole -", 89, "Clear:89"),
        _row("ppole?", 20, "Clear:20"),
    ]
    families = collapse_families(rows)
    assert len(families) == 1
    assert families[0]["lines_settled"] == 11671, "a family's value is the sum of its variants"
    assert families[0]["variants"].count("|") == 2, "the variants stay visible — the pattern is evidence"


def test_the_merged_category_mix_sums_across_variants(tmp_path):
    rows = [_row("x", 10, "Clear:8|Trash:2"), _row("x -", 5, "Trash:5")]
    (family,) = collapse_families(rows)
    assert family["categ_current"] == "Trash:7|Clear:8" or family["categ_current"] == "Clear:8|Trash:7"
    assert family["lines_settled"] == 15


# ---------------------------------------------------------------------------
# What a label can and cannot change
# ---------------------------------------------------------------------------


def test_already_trash_families_are_not_at_risk():
    """A label on a line the pipeline already discards cannot move the flag.

    That is the whole reason this tool exists: raw frequency order spends most
    of an archivist's budget re-confirming `Trash`.
    """
    assert stratum_of({"categ_current": "Clear:10", "recoverability": "1.00"}).startswith("at_risk")
    assert stratum_of({"categ_current": "Noisy:10", "recoverability": "0.00"}).startswith("at_risk")
    assert stratum_of({"categ_current": "Trash:10", "recoverability": "1.00"}).startswith("confirms_trash")
    # Mixed rows go by the majority, the same rule build_annotation_pack uses.
    assert stratum_of({"categ_current": "Trash:40|Clear:22", "recoverability": ""}).startswith("confirms_trash")


# ---------------------------------------------------------------------------
# The census
# ---------------------------------------------------------------------------


def test_every_self_contradictory_family_joins_the_census_whatever_its_size():
    """The pipeline giving identical text two answers is the highest value per decision.

    A two-line contradiction would never survive a frequency cut, and it is
    exactly the kind of row the issue's H4 asks for.
    """
    rows = [_row(_name("big", i), 100 - i, "Clear:1") for i in range(5)]
    rows.append(_row("tiny", 2, "Clear:1|Trash:1"))
    result = build(_families(rows), census=3, sample=0, seed=30)

    census_texts = {f["text"] for f in result["census"]}
    assert "tiny" in census_texts
    assert {f["tranche"] for f in result["census"]} == {"census_head", "census_contested"}


def test_the_census_is_never_sampled():
    rows = [_row(_name("s", i), 50 - i, "Clear:1") for i in range(20)]
    result = build(_families(rows), census=8, sample=5, seed=30)
    head = [f for f in result["census"] if f["tranche"] == "census_head"]
    assert len(head) == 8
    assert all(f["sampling_weight"] == "1.0" for f in result["census"]), (
        "a census row stands for itself; a weight other than 1 would double-count it"
    )


# ---------------------------------------------------------------------------
# The sample, and the frame that makes it projectable
# ---------------------------------------------------------------------------


def test_the_sample_is_exactly_the_size_the_frame_promises():
    """Largest-remainder apportionment, not per-stratum rounding.

    A frame that promises 200 and delivers 199 is a frame someone has to check
    before trusting, and the point of writing one is that nobody should have to.
    """
    rows = [_row(_name("a", i), 1, "Clear:1", recoverability="1.00") for i in range(300)]
    rows += [_row(_name("b", i), 1, "Clear:1", recoverability="0.00") for i in range(200)]
    rows += [_row(_name("c", i), 1, "Clear:1", recoverability="0.50") for i in range(111)]

    result = build(_families(rows), census=10, sample=200, seed=30)
    assert len(result["sample"]) == 200
    assert sum(f["sampled"] for f in result["frame"]) == 200


def test_the_frame_describes_the_draw_that_actually_happened():
    rows = [_row(_name("a", i), 1, "Clear:1", recoverability="1.00") for i in range(120)]
    rows += [_row(_name("b", i), 1, "Clear:1", recoverability="0.00") for i in range(80)]
    result = build(_families(rows), census=10, sample=50, seed=30)

    drawn_per_stratum: dict[str, int] = {}
    for f in result["sample"]:
        drawn_per_stratum[f["stratum"]] = drawn_per_stratum.get(f["stratum"], 0) + 1
    for row in result["frame"]:
        assert drawn_per_stratum.get(row["stratum"], 0) == row["sampled"]
        if row["sampled"]:
            # `sampling_weight` is rounded to 4 places in the frame for readability.
            assert abs(row["sampling_weight"] - row["strings_in_stratum"] / row["sampled"]) < 1e-4


def test_the_weight_recovers_the_stratum_size():
    """The projection has to be arithmetic, not a second judgement call."""
    rows = [_row(_name("a", i), 1, "Clear:1") for i in range(200)]
    result = build(_families(rows), census=10, sample=40, seed=30)
    recovered = sum(float(f["sampling_weight"]) for f in result["sample"])
    assert abs(recovered - result["tail_strings"]) < 1.0


def test_the_draw_is_reproducible_from_the_seed_and_only_from_it():
    rows = [_row(_name("a", i), 1, "Clear:1") for i in range(200)]
    families = _families(rows)
    same = build(families, census=5, sample=30, seed=30)
    again = build(_families(rows), census=5, sample=30, seed=30)
    different = build(_families(rows), census=5, sample=30, seed=31)

    assert [f["text"] for f in same["sample"]] == [f["text"] for f in again["sample"]]
    assert [f["text"] for f in same["sample"]] != [f["text"] for f in different["sample"]]


def test_apportion_never_exceeds_a_stratum_and_always_sums():
    sizes = {"a": 3, "b": 100, "c": 7}
    alloc = _apportion(sizes, 40, sum(sizes.values()))
    assert sum(alloc.values()) == 40
    assert all(alloc[k] <= sizes[k] for k in sizes)

    # Asking for more than exists gives everything and stops, rather than looping.
    alloc = _apportion(sizes, 500, sum(sizes.values()))
    assert alloc == sizes


# ---------------------------------------------------------------------------
# Contract with the annotator
# ---------------------------------------------------------------------------


def test_nothing_is_pre_filled_and_no_row_appears_twice(tmp_path):
    rows = [_row(_name("s", i), 60 - i, "Clear:1") for i in range(40)]
    rows.append(_row("split", 3, "Clear:2|Trash:1"))
    queue = _queue(tmp_path, rows)
    out = tmp_path / "ask"

    assert main(["--queue", str(queue), "--out-dir", str(out), "--census", "5", "--sample", "10"]) == 0

    census = list(csv.DictReader((out / "census.csv").open(encoding="utf-8")))
    sample = list(csv.DictReader((out / "sample.csv").open(encoding="utf-8")))

    assert census and sample
    for row in census + sample:
        assert row["gold_categ"] == "", "a queue that proposes answers is a queue that gets agreed with"
        assert row["confidence"] == ""
        assert row["note"] == ""

    overlap = {r["text"] for r in census} & {r["text"] for r in sample}
    assert not overlap, f"a family in both tranches would be counted twice: {overlap}"


def test_the_frame_and_readme_are_written_beside_the_csvs(tmp_path):
    rows = [_row(_name("s", i), 20 - i, "Clear:1") for i in range(15)]
    out = tmp_path / "ask"
    main(["--queue", str(_queue(tmp_path, rows)), "--out-dir", str(out), "--census", "3", "--sample", "5"])

    frame = json.loads((out / "frame.json").read_text(encoding="utf-8"))
    assert frame and all({"stratum", "strings_in_stratum", "sampled", "sampling_weight"} <= set(r) for r in frame)

    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "gold_categ" in readme
    assert "Sampling frame" in readme
    assert "--seed 30" in readme, "the seed has to be recoverable from the delivered files alone"


def test_a_queue_missing_a_required_column_fails_loudly(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("text,occurrences\nfoo,1\n", encoding="utf-8")
    try:
        main(["--queue", str(path), "--out-dir", str(tmp_path / "out")])
    except SystemExit as exc:
        assert "categ_current" in str(exc)
    else:  # pragma: no cover - the tool must not silently produce an empty ask
        raise AssertionError("a queue without categ_current must not produce an ask")
