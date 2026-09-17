"""
tests/test_shape_witness_vocabulary.py
======================================
The two things issue #30 left open about ``_has_shape_garbage_evidence()``:
the loan false-positive class that gates the flag, and the lexical signal for
the residue (D14).

Why this file exists
--------------------
The design block above the predicate named its own weak point and then did not
close it:

    "KNOWN false positives of the vowel-run clause: Latin/French/German loans
     with a 3+ vowel run (`Poaceae`, `Naiade`, ...). Most carry weird_ratio 0.0
     and so never reach the route at all -- a real but THIN margin, since it
     depends on a signal outside this predicate. Measuring that class against
     annotated lines is a precondition for enabling the flag, not a follow-up."

``agent_dev_logs/plans/30.plan.md`` carried it for a month as "still a stated
precondition for flipping the flag, still unmeasured". Measured, it fails, and
not marginally: ``-aceae`` is the botanical FAMILY suffix, so the vowel-run
clause did not make an occasional mistake on this class -- it convicted all of
it, in a corpus whose archaeobotany reports are where that class lives.

The margin the block relies on is a signal this predicate does not own. These
tests pin the predicate's own behaviour instead, which is the thing a future
change can break without noticing.

Every test here is pure text. No model, no corpus, no GPU -- which is the point:
the class that gated this flag was always measurable, and nothing about it
needed the delivered batch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import text_util as tu  # noqa: E402
from text_util import _has_shape_garbage_evidence, shape_garbage_clauses  # noqa: E402

# ---------------------------------------------------------------------------
# Populations
# ---------------------------------------------------------------------------

#: Botanical family names. Every one ends in the family suffix `-aceae`, which is
#: why this class is systematic rather than anecdotal: the suffix carries the
#: `eae` vowel run, so before the exemption the clause convicted the naming
#: convention itself. Measured 2026-09-17 on the shipped predicate: 10 of 10.
BOTANICAL_FAMILIES = [
    "Poaceae",
    "Rosaceae",
    "Fabaceae",
    "Brassicaceae",
    "Cyperaceae",
    "Chenopodiaceae",
    "Asteraceae",
    "Betulaceae",
    "Fagaceae",
    "Polygonaceae",
]

#: Binomials, genera and osteological terms from the #30 thread and from the
#: report classes Dana reviewed. These already passed before the exemption; they
#: are here so a future widening of any clause has to break a named line.
TAXONOMIC_VOCABULARY = [
    "Equus caballus",
    "Canis familiaris",
    "Pinus silvestris",
    "Unio crassus",
    "Corylus avellana",
    "Triticum aestivum",
    "Capreolus capreolus",
    "Cervus elaphus",
    "Occipitale",
    "Phalanx proximalis",
    "Maxilla+dentes",
    "Ossa tarsi",
    "radius prox.sin.",
]

#: The loans the SUFFIX rule deliberately does not reach: name-shaped rather than
#: suffixed. They are the vocabulary half of the D14 case -- the reason a lexical
#: signal is needed at all, rather than one more orthographic rule.
UNSUFFIXED_LOANS = ["Naiade", "Beuern", "Oueste"]

#: Garbage the witness must keep convicting. An exemption that buys a false
#: positive back by giving up a true one is not a narrowing, it is a retreat.
MUST_STILL_CONVICT = [
    "oueussd",
    "sektlll",
    "cuxoaid",
    "rragment",
    "vansasaasasa",
    "NINNNIC",
    "Tthts I",
    "IDIDIDIDIDIDUOID",
    "lllll",
]

#: Phonotactically legal garbage. Out of reach of every SHAPE clause by
#: construction -- that is the residue D14 is about.
RESIDUE = ["edelite", "vfetennl k.", "zcv7"]


def _table(tmp_path: Path, rows: dict[str, int]) -> str:
    """Write a token/document-frequency table in build_token_lexicon.py's format."""
    path = tmp_path / "token_df.tsv"
    body = "# synthetic table for tests\n" + "".join(f"{t}\t{n}\n" for t, n in rows.items())
    path.write_text(body, encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# The precondition that gated the flag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", BOTANICAL_FAMILIES)
def test_botanical_family_names_are_not_witnessed(name):
    """The `-aceae` class, which the predicate convicted 10 of 10 before the exemption.

    This is the "loan false-positive class" the plan recorded as a precondition
    for enabling `SHORT_GARBAGE_WITNESS_ENABLE`. With the flag on and without the
    exemption, every botanical family name in an archaeobotanical report would
    route to Trash on a single clause.
    """
    assert _has_shape_garbage_evidence(name) is False, (
        f"{name!r} is witnessed as garbage: {shape_garbage_clauses(name)}. "
        "This is the Latin family suffix, not a rare spelling."
    )


@pytest.mark.parametrize("text", TAXONOMIC_VOCABULARY)
def test_taxonomic_and_osteological_vocabulary_is_not_witnessed(text):
    assert _has_shape_garbage_evidence(text) is False, f"{text!r}: {shape_garbage_clauses(text)}"


def test_the_exemption_is_a_suffix_rule_not_a_latin_amnesty():
    """`-aceae` is exempt; a token that merely looks Latinate is not.

    The exemption has to stay narrow enough that it cannot be reached by
    accident. `oueussd` and `cuxoaid` are not Latin and must not become exempt
    because some future edit widens the pattern.
    """
    assert tu._RE_TAXONOMIC_SUFFIX.search("poaceae")
    assert tu._RE_TAXONOMIC_SUFFIX.search("rosoideae")
    assert not tu._RE_TAXONOMIC_SUFFIX.search("oueussd")
    assert not tu._RE_TAXONOMIC_SUFFIX.search("cuxoaid")
    # Length floor: a short token ending in the pattern is a coincidence.
    assert tu._TAXONOMIC_SUFFIX_MIN_ALPHA >= 5


@pytest.mark.parametrize("text", MUST_STILL_CONVICT)
def test_the_exemptions_cost_no_conviction(text):
    """Every named garbage line still fires at least one clause.

    Measured together with the exemption rather than after it: 0 convictions lost
    across this list. An exemption that traded one of these away would be moving
    the error, not removing it.
    """
    assert _has_shape_garbage_evidence(text) is True, f"{text!r} stopped being witnessed"


# ---------------------------------------------------------------------------
# The vowel-run knob
# ---------------------------------------------------------------------------


def test_vowel_run_minimum_is_decoupled_from_fused_vowel_run_min():
    """The witness must be tunable without moving the quality score.

    `_RE_FUSED_VOWEL_RUN` feeds `detect_fused_words()`, which feeds `fused_ratio`
    in `compute_quality_score` and the `fused_words` CSV column. While the witness
    shared that constant, the only clause that discriminates on the #30 population
    could not be tuned without changing scores on every line in the corpus.
    """
    assert tu.SHORT_GARBAGE_WITNESS_VOWEL_RUN_MIN == tu.FUSED_VOWEL_RUN_MIN, (
        "the shipped default must reproduce the previous behaviour exactly"
    )
    # And it must actually steer the clause, not merely exist.
    assert tu._compile_vowel_run(3).search("oai")
    assert not tu._compile_vowel_run(4).search("oai")
    assert tu._compile_vowel_run(4).search("oueu")


def test_raising_the_vowel_run_is_a_measured_trade_in_both_directions():
    """Pins the trade at 4 so it is a decision, not a surprise.

    Documented in the clause and in setup/config.txt: `oueussd` survives, the
    unsuffixed loans stop firing, and `cuxoaid` escapes with no other clause
    catching it. Whoever raises this constant should be raising it against gold
    with this cost in view.
    """
    with tu.override_constants({"SHORT_GARBAGE_WITNESS_VOWEL_RUN_MIN": 4}):
        assert _has_shape_garbage_evidence("oueussd") is True
        assert _has_shape_garbage_evidence("cuxoaid") is False, "the cost side of the trade moved"
        for loan in UNSUFFIXED_LOANS:
            assert _has_shape_garbage_evidence(loan) is False


# ---------------------------------------------------------------------------
# D14: the vocabulary signal
# ---------------------------------------------------------------------------


def test_lexicon_is_inert_when_no_table_is_configured():
    """The shipped state. With no table the predicate is the shape-only predicate."""
    assert tu.SHORT_GARBAGE_LEXICON_PATH == ""
    assert tu.token_lexicon() == frozenset()
    assert tu.SHORT_GARBAGE_LEXICON_CONVICT is False
    for text in MUST_STILL_CONVICT:
        assert _has_shape_garbage_evidence(text) is True
    for text in RESIDUE:
        assert _has_shape_garbage_evidence(text) is False, (
            "with no lexicon the residue must remain out of reach — that is the "
            "documented limit this table is what changes"
        )


def test_attested_vocabulary_vetoes_the_unsuffixed_loans(tmp_path):
    """The half the suffix rule deliberately leaves alone.

    `Naiade`, `Beuern` and `Oueste` are name-shaped, so no suffix rule reaches
    them and inventing a legal-vowel-sequence list to do it is the guessing that
    cost twelve lines the last time this predicate was widened by reading rather
    than measuring. Attestation reaches them without anyone deciding which vowel
    sequences a European language may contain.
    """
    path = _table(tmp_path, {"naiade": 14, "beuern": 9, "oueste": 5, "oueussd": 1, "sektlll": 2})
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": path, "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        for loan in UNSUFFIXED_LOANS:
            assert _has_shape_garbage_evidence(loan) is False, f"{loan!r} was attested and still convicted"
        # Below the threshold is not attested: one document is what OCR noise looks like.
        assert _has_shape_garbage_evidence("oueussd") is True
        assert _has_shape_garbage_evidence("sektlll") is True


def test_the_veto_is_a_veto_and_never_adds_a_conviction(tmp_path):
    """Presence in the table can only remove a clause, never introduce one."""
    path = _table(tmp_path, {"kaaden": 40, "pinii": 12})
    before = {t: shape_garbage_clauses(t) for t in MUST_STILL_CONVICT + BOTANICAL_FAMILIES + RESIDUE}
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": path, "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        after = {t: shape_garbage_clauses(t) for t in MUST_STILL_CONVICT + BOTANICAL_FAMILIES + RESIDUE}
    for text, clauses in after.items():
        assert set(clauses) <= set(before[text]), f"{text!r} gained a clause from a veto-only table"


def test_unattested_conviction_reaches_the_residue_and_ships_off(tmp_path):
    """D14, the part no character-level rule can do.

    `edelite` and `vfetennl k.` are spelled the way words are spelled. The only
    property that separates them from `malakofauna` is that nothing else in the
    collection contains them. This is the one clause of the witness that can ADD
    a conviction, so it carries its own key and that key ships false.
    """
    path = _table(
        tmp_path,
        {
            "malakofauna": 31,
            "diapozitiv": 22,
            "occipitale": 17,
            "equus": 40,
            "caballus": 38,
            "kaaden": 8,
            "vrstva": 900,
        },
    )
    overrides = {"SHORT_GARBAGE_LEXICON_PATH": path, "SHORT_GARBAGE_LEXICON_MIN_DF": 3}

    # Table loaded, conviction OFF — the residue is still out of reach.
    with tu.override_constants(overrides):
        assert tu.SHORT_GARBAGE_LEXICON_CONVICT is False
        for text in RESIDUE:
            assert _has_shape_garbage_evidence(text) is False

    # Conviction ON — the residue is reached, and vocabulary survives.
    with tu.override_constants({**overrides, "SHORT_GARBAGE_LEXICON_CONVICT": True}):
        assert "no_vocabulary" in shape_garbage_clauses("edelite")
        assert "no_vocabulary" in shape_garbage_clauses("vfetennl k.")
        for text in ["malakofauna", "diapozitiv", "Equus caballus", "Occipitale", "Kaaden", "vrstva"]:
            assert _has_shape_garbage_evidence(text) is False, (
                f"{text!r} is attested and must survive the unattested-conviction clause"
            )


def test_unattested_conviction_cannot_fire_without_a_table(tmp_path):
    """Belt and braces: the flag alone must not turn every token into garbage.

    Without a table `token_lexicon()` is empty, so "unattested" would be true of
    everything. The clause checks for a loaded table first; this pins that it
    does, because the failure mode is the entire corpus routing to Trash.
    """
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_CONVICT": True}):
        assert tu.token_lexicon() == frozenset()
        for text in ["malakofauna", "Equus caballus", "vrstva", "Poaceae"]:
            assert _has_shape_garbage_evidence(text) is False


def test_a_corrupt_table_degrades_to_no_signal_rather_than_raising(tmp_path):
    """This predicate runs per sub-token inside the categoriser.

    An optional, operator-supplied file that raises would take a multi-hour
    corpus run down at whatever line it reached. It must degrade to "no
    vocabulary signal" instead.
    """
    bad = tmp_path / "broken.tsv"
    bad.write_bytes(b"\xff\xfe not a table at all\n\x00\x00")
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": str(bad)}):
        assert _has_shape_garbage_evidence("oueussd") is True
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": str(tmp_path / "does_not_exist.tsv")}):
        assert tu.token_lexicon() == frozenset()
        assert _has_shape_garbage_evidence("oueussd") is True


def test_min_df_is_honoured_rather_than_assumed(tmp_path):
    path = _table(tmp_path, {"naiade": 2})
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": path, "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        assert _has_shape_garbage_evidence("Naiade") is True, "df 2 is below the threshold of 3"
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": path, "SHORT_GARBAGE_LEXICON_MIN_DF": 2}):
        assert _has_shape_garbage_evidence("Naiade") is False


# ---------------------------------------------------------------------------
# The builder must tokenise the way the predicate looks up
# ---------------------------------------------------------------------------


def test_builder_tokenisation_matches_the_predicate_lookup():
    """The failure this prevents is silent and one-directional.

    If the table is keyed differently from the way the predicate looks tokens up,
    every lookup misses, which reads as "no vocabulary support" — i.e. as a
    witness that convicts MORE. That is the direction that costs real lines, and
    nothing in the output would say so. Four harness divergences in this
    repository came from a tool carrying its own copy of text_util logic; the
    builder imports `_split_subtokens` and `_STRIP_CHARS` for that reason.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("_btl", _ROOT / "tools" / "build_token_lexicon.py")
    btl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(btl)

    for line in ["radius prox.sin.", "Reg.Bez.Aussig.", "Equus caballus", "Sonda VIII/3", "0,2-0,4 m"]:
        built = list(btl.iter_tokens(line))
        # The predicate's own path, reproduced from the same helpers.
        expected = [
            core.lower()
            for word in line.split()
            for sub in tu._split_subtokens(word)
            if (core := sub.strip(tu._STRIP_CHARS))
        ]
        assert built == expected, f"{line!r}: builder {built} != predicate {expected}"


# ---------------------------------------------------------------------------
# Table format: a token that looks like a comment
# ---------------------------------------------------------------------------


def test_a_token_beginning_with_hash_is_data_not_a_comment(tmp_path):
    """Found in the real 822-document table: 27 tokens start with `#`.

    `#` is not in `_STRIP_CHARS`, so the builder emits tokens like `#rdisico` and
    `#žkami` verbatim — and the reader skipped every line starting with `#` as a
    provenance comment, dropping them at load. Nothing said so.

    Impact on the delivered table is nil: all 27 are df 1, below any threshold,
    and all garbage. It is fixed because it is the same silent-drop shape as the
    rest of this issue — the file says one thing, the loader reads another, and
    the only symptom is a number that is quietly slightly wrong.

    The format needs no escaping to tell them apart: a header line has no TAB
    (`# columns: token<TAB>document_frequency` is literal text), a data line
    always does.
    """
    path = tmp_path / "token_df.tsv"
    path.write_text(
        "# token document-frequency table — provenance header\n"
        "# columns: token<TAB>document_frequency\n"
        "#rdisico\t40\n"
        "ordinary\t40\n",
        encoding="utf-8",
    )
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": str(path), "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        lex = tu.token_lexicon()

    assert "#rdisico" in lex, "a token that merely looks like a comment was dropped"
    assert "ordinary" in lex
    assert not any(t.startswith("# ") for t in lex), "header lines leaked in as tokens"
    assert len(lex) == 2


def test_header_lines_are_still_skipped(tmp_path):
    """The other half of the same contract — the fix must not admit the header."""
    path = tmp_path / "token_df.tsv"
    path.write_text(
        "# built: 2026-09-17T11:36:51+00:00\n# documents: 822  lines: 12716706\nordinary\t5\n",
        encoding="utf-8",
    )
    with tu.override_constants({"SHORT_GARBAGE_LEXICON_PATH": str(path), "SHORT_GARBAGE_LEXICON_MIN_DF": 3}):
        assert tu.token_lexicon() == frozenset({"ordinary"})


# ---------------------------------------------------------------------------
# The coupling between the two flags
# ---------------------------------------------------------------------------


def test_the_witness_without_a_lexicon_is_reported_as_a_known_bad_configuration():
    """Measured on the cluster, and it is the single most consequential setting here.

    Over 1,480,119 in-scope lines the shape witness alone confirms 5,107 existing
    `Trash` verdicts and newly convicts **15,217** lines the pipeline currently
    calls `Clear` or `Noisy` — 1 : 3 against. With the vocabulary veto at
    `min_df` 3 the same witness scores 3,905 against 2,306, i.e. 1.7 : 1 in
    favour. The veto is not a refinement of the witness; it is the difference
    between arming it and not.

    Advisory rather than a gate: stage 5a of the runbook deliberately measures the
    shape-only configuration, and refusing it would make that measurement
    impossible. But nobody should reach it by accident.
    """
    assert tu.uncoupled_witness_warning(witness_enabled=True, lexicon_path="") is not None
    assert tu.uncoupled_witness_warning(witness_enabled=True, lexicon_path="   ") is not None
    # Both other combinations are fine, including the shipped one.
    assert tu.uncoupled_witness_warning(witness_enabled=False, lexicon_path="") is None
    assert tu.uncoupled_witness_warning(witness_enabled=True, lexicon_path="tools/gold/token_df.tsv") is None
    assert tu.uncoupled_witness_warning(witness_enabled=False, lexicon_path="tools/gold/token_df.tsv") is None


def test_the_shipped_configuration_raises_no_advisory():
    assert tu.uncoupled_witness_warning() is None
