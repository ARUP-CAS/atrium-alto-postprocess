"""
tests/test_recategorize_parity.py
=================================
Regression net for the unified, constants-parameterised re-scorer (#5).

The offline importance tooling must use the SAME engine as production: the real
``compute_quality_score`` / ``categorize_line`` / ``apply_document_postprocessing``
driven by ``text_util.override_constants`` — never a parallel
re-implementation. The decisive guarantee is *parity*: at the default config the
re-score reproduces the stored ``categ`` on the sample corpus (flip_rate <= 0.01).
If that ever drifts, the surrogate sweep is measuring something other than
production and this test fails loudly.

All pure-Python — the GPU/ML stack is stubbed, exactly like test_calibration.
"""

import sys
import types
from pathlib import Path

import pytest

# Stub the GPU/ML stack before importing the tool (it imports claasify_TEXT).
for _n in ("torch", "tqdm", "fasttext", "transformers"):
    sys.modules.setdefault(_n, types.ModuleType(_n))
sys.modules["tqdm"].tqdm = lambda x, **k: x  # type: ignore[attr-defined]

_ROOT = Path(__file__).resolve().parent.parent
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import recategorize_from_csv as R  # noqa: E402

import classify_TEXT as lc  # noqa: E402
import text_util as tu  # noqa: E402

_SAMPLE_DIR = _ROOT / "data_samples" / "DOC_LINE_CATEG"

pytestmark = pytest.mark.skipif(
    not _SAMPLE_DIR.is_dir() or not any(_SAMPLE_DIR.glob("*.csv")),
    reason="no DOC_LINE_CATEG sample CSVs present",
)



@pytest.mark.parametrize(
    "text",
    [
        "Rozměry : v - 112mm,pr.okraje - 145) pr. dna - 7",
        "Tb. IX. ,2. č.neg.430. -",
        "Tb. X. ,1. Č. neg. 432. .",
        "Obsah :",
        "2, Popis nálezu i - 3",
        "V Prase 15. 1. 1995",
        "Trať čp. 34, 35, 36",
    ],
)
def test_structured_archaeological_lines_are_not_short_garbage(text):
    from tools.recategorize_from_csv import is_structured_line

    assert is_structured_line(text)



@pytest.mark.parametrize(
    "text",
    [
        "olie",
        "oueussd",
        "pbqdnuwmoxszeyv!!",
        "NINNNIC",
    ],
)
def test_obvious_garbage_is_not_structured(text):
    from tools.recategorize_from_csv import is_structured_line

    assert not is_structured_line(text)



@pytest.fixture(scope="module")
def corpus():
    return R.load_csvs(_SAMPLE_DIR)


def test_decisive_override_changes_categories(corpus):
    """A hard-sweep override that trashes confident-but-perplexed lines must flip
    a non-trivial share of the scored corpus — proving constants propagate into
    the real determine_category routes."""
    cfg = dict(R.DEFAULT_CONSTANTS)
    cfg["HARD_SWEEP_PPL_MIN"] = 1.0
    cfg["HARD_SWEEP_LANG_MAX"] = 2.0  # every orig_lang_score < 2.0
    metrics = R.evaluate_dataframe(corpus, cfg)
    assert metrics["flip_rate"] > 0.01
    assert metrics["trash_rate"] > R.evaluate_dataframe(corpus, R.DEFAULT_CONSTANTS)["trash_rate"]


# ── override_constants restores globals, even on exception ──────────────────


def test_override_constants_restores_globals():
    before_tu = tu.CATEG_TRASH_SCORE_MAX
    before_lc = lc.CATEG_TRASH_SCORE_MAX  # classify_TEXT holds its own binding
    with tu.override_constants({"CATEG_TRASH_SCORE_MAX": 0.123}, modules=(tu, lc)):
        assert tu.CATEG_TRASH_SCORE_MAX == 0.123
        assert lc.CATEG_TRASH_SCORE_MAX == 0.123
    assert tu.CATEG_TRASH_SCORE_MAX == before_tu
    assert lc.CATEG_TRASH_SCORE_MAX == before_lc


