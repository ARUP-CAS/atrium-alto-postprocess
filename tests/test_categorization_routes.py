"""
tests/test_categorization_routes.py
===================================
Unit coverage for the categorisation routes: the inverted/mirror lexicon and
its derivation, analyze_rotation_signals (gate behaviour), the per-line
trash_inverted route + non-diacritics hard gate, low-ppl Clear fast-track,
damaged-token capping, and structured measurement predicate boundaries.
"""

from text_util import (
    _MIRROR_GLYPH,
    _ROTATE_GLYPH,
    ROT_GHOSTLIST,
    ROT_WHITELIST,
    _looks_like_measurement,
    _transform_word,
    analyze_rotation_signals,
    categorize_line,
    inspect_short_line_telemetry,
    is_structured_line,
)


class TestExplicitDiagnosticHardGates:
    """Test explicit hard gates routing directly on rule firing + garbage evidence."""

    def test_bigram_run_with_garbage_evidence_routes_to_trash(self):
        # High quality score base, but bigram run + low valid word ratio -> Trash
        cat, _, reason = categorize_line(0.85, "IDIDID text", 2, 0.3, 100.0, valid_word_ratio=0.10, return_reason=True)
        assert cat == "Trash" and reason in ("trash_threshold", "trash_hard_sweep")

    def test_fragment_tokens_with_garbage_evidence_routes_to_trash(self):
        # Fragment tokens + low language score -> Trash via rule_fragment_tokens
        cat, _, reason = categorize_line(
            0.82, "a b c d e f", 6, 0.2, 120.0, lang_score=0.10, orig_lang_score=0.10, return_reason=True
        )
        assert cat == "Trash" and reason == "trash_threshold"


class TestShortLineTelemetry:
    """Test telemetry inspector helper for short-line route analysis."""

    def test_inspect_short_line_telemetry_captures_fields(self):
        telemetry = inspect_short_line_telemetry(
            text_source="v - 112mm",
            word_count=2,
            valid_word_ratio=1.0,
            lang_score=0.9,
            perplexity=45.0,
        )
        assert telemetry["word_count"] == 2
        assert telemetry["structured"] is True
        assert telemetry["final_category"] in ("Clear", "Noisy", "Trash")
        assert "route_reason" in telemetry


class TestGlyphTransforms:
    def test_mirror_corrected_values(self):
        assert _transform_word("pouze", _MIRROR_GLYPH) == "ezuoq"
        assert _transform_word("bude", _MIRROR_GLYPH) == "ebud"

    def test_rotate_corrected_values(self):
        assert _transform_word("pouze", _ROTATE_GLYPH) == "aznod"
        assert _transform_word("bude", _ROTATE_GLYPH) == "apnq"

    def test_short_words(self):
        assert _transform_word("po", _MIRROR_GLYPH) == "oq"
        assert _transform_word("po", _ROTATE_GLYPH) == "od"
        assert _transform_word("on", _MIRROR_GLYPH) == "no"

    def test_unmappable_glyph_aborts_word(self):
        assert _transform_word("kov", _ROTATE_GLYPH) is None


class TestTrashInvertedGate:
    def test_ghost_dominated_and_not_upright_is_trash(self):
        cat, _, reason = categorize_line(
            0.80, "oq zem", 2, 0.3, 300.0, return_reason=True, ghost_dominated=True, is_upright_czech=False
        )
        assert cat == "Trash" and reason == "trash_inverted"

    def test_upright_overrides_ghost_route(self):
        cat, _, reason = categorize_line(
            0.80, "oq náčrt", 2, 0.3, 300.0, return_reason=True, ghost_dominated=True, is_upright_czech=True
        )
        assert reason != "trash_inverted" and cat != "Trash"


class TestLowPplFastTrack:
    """The low-ppl Clear fast-track (rule_lowppl_clear): LM-confident text
    (ppl < LOWPPL_CLEAR_MAX, word_count >= 3) is promoted straight to Clear,
    independent of the score band."""

    def test_lowppl_multiword_promoted_to_clear(self):
        cat, _, reason = categorize_line(
            0.95, "krátký čistý text", 3, 0.4, 30.0, garbage_density=0.1, return_reason=True
        )
        assert cat == "Clear" and reason == "lowppl_clear"

    def test_short_fragment_no_longer_held_noisy(self):
        cat, _, reason = categorize_line(0.92, "značky.", 1, 0.4, 200.0, garbage_density=0.14, return_reason=True)
        assert cat == "Clear" and reason != "lowppl_clear"

    def test_lowppl_low_valid_ratio_capped_to_noisy(self):
        cat, _, reason = categorize_line(
            0.80, "slovo bez bez diakritiky", 4, 0.4, 30.0, return_reason=True, valid_word_ratio=0.50
        )
        assert cat == "Noisy" and reason == "noisy_threshold"


