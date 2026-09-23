"""Tests for `tools/ocr_neighbours.py` and the multi-collection lexicon (#30).

The module answers a question neither shape nor attestation can: *is this token
garbage, or a damaged rendering of a real word?* `1 fraament okraie` — 530 lines,
all currently `Trash` — is "1 fragment okraje", which shape reads as noise and
attestation cannot see at all.

Two things are pinned hardest here:

* **The multi-column table must load.** A per-collection table adds columns after
  the total, and the loader used to `int()` everything after the first tab. That
  raises on every data row, so the whole lexicon would vanish with no symptom and
  the veto would go quietly inert.
* **A suggestion is not a correction.** `Linum`/`ilium` and `Lepus`/`lupus` are
  one edit apart and both real Latin. The mechanism label is what separates
  evidence from noise, and collapsing it throws that away.

Frequencies in these fixtures are the real ones from the 822-document table where
a real token is involved, so a fixture that drifts from the corpus is visible.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import text_util as tu  # noqa: E402


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "tools" / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ocr():
    return _load("_ocr", "ocr_neighbours.py")


@pytest.fixture(scope="module")
def btl():
    return _load("_btl_multi", "build_token_lexicon.py")


#: Real document frequencies from the 822-document build. `pole` 163 against
#: `ppole` 35 is the ratio the twin check turns on -- and `ppole` is an
#: abbreviation, not an artefact, which is why a twin is evidence rather than a
#: verdict; `xiii` 87 against `xxiii` 54 is the Roman-numeral pair that must NOT
#: trip it.
REAL_DF = {
    "pole": 163,
    "ppole": 35,
    "fragment": 250,
    "okraje": 350,
    "okraji": 328,
    "objekt": 378,
    "jámy": 356,
    "základní": 234,
    "vrstva": 429,
    "triticum": 39,
    "monococcum": 20,
    "xiii": 87,
    "xxiii": 54,
    "linum": 0,
    "ilium": 22,
}


@pytest.fixture(scope="module")
def nb(ocr):
    return ocr.OCRNeighbours({t: d for t, d in REAL_DF.items() if d}, strong_df=10)


# ---------------------------------------------------------------------------
# The regression that would otherwise be silent
# ---------------------------------------------------------------------------


def test_a_multi_column_table_loads_identically_to_a_two_column_one(tmp_path):
    """Per-collection columns must not empty the lexicon.

    `_read_token_lexicon` partitioned on the first tab and `int()`-ed the rest. On
    `vrstva\\t429\\t120\\t309` that raises `ValueError`, the row is skipped, and
    since EVERY data row has the same shape the table loads as empty — the veto
    inert, the witness unguarded, and nothing anywhere saying so.
    """
    two = tmp_path / "two.tsv"
    two.write_text("# header\nvrstva\t429\nppole\t35\n", encoding="utf-8")
    four = tmp_path / "four.tsv"
    four.write_text(
        "# header\n# columns: token<TAB>document_frequency<TAB>ARUP<TAB>ARUB\nvrstva\t429\t120\t309\nppole\t35\t0\t35\n",
        encoding="utf-8",
    )

    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": str(two), "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        from_two = dict(tu.token_lexicon())
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": str(four), "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        from_four = dict(tu.token_lexicon())

    assert from_two == {"vrstva": 429, "ppole": 35}
    assert from_four == from_two, "the per-collection columns changed what the predicate reads"


def test_a_malformed_row_is_still_skipped_not_fatal(tmp_path):
    """Tolerating extra columns must not tolerate a non-numeric first field."""
    path = tmp_path / "mixed.tsv"
    path.write_text("# h\ngood\t12\t4\t8\nbroken\tnotanumber\t1\nalso_good\t7\n", encoding="utf-8")
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": str(path), "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        lex = dict(tu.token_lexicon())
    assert lex == {"good": 12, "also_good": 7}


# ---------------------------------------------------------------------------
# Multi-collection build
# ---------------------------------------------------------------------------


def _corpus(path: Path, docs: dict[str, list[str]]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    for name, lines in docs.items():
        (path / f"{name}.csv").write_text("text\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_per_collection_counts_sum_to_the_total(btl, tmp_path):
    """Document frequency is the unit and a document has one collection, so totals are sums."""
    a = _corpus(tmp_path / "A", {"d1": ["vrstva nalez"], "d2": ["vrstva keramika"]})
    b = _corpus(tmp_path / "B", {"d3": ["vrstva ppole"], "d4": ["ppole objekt"]})

    total, per, stats = btl.build([("ARUP", a), ("ARUB", b)], min_alpha=4)

    assert stats["documents"] == 4
    for token, count in total.items():
        assert count == per["ARUP"].get(token, 0) + per["ARUB"].get(token, 0), token
    assert total["vrstva"] == 3 and per["ARUP"]["vrstva"] == 2 and per["ARUB"]["vrstva"] == 1
    # The collection-specific shape: present in one collection, absent from the
    # other. A convention (`ppole` is an abbreviation) and an artefact look alike here.
    assert per["ARUP"].get("ppole", 0) == 0 and per["ARUB"]["ppole"] == 2


def test_a_single_unnamed_corpus_still_writes_two_columns(btl, tmp_path):
    """The shipped format must not move. Every existing table and reader depends on it."""
    corpus = _corpus(tmp_path / "solo", {"d1": ["vrstva nalez"], "d2": ["vrstva keramika"]})
    total, per, stats = btl.build([("", corpus)], min_alpha=4)
    out = tmp_path / "solo.tsv"
    btl.write_table(total, out, corpus, stats, min_alpha=4, min_df_note=3, df_by_collection=None)

    body = [ln for ln in out.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
    assert all(ln.count("\t") == 1 for ln in body), "single-corpus output must stay token<TAB>count"
    assert "# columns: token<TAB>document_frequency\n" in out.read_text(encoding="utf-8")


def test_collection_spec_errors_are_reported_not_raised(btl, tmp_path):
    corpus = _corpus(tmp_path / "C", {"d1": ["vrstva"]})
    assert isinstance(btl.parse_collections(["noequals"], None), str)
    assert isinstance(btl.parse_collections([f"A={corpus}", f"A={corpus}"], None), str), "duplicate name"
    assert isinstance(btl.parse_collections(["A=/definitely/not/here"], None), str)
    assert isinstance(btl.parse_collections([], None), str), "nothing given"
    # Mixing a bare path with named collections is ambiguous in the output header.
    assert isinstance(btl.parse_collections([f"A={corpus}"], str(corpus)), str)
    ok = btl.parse_collections([f"A={corpus}"], None)
    assert ok == [("A", corpus)]


# ---------------------------------------------------------------------------
# Neighbours — both mechanisms, and the difference between them
# ---------------------------------------------------------------------------


def test_edit_distance_one_finds_a_single_substitution(nb):
    """`fraament -> fragment`: the case that proved 530 lines are real text."""
    got = nb.nearest_attested("fraament")
    assert got, "no suggestion for a token one edit from a df-250 word"
    assert got[0][0] == "fragment"
    assert got[0][2] == "edit1"


def test_directed_expansion_reaches_what_edit_distance_cannot(nb):
    """Diacritic restoration is the mechanism's reason to exist.

    `zakladni` -> `základní` is THREE edits. No edit-distance-1 index can find it,
    and Czech scanned as ASCII loses every accent at once, so this is the corpus's
    most common transformation rather than an edge case.
    """
    got = nb.nearest_attested("zakladni")
    assert got and got[0][0] == "základní"
    assert got[0][2] == "diacritics"

    # Confirm the claim: it really is out of ED1 range.
    assert "základní" not in nb._ed1_candidates("zakladni")


def test_glyph_confusion_is_labelled_as_such(nb):
    """`okraie -> okraje` is the j/i confusion, not a coincidental neighbour."""
    got = dict((c, m) for c, _, m in nb.nearest_attested("okraie", limit=5))
    assert got.get("okraje") == "confusion"


def test_a_coincidental_neighbour_is_offered_but_not_as_a_correction(nb):
    """`linum` and `ilium` are one edit apart and both real Latin.

    The suggestion is allowed — suppressing it would hide evidence — but it must
    arrive labelled `edit1`, which is the weakest mechanism, and never as
    `diacritics` or `confusion`. A consumer that ignores the label will read a
    coincidence as a correction, which is the failure this labelling prevents.
    """
    got = nb.nearest_attested("linum")
    assert got, "the neighbour exists and hiding it would be worse"
    assert all(m == "edit1" for _, _, m in got), f"a coincidence was labelled as a known confusion: {got}"


def test_an_attested_token_needs_no_recovery(nb):
    assert nb.nearest_attested("vrstva") == []
    assert nb.token_status("vrstva") == "attested"


def test_short_tokens_are_not_queried(nb):
    """At three letters most of a lexicon is within one edit, so a neighbour means nothing."""
    assert nb.nearest_attested("ole") == []


# ---------------------------------------------------------------------------
# The `ppole` case: attested, real, and it still has a stronger twin
# ---------------------------------------------------------------------------


def test_an_attested_abbreviation_still_reports_its_stronger_twin(nb):
    """`ppole` is in the lexicon at 35 because one institution's forms use it.

    It is the abbreviation of *popelnicová pole* (@david-spacil, 2026-09-19), not
    a misread, and an abbreviation's base word is always the commoner of the two
    -- so the twin is reported and it is evidence for a reader, not a verdict.
    `nearest_attested` is silent on it — correctly, it needs no recovery — so
    without `stronger_twin` the single most important row in the queue (11,562
    lines, 57.6% of the population) would carry no evidence at all.
    """
    twin = nb.stronger_twin("ppole")
    assert twin is not None
    assert twin[0] == "pole" and twin[1] == 163


def test_roman_numerals_do_not_trip_the_twin_check(nb):
    """`xxiii` vs `xiii` are different numerals, not a doubling.

    They sit at 54 and 87 — a ratio of 1.6, well under the 4.0 threshold — which
    is why the check is a ratio and not a character rule. `text_util` used to
    rely on the same separation to convict attested tokens; that guard is gone
    (#30 D40) and this tool's own default, declared on `stronger_twin`, is what
    remains of it. Evidence for a reader, not a verdict.
    """
    assert nb.stronger_twin("xxiii") is None


def test_a_word_with_no_twin_reports_none(nb):
    assert nb.stronger_twin("vrstva") is None
    assert nb.stronger_twin("triticum") is None


# ---------------------------------------------------------------------------
# Recoverability
# ---------------------------------------------------------------------------


def test_damaged_real_text_scores_high_and_garbage_scores_zero(nb):
    """The distinction the whole module exists to draw."""
    damaged, detail = nb.recoverability("1 fraament okraie")
    assert damaged == pytest.approx(1.0), detail
    garbage, _ = nb.recoverability("oueussd sektlll")
    assert garbage == 0.0


def test_a_line_with_nothing_queryable_is_no_opinion_not_garbage(nb):
    """Pure notation must not be scored 0 and read as evidence of noise."""
    score, detail = nb.recoverability("II/C 12.")
    assert detail == []
    assert score == 0.0, "the value is 0.0, and the empty detail is what says 'no opinion'"


def test_an_empty_lexicon_is_a_no_op(ocr):
    """No table configured is the shipped state; it must degrade to silence."""
    empty = ocr.OCRNeighbours({}, strong_df=10)
    assert empty.nearest_attested("fraament") == []
    assert empty.stronger_twin("ppole") is None
    assert empty.recoverability("1 fraament okraie")[0] == 0.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _table(tmp_path: Path) -> Path:
    path = tmp_path / "lex.tsv"
    path.write_text(
        "# test table\n" + "".join(f"{t}\t{d}\n" for t, d in REAL_DF.items() if d),
        encoding="utf-8",
    )
    return path


def test_annotate_adds_evidence_without_touching_the_answer_column(ocr, tmp_path):
    """The evidence columns inform; they must never fill `gold_categ`.

    This issue has hit the circularity of measuring its own opinion three times.
    A pre-filled label that gets accepted by default would be the fourth.
    """
    src = tmp_path / "queue.csv"
    src.write_text(
        "text,occurrences,gold_categ\n1 fraament okraie,530,\nppole,11562,\noueussd,1,\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.csv"
    rc = ocr.main(["--lexicon", str(_table(tmp_path)), "--annotate", str(src), "--out", str(out)])
    assert rc == 0

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert all(r["gold_categ"] == "" for r in rows), "the tool wrote an answer"
    by_text = {r["text"]: r for r in rows}
    assert "fragment" in by_text["1 fraament okraie"]["nearest_attested"]
    assert by_text["1 fraament okraie"]["recoverability"] == "1.00"
    assert "pole" in by_text["ppole"]["nearest_attested"], "the stronger twin must be reported"
    assert by_text["oueussd"]["recoverability"] == "0.00"
    assert by_text["oueussd"]["nearest_attested"] == ""


def test_annotate_refuses_a_frame_without_the_text_column(ocr, tmp_path, capsys):
    src = tmp_path / "wrong.csv"
    src.write_text("alpha,beta\n1,2\n", encoding="utf-8")
    rc = ocr.main(["--lexicon", str(_table(tmp_path)), "--annotate", str(src), "--out", str(tmp_path / "o.csv")])
    assert rc == 2
    assert "no 'text' column" in capsys.readouterr().err


def test_an_unreadable_lexicon_fails_loudly(ocr, tmp_path, capsys):
    """Silence here is what the multi-column bug produced; it must be an error instead."""
    bad = tmp_path / "bad.tsv"
    bad.write_text("not a table at all\n", encoding="utf-8")
    rc = ocr.main(["--lexicon", str(bad), "--lookup", "vrstva"])
    assert rc == 2
    assert "no rows" in capsys.readouterr().err


def test_lookup_names_the_mechanism_in_its_output(ocr, tmp_path, capsys):
    rc = ocr.main(["--lexicon", str(_table(tmp_path)), "--lookup", "zakladni", "ppole"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "diacritics" in out
    assert "163x" in out, "the stronger twin must be visible"
    assert "that call is the archive's" in out, "the tool must not imply it decides the category"


# ---------------------------------------------------------------------------
# The annotation pack (#30, 2026-09-19)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pack():
    return _load("_pack", "build_annotation_pack.py")


def _queue(tmp_path: Path) -> Path:
    """A queue with one row per cell of the disagreement cross-tab."""
    path = tmp_path / "queue.csv"
    rows = [
        # Trash + fully recoverable -> tab A, the discarded-text finding
        ("1 fraament okraie", "530", "Trash:530", "fraament -> fragment (6375, edit1)", "1.00"),
        # Clear + no recoverability -> tab B, Dana's concern
        ("sektlll", "543", "Clear:539|Trash:4", "", "0.00"),
        # Clear + recoverable -> tab C, abbreviations and conventions
        ("ppole", "11562", "Clear:11562", "ppole attested 35x but pole is 163x", "1.00"),
        # Trash + none -> tab D, agreement
        ("OOOskart", "104", "Trash:104", "", "0.00"),
        # A variant that must fold into the ppole family rather than open a row
        ("ppole -", "89", "Clear:89", "", "1.00"),
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["text", "occurrences", "categ_current", "nearest_attested", "recoverability"])
        w.writerows(rows)
    return path


def test_the_pack_partitions_by_disagreement(pack, tmp_path):
    """Each cell of the cross-tab lands in its own tab, and nothing is lost."""
    out = tmp_path / "pack"
    assert pack.main(["--queue", str(_queue(tmp_path)), "--out-dir", str(out)]) == 0

    tabs = {p.stem: list(csv.DictReader(p.open(encoding="utf-8"))) for p in out.glob("*.csv")}
    assert set(tabs) == set(pack.TABS)
    texts = {name: {r["text"] for r in rows} for name, rows in tabs.items()}

    assert "1 fraament okraie" in texts["A_discarded_but_recoverable"], "discarded-but-recoverable is tab A"
    assert "sektlll" in texts["B_clear_but_unrecoverable"]
    assert "ppole" in texts["C_clear_and_recoverable"]
    assert "OOOskart" in texts["D_trash_and_unrecoverable"]

    # Every input family appears exactly once across the whole pack.
    seen = [t for s in texts.values() for t in s]
    assert len(seen) == len(set(seen)), "a family landed in two tabs"


def test_variants_fold_into_one_decision(pack, tmp_path):
    """`ppole` and `ppole -` are one judgement covering both, not two rows."""
    out = tmp_path / "pack"
    pack.main(["--queue", str(_queue(tmp_path)), "--out-dir", str(out)])
    rows = list(csv.DictReader((out / "C_clear_and_recoverable.csv").open(encoding="utf-8")))
    ppole = [r for r in rows if r["text"].startswith("ppole")]
    assert len(ppole) == 1, "the variants opened separate rows"
    assert int(ppole[0]["lines_settled"]) == 11562 + 89
    assert "ppole -" in ppole[0]["variants"]


def test_the_pack_never_proposes_an_answer(pack, tmp_path):
    """`gold_categ` empty everywhere.

    Issue #30 has built a circular objective three times. A pre-filled label
    accepted by default would be the fourth, and it would be the hardest to see
    because it would look like agreement.
    """
    out = tmp_path / "pack"
    pack.main(["--queue", str(_queue(tmp_path)), "--out-dir", str(out)])
    for path in out.glob("*.csv"):
        for row in csv.DictReader(path.open(encoding="utf-8")):
            assert row.get("gold_categ", "") == "", f"{path.name} proposed an answer"


def test_categ_current_is_hidden_except_where_it_is_the_question(pack, tmp_path):
    """Showing the pipeline's answer to the person checking it biases agreement.

    Tab B is the exception, and so is any string the pipeline labelled two ways --
    there the disagreement is what is being adjudicated.
    """
    out = tmp_path / "pack"
    pack.main(["--queue", str(_queue(tmp_path)), "--out-dir", str(out)])

    b_rows = list(csv.DictReader((out / "B_clear_but_unrecoverable.csv").open(encoding="utf-8")))
    assert any(r.get("categ_current") for r in b_rows), "tab B must show the split it is asking about"

    a_rows = list(csv.DictReader((out / "A_discarded_but_recoverable.csv").open(encoding="utf-8")))
    assert all(not r.get("categ_current") for r in a_rows), "tab A leaked the pipeline's answer"


def test_a_queue_without_evidence_columns_is_refused(pack, tmp_path, capsys):
    """Without the evidence this tool would be sorting rows by nothing."""
    bare = tmp_path / "bare.csv"
    bare.write_text("text,occurrences\nfoo,1\n", encoding="utf-8")
    rc = pack.main(["--queue", str(bare), "--out-dir", str(tmp_path / "p")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "ocr_neighbours.py --annotate" in err, "the refusal must name the fix"


def test_the_readme_states_the_asymmetry(pack, tmp_path):
    """The archivist-facing text must not let a zero read as a verdict."""
    out = tmp_path / "pack"
    pack.main(["--queue", str(_queue(tmp_path)), "--out-dir", str(out)])
    # Collapse wrapping: the sentence spans a line break in the rendered file.
    readme = " ".join((out / "README.md").read_text(encoding="utf-8").split())
    assert "Zero means only that this corpus has nothing to say" in readme
    assert "Schuhleistenkeilbruchstueck" in readme
    assert "popelnicová pole" in readme, "the ppole correction has to reach the reader"