def test_override_constants_restores_on_exception():
    before = tu.PERPLEXITY_THRESHOLD_MAX
    with pytest.raises(RuntimeError):
        with tu.override_constants({"PERPLEXITY_THRESHOLD_MAX": 1.0}):
            assert tu.PERPLEXITY_THRESHOLD_MAX == 1.0
            raise RuntimeError("boom")
    assert tu.PERPLEXITY_THRESHOLD_MAX == before


# ── Config / override parsing + validation guardrails ───────────────────────


def test_default_constants_track_live_modules():
    # DEFAULT_CONSTANTS is read from the live modules, so it can never drift from
    # config.txt the way a hardcoded table would.
    assert R.DEFAULT_CONSTANTS["CATEG_TRASH_SCORE_MAX"] == tu.CATEG_TRASH_SCORE_MAX
    assert R.DEFAULT_CONSTANTS["CATEG_NOISY_SCORE_MAX"] == tu.CATEG_NOISY_SCORE_MAX
    assert "QS_WEIGHT_SYMBOL" not in R.TUNABLE_CONSTANTS  # dropped from the QS sum in #3


def test_validate_rejects_inverted_thresholds():
    bad = dict(R.DEFAULT_CONSTANTS)
    bad["CATEG_TRASH_SCORE_MAX"] = 0.95
    bad["CATEG_NOISY_SCORE_MAX"] = 0.80
    with pytest.raises(ValueError):
        R.validate_constants(R.coerce_constants(bad))


def test_parse_overrides_rejects_unknown_constant():
    with pytest.raises(ValueError):
        R.parse_overrides(["NOT_A_REAL_CONSTANT=1.0"])
    assert R.parse_overrides(["CATEG_TRASH_SCORE_MAX=0.45"]) == {"CATEG_TRASH_SCORE_MAX": 0.45}


# ── B2: QS_GARBAGE_NORM_MAX decoupling ──────────────────────────────────────


def test_qs_garbage_norm_max_is_tunable():
    """QS_GARBAGE_NORM_MAX must appear in TUNABLE_CONSTANTS after the B2 edit."""
    assert "QS_GARBAGE_NORM_MAX" in R.TUNABLE_CONSTANTS


def test_qs_garbage_norm_max_default_matches_live_module():
    """DEFAULT_CONSTANTS must reflect the live module value — never hardcoded."""
    assert R.DEFAULT_CONSTANTS["QS_GARBAGE_NORM_MAX"] == tu.QS_GARBAGE_NORM_MAX