class TestGhostlist:
    def test_whitelist_and_ghostlist_disjoint(self):
        assert ROT_WHITELIST.isdisjoint(ROT_GHOSTLIST)

    def test_common_real_words_not_ghosts(self):
        for w in ("no", "od", "po", "bo", "pod", "se"):
            assert w not in ROT_GHOSTLIST

    def test_expected_ghosts_present(self):
        for g in ("aznod", "apnq", "oq", "boq", "zem"):
            assert g in ROT_GHOSTLIST


class TestAnalyzeRotationSignals:
    def test_empty_text(self):
        assert analyze_rotation_signals("") == (False, False)

    def test_diacritics_force_upright(self):
        up, ghost = analyze_rotation_signals("náčrt sondy")
        assert up is True and ghost is False

    def test_whitelist_word_forces_upright(self):
        up, _ = analyze_rotation_signals("pouze tento")
        assert up is True

    def test_ghost_dominated_short_inverted(self):
        up, ghost = analyze_rotation_signals("oq zem")
        assert up is False and ghost is True

    def test_diacritic_keeps_upright_despite_ghost(self):
        up, _ = analyze_rotation_signals("oq náčrt")
        assert up is True


class TestExtremePplRoute:
    def test_extreme_ppl_low_conf_garbage_trashed(self):
        cat, _, reason = categorize_line(
            0.80, "Alyrý cvod nede % Agrgr oAOrt", 6, 0.41, 15168.0, return_reason=True, orig_lang_score=0.6658
        )
        assert cat == "Trash" and reason == "trash_hard_sweep"

    def test_extreme_ppl_confident_text_spared(self):
        cat, _, reason = categorize_line(
            0.80, "Taxon vojcuskou povinen jest", 4, 0.45, 15168.0, return_reason=True, orig_lang_score=0.95
        )
        assert reason != "trash_hard_sweep"


class TestLmConfidentCzechBypass:
    def test_upright_czech_low_ppl_bypasses_valid_cap(self):
        cat, _, reason = categorize_line(
            0.88,
            "í nezpůsobilost ke službě nebyla",
            5,
            0.43,
            80.0,
            return_reason=True,
            valid_word_ratio=0.80,
            is_upright_czech=True,
            garbage_density=0.0,
        )
        assert cat == "Clear" and reason == "clear_threshold"

    def test_non_czech_low_valid_still_capped(self):
        cat, _, reason = categorize_line(
            0.88,
            "slovo bez diakritiky tady",
            5,
            0.43,
            80.0,
            return_reason=True,
            valid_word_ratio=0.80,
            is_upright_czech=False,
            garbage_density=0.0,
        )
        assert cat == "Noisy" and reason == "noisy_threshold"

    def test_high_garbage_czech_not_bypassed(self):
        cat, _, _ = categorize_line(
            0.88,
            "nonč mI žn dn 1074 484",
            5,
            0.22,
            131.0,
            return_reason=True,
            valid_word_ratio=0.40,
            is_upright_czech=True,
            garbage_density=0.20,
        )
        assert cat == "Noisy" or cat == "Trash"


class TestDamagedTokenCap:
    """Restored damaged-token backstop: character-level damage prevents Clear."""

    def test_damaged_token_caps_clear_score_to_noisy(self):
        # High quality score (qs=0.90), but text contains damaged token 'd^ku'
        cat, _, reason = categorize_line(0.90, "tento text obsahuje d^ku poškození", 5, 0.4, 100.0, return_reason=True)
        assert cat == "Noisy" and reason == "noisy_threshold"


class TestStructuredLineMeasurement:
    """Tightened _looks_like_measurement and is_structured_line predicates."""

    def test_legitimate_measurements_protected(self):
        assert is_structured_line("Rozměry: v - 112mm, pr.okraje - 145, pr. dna - 7") is True
        assert is_structured_line("Rozměry ; v- 144 mm, pr. okraje - 125") is True
        assert is_structured_line("v - 185 mm, pr. okraje - 20") is True
        assert is_structured_line("pr. hrdla 62mm, pr.-dna 36") is True

    def test_single_letter_units_and_probe_noise_rejected(self):
        assert _looks_like_measurement("3 m") is False
        assert _looks_like_measurement("o 5 m") is False
        assert _looks_like_measurement("cuxoaid v. 12") is False
        assert _looks_like_measurement("clouCelRa pr. 4") is False