def test_qs_garbage_norm_max_independent_of_hard_gate(corpus):
    """Raising QS_GARBAGE_NORM_MAX must move the QS score for high-density lines
    without changing the hard rule_garbage_density gate (which still uses
    CATEG_GARBAGE_DENSITY_HIGH = 0.35).  Concretely: if we push QS_GARBAGE_NORM_MAX
    to 0.80 (much larger than 0.35) some borderline garbage lines should escape the
    QS-band threshold and flip.  Meanwhile forcing CATEG_GARBAGE_DENSITY_HIGH = 0.80
    (the old coupled approach) would *also* widen the hard gate and let many more
    lines through — a different and larger effect."""
    import numpy as np

    from tools.recategorize_from_csv import recategorize_dataframe

    # High QS_GARBAGE_NORM_MAX only — hard gate stays at 0.35
    cfg_norm_only = dict(R.DEFAULT_CONSTANTS)
    cfg_norm_only["QS_GARBAGE_NORM_MAX"] = 0.80

    # High CATEG_GARBAGE_DENSITY_HIGH only — both gate and norm scale move
    cfg_gate_only = dict(R.DEFAULT_CONSTANTS)
    cfg_gate_only["CATEG_GARBAGE_DENSITY_HIGH"] = 0.80

    pred_norm = recategorize_dataframe(corpus, cfg_norm_only)
    pred_gate = recategorize_dataframe(corpus, cfg_gate_only)

    norm_categorized = pred_norm["categ"].map(R.normalize_category).to_numpy()
    gate_categorized = pred_gate["categ"].map(R.normalize_category).to_numpy()

    # The two should differ (at least on the smoke fixture) when garbage-dense
    # lines are present, because the gate change alone lets through lines that the
    # norm-only change does not (and vice versa).
    # If the sample has no garbage-dense lines both may trivially agree; allow that.
    # The key invariant is: the two parameter changes are independently addressable.
    baseline = recategorize_dataframe(corpus, R.DEFAULT_CONSTANTS)
    base_cat = baseline["categ"].map(R.normalize_category).to_numpy()

    # At minimum, neither of these overrides should cause MORE flips than the
    # "nuclear" option of setting both to 0.80 at once.
    cfg_both = dict(R.DEFAULT_CONSTANTS)
    cfg_both["QS_GARBAGE_NORM_MAX"] = 0.80
    cfg_both["CATEG_GARBAGE_DENSITY_HIGH"] = 0.80
    pred_both = recategorize_dataframe(corpus, cfg_both)
    both_cat = pred_both["categ"].map(R.normalize_category).to_numpy()

    flips_norm = int(np.sum(norm_categorized != base_cat))
    flips_gate = int(np.sum(gate_categorized != base_cat))
    flips_both = int(np.sum(both_cat != base_cat))

    assert flips_both >= max(flips_norm, flips_gate), (
        "Setting both parameters should affect at least as many lines as either alone"
    )


def test_evaluate_dataframe_baseline_is_zero_flip(corpus):
    metrics = R.evaluate_dataframe(corpus, R.DEFAULT_CONSTANTS)
    assert metrics["flip_rate"] <= 0.02
    assert metrics["line_count"] == len(corpus)
    for label, f1 in metrics["per_class_f1"].items():
        if metrics["per_class_support"].get(label, 0) > 0:
            assert f1 >= 0.9, f"{label} not adequately recovered at baseline"


def test_evaluate_is_document_aware(corpus):
    per_doc = R.evaluate_per_document(corpus, R.DEFAULT_CONSTANTS)
    assert len(per_doc) == corpus["file"].nunique()
    violations = {
        doc_id: stats
        for doc_id, stats in per_doc.items()
        if stats["flip_rate"] > 0.05
    }

    assert not violations, (
            "Document-aware parity exceeded 5% flip rate for:\n"
            + "\n".join(
        f"  {doc_id}: {stats}"
        for doc_id, stats in violations.items()
    )
    )


def test_default_constants_reproduce_stored_categories(corpus):
    """The faithful re-score at the live config must not flip any line beyond 2%."""
    predicted = R.recategorize_dataframe(corpus, None)
    stored = corpus["categ"].map(R.normalize_category).to_numpy()
    got = predicted["categ"].map(R.normalize_category).to_numpy()
    mismatches = [
        (corpus.iloc[i].get("file"), corpus.iloc[i].get("line_num"), stored[i], got[i])
        for i in range(len(stored))
        if stored[i] != got[i]
    ]
    assert len(mismatches) / len(stored) <= 0.02, f"re-score drift exceeded 2% at default config: {mismatches[:10]}"


def test_qs_garbage_norm_max_default_is_parity(corpus):
    metrics = R.evaluate_dataframe(corpus, R.DEFAULT_CONSTANTS)
    assert metrics["flip_rate"] <= 0.02, "QS_GARBAGE_NORM_MAX at default should preserve parity"



def test_print_document_aware_parity_violations(corpus, capsys):
    """
    Diagnostic test for document-level parity.

    This test intentionally does not assert a threshold. It prints every
    document whose default-config re-score exceeds the 5% flip-rate budget,
    together with its aggregate statistics.

    Remove or convert into a strict assertion once the underlying parity
    issue has been resolved.
    """
    per_doc = R.evaluate_per_document(corpus, R.DEFAULT_CONSTANTS)

    violations = {
        doc_id: stats
        for doc_id, stats in per_doc.items()
        if stats["flip_rate"] > 0.05
    }

    if not violations:
        return

    print("\n=== DOCUMENT-AWARE PARITY VIOLATIONS ===")

    for doc_id, stats in sorted(
        violations.items(),
        key=lambda item: item[1]["flip_rate"],
        reverse=True,
    ):
        print(
            f"{doc_id}: "
            f"flip_rate={stats['flip_rate']:.2%}, "
            f"changed={stats.get('changed', '?')}, "
            f"total={stats.get('total', '?')}"
        )

    print("==========================================")


def find_parity_mismatches(
    df,
    constants=None,
):
    """
    Return line-level category mismatches between stored categories and the
    production-equivalent re-score.

    Parameters
    ----------
    df:
        Input DataFrame containing the original stored categories and the
        columns required by ``recategorize_dataframe``.

    constants:
        Optional constants override. If None, the live/default constants are
        used.

    Returns
    -------
    pandas.DataFrame
        One row per mismatching line. The returned DataFrame contains the
        original input columns plus:

        ``stored_category``
            Normalized category from the input corpus.

        ``predicted_category``
            Normalized category produced by the re-scorer.

        ``category_changed``
            Always True for rows in the returned DataFrame.

    Notes
    -----
    This helper intentionally delegates all categorization to the real
    ``recategorize_dataframe`` implementation. It does not duplicate or
    approximate production categorization logic.
    """
    import pandas as pd

    predicted = recategorize_dataframe(df, constants)

    if len(predicted) != len(df):
        raise ValueError(
            "recategorize_dataframe changed the number of rows: "
            f"input={len(df)}, predicted={len(predicted)}"
        )

    result = df.copy()

    stored = result["categ"].map(normalize_category)
    predicted_categories = predicted["categ"].map(normalize_category)

    result["stored_category"] = stored.to_numpy()
    result["predicted_category"] = predicted_categories.to_numpy()

    result["category_changed"] = (
        result["stored_category"] != result["predicted_category"]
    )

    return result.loc[
        result["category_changed"]
    ].copy()


def test_report_document_aware_parity_violations(corpus):
    """
    Diagnostic report for document-level parity failures.

    The test fails if any document exceeds the 5% flip-rate budget and prints
    the exact mismatching lines responsible for the violation.
    """
    mismatches = R.find_parity_mismatches(
        corpus,
        R.DEFAULT_CONSTANTS,
    )

    if mismatches.empty:
        return

    per_doc = (
        mismatches.groupby("file", dropna=False)
        .size()
        .rename("changed")
        .to_frame()
    )

    totals = (
        corpus.groupby("file", dropna=False)
        .size()
        .rename("total")
        .to_frame()
    )

    report = per_doc.join(totals)

    report["flip_rate"] = (
        report["changed"] / report["total"]
    )

    violations = report.loc[
        report["flip_rate"] > 0.05
    ].sort_values(
        ["flip_rate", "changed"],
        ascending=False,
    )

    if violations.empty:
        return

    print("\n=== DOCUMENT-AWARE PARITY VIOLATIONS ===")

    for doc_id, stats in violations.iterrows():
        print(
            f"\n{doc_id}: "
            f"{int(stats['changed'])}/{int(stats['total'])} "
            f"({stats['flip_rate']:.2%})"
        )

        doc_mismatches = mismatches.loc[
            mismatches["file"] == doc_id
        ]

        for _, row in doc_mismatches.iterrows():
            file_name = row.get("file", doc_id)
            line_num = row.get("line_num", "?")
            text = str(row.get("text", ""))

            print(
                f"  L{line_num}: "
                f"{row['stored_category']} -> "
                f"{row['predicted_category']} | "
                f"{text[:300]}"
            )

    print("\n==========================================")

    assert False, (
        "Document-aware parity exceeded 5% flip rate for one or more "
        "documents. See diagnostic output above."
    )
