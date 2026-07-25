"""
service/text_inference.py
Manages the LayoutReader, FastText, and Qwen2.5-0.5B (default) perplexity models.

Classification is fully aligned with the main pipeline (classify_TEXT.py):
  - Unified penalty path : categorize_line() from text_util_langID
  - New API fields       : word_weird, garbage_density, ldl_fuses, etc.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from v3.helpers import boxes2inputs, parse_logits, prepare_inputs
except ImportError:
    print("CRITICAL: 'v3' folder not found in project root — layout reordering unavailable.")
    prepare_inputs = boxes2inputs = parse_logits = None  # type: ignore[assignment]

# Import the full quality-analysis toolkit from the main pipeline module.
# Unconditional on purpose: the service must never silently fall back to a
# stale secondary categoriser — a broken import has to fail loud at startup.
# extract_JSON_2_TXT's key-whitelist walk has no heavy dependencies (stdlib
# json only), so it's imported directly rather than re-implemented — unlike
# the ALTO parsing below, which is deliberately mirrored (#8) to avoid pulling
# extract_LytRdr_ALTO_2_TXT's eager torch/transformers/pandas imports into a
# module that must stay importable without ML libraries installed.
from extract_JSON_2_TXT import TARGET_KEYS, _yield_json_text_by_keys  # noqa: E402
from service.utils import normalize_boxes, parse_alto_xml_lines, post_process_text  # noqa: E402
from text_util import (  # noqa: E402
    analyze_rotation_signals,
    calculate_perplexity_batch,
    compute_garbage_density,
    compute_quality_score,
    compute_valid_ratio,
    compute_vowel_ratio,
    compute_word_weird_ratio,
    detect_fused_words,
    detect_gibberish_words,
    detect_letter_digit_letter,
    detect_mid_uppercase,
    detect_repeated_chars,
    detect_strange_symbols,
    detect_wx_words,
    parse_line_splits,
    score_words_in_line,
)
from text_util import categorize_line as _categorize_line_struct  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(project_root / "models")))
FASTTEXT_MODEL_PATH = MODEL_DIR / "lid.176.bin"

# LayoutReader chunk sizes (#8): same defaults as extract_LytRdr_ALTO_2_TXT's
# [EXTRACT] LR_CHUNK_SIZE/LR_MIN_CHUNK_SIZE, but env-var configured here since
# the service otherwise has no dependency on setup/config.txt.
LR_CHUNK_SIZE = int(os.getenv("LR_CHUNK_SIZE", 350))
LR_MIN_CHUNK_SIZE = int(os.getenv("LR_MIN_CHUNK_SIZE", 50))


class TextModelManager:
    def __init__(self) -> None:
        self.device = "cpu"  # Initialized here, updated properly in load_models
        self.layout_model: Optional[Any] = None
        self.ft_model: Optional[Any] = None
        self.ppl_model: Optional[Any] = None
        self.ppl_tokenizer: Optional[Any] = None
        self._models_loaded = False

    def load_models(self) -> None:
        """Load all models synchronously; raise RuntimeError on failure."""
        if self._models_loaded:
            return

        import torch

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading Text Processing Models on %s …", self.device)

        try:
            # LAZY LOAD heavy ML libraries strictly inside this method
            import fasttext
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                LayoutLMv3ForTokenClassification,
            )

            # 1. LayoutReader (LayoutLMv3)
            layout_model_path = os.getenv("LAYOUT_MODEL_PATH", "hantian/layoutreader")
            self.layout_model = LayoutLMv3ForTokenClassification.from_pretrained(layout_model_path)
            self.layout_model.to(self.device)
            self.layout_model.eval()

            # 2. FastText language identification
            self.ft_model = fasttext.load_model(str(FASTTEXT_MODEL_PATH))

            # 3. Perplexity model (Qwen2.5-0.5B by default; override with GPT2_MODEL_NAME,
            #    e.g. distilgpt2 for English-only collections).
            #    Loaded in full precision and moved explicitly to a single device (no 4-bit
            #    bitsandbytes / device_map="auto", which placed layers non-deterministically).
            gpt2_path = os.getenv("GPT2_MODEL_NAME", "Qwen/Qwen2.5-0.5B")
            self.ppl_tokenizer = AutoTokenizer.from_pretrained(gpt2_path)
            self.ppl_tokenizer.pad_token = self.ppl_tokenizer.eos_token

            ppl_dtype = "auto" if self.device == "cuda" else torch.float32
            self.ppl_model = AutoModelForCausalLM.from_pretrained(gpt2_path, dtype=ppl_dtype)
            self.ppl_model.to(self.device)

            self.ppl_model.eval()

            self._models_loaded = True
            logger.info("All models loaded successfully.")

        except Exception as exc:
            logger.error("Critical error loading models: %s", exc)
            self._models_loaded = False
            raise RuntimeError(f"Failed to load core text-processing models: {exc}") from exc

    def _classify_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Score and categorise a list of already-split text lines.

        Shared by process_text_file / process_json / process_alto so all three
        formats classify identically once they've each produced an ordered
        list of lines. Perplexity is computed once for the whole batch (#8),
        mirroring how classify_TEXT.py favours batched GPU perplexity over a
        per-line model call.
        """
        if not lines:
            return []

        ppls = calculate_perplexity_batch(lines, self.ppl_model, self.ppl_tokenizer, self.device)
        cleaned_lines: List[Dict[str, Any]] = []
        for line_num, (text, ppl) in enumerate(zip(lines, ppls, strict=True), start=1):
            entry = _classify_line(
                text,
                ppl,
                ft_model=self.ft_model,
                ppl_model=self.ppl_model,
                tokenizer=self.ppl_tokenizer,
                device=self.device,
            )
            entry["line_num"] = line_num
            cleaned_lines.append(entry)
        return cleaned_lines

    def process_text_file(self, path: str) -> Dict[str, Any]:
        """Classify a plain-text upload, one line per non-empty line."""
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        return {"type": "plain_text", "cleaned_lines": self._classify_lines(lines)}

    def process_json(self, path: str) -> Dict[str, Any]:
        """Classify a generic JSON OCR upload.

        Extracts ordered text leaves with the same TARGET_KEYS whitelist walk
        extract_JSON_2_TXT.py uses for the batch pipeline, so a given file
        yields the same lines through either path. Each leaf is treated as
        one line, matching the pipeline's "one JSON file = one page" model.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        lines = list(_yield_json_text_by_keys(data, TARGET_KEYS))
        return {"type": "json", "cleaned_lines": self._classify_lines(lines)}

    def process_alto(self, path: str) -> Dict[str, Any]:
        """Classify an ALTO XML upload: parse -> reorder -> dehyphenate -> classify.

        Uses the line-level parser (parse_alto_xml_lines), not the word-level
        parse_alto_xml also exported by service/utils.py — line granularity is
        what LayoutReader reordering and per-line classification both expect
        here (#8).
        """
        lines, boxes, (page_w, page_h) = parse_alto_xml_lines(path)
        if not lines:
            return {"type": "alto_xml", "cleaned_lines": []}

        norm_boxes = normalize_boxes(boxes, page_w, page_h)

        if boxes2inputs is not None and self.layout_model is not None:
            ordered_lines, ordered_boxes = _run_layout_reader(lines, norm_boxes, self.layout_model, self.device)
        else:
            # v3.helpers unavailable: fall back to document order rather than
            # failing the whole request (#8; mirrors the startup warning above).
            ordered_lines, ordered_boxes = lines, norm_boxes

        full_text = post_process_text(ordered_lines, ordered_boxes)

        # Reconstruct hyphen-split words and classify line by line, carrying
        # the split-suffix state across lines exactly like classify_TEXT.py's
        # per-page loop (so a word split across a line break isn't duplicated
        # or left broken).
        raw_lines = full_text.splitlines()
        resolved_lines: List[str] = []
        expected_incoming_suffix = ""
        for raw_line in raw_lines:
            if not raw_line.strip():
                continue
            merged_text, _outgoing_prefix, outgoing_suffix = parse_line_splits(raw_line)
            if expected_incoming_suffix:
                stripped = merged_text.lstrip()
                if stripped.startswith(expected_incoming_suffix):
                    merged_text = merged_text.replace(expected_incoming_suffix, "", 1).strip()
            expected_incoming_suffix = outgoing_suffix
            if merged_text.strip():
                resolved_lines.append(merged_text.strip())

        return {"type": "alto_xml", "cleaned_lines": self._classify_lines(resolved_lines)}


def _run_layout_reader(lines: List[str], norm_boxes: List[List[int]], layout_model, device):
    """Predict LayoutReader reading order for one page's lines, chunked with
    CUDA-OOM halving/retry. Mirrors extract_LytRdr_ALTO_2_TXT.extract_single_page's
    inference loop (#8), factored out as a reusable function since the service
    processes one page per request rather than a CSV of many.
    """
    import torch

    full_ordered_lines: List[str] = []
    full_ordered_boxes: List[List[int]] = []

    chunk_size = LR_CHUNK_SIZE
    i = 0
    while i < len(lines):
        chunk_lines = lines[i : i + chunk_size]
        chunk_boxes = norm_boxes[i : i + chunk_size]
        if not chunk_lines:
            i += chunk_size
            continue

        try:
            inputs = boxes2inputs(chunk_boxes)
            inputs = prepare_inputs(inputs, layout_model)
            for k, v in inputs.items():
                if isinstance(v, torch.Tensor):
                    inputs[k] = v.to(device)

            with torch.no_grad():
                logits = layout_model(**inputs).logits.cpu().squeeze(0)

            order_indices = parse_logits(logits, len(chunk_boxes))
            full_ordered_lines.extend([chunk_lines[idx] for idx in order_indices])
            full_ordered_boxes.extend([chunk_boxes[idx] for idx in order_indices])
            i += chunk_size

        except (torch.cuda.OutOfMemoryError, RuntimeError) as e:
            is_oom = isinstance(e, torch.cuda.OutOfMemoryError) or (
                isinstance(e, RuntimeError) and "memory" in str(e).lower()
            )
            if not is_oom:
                raise
            torch.cuda.empty_cache()
            chunk_size = chunk_size // 2
            if chunk_size < LR_MIN_CHUNK_SIZE:
                logger.error("LayoutReader OOM even at minimum chunk size; falling back to document order.")
                return lines, norm_boxes
            logger.warning("LayoutReader OOM: retrying at i=%d with chunk_size=%d.", i, chunk_size)

    return full_ordered_lines, full_ordered_boxes


# ---------------------------------------------------------------------------
# Helper: classify one line (mirrors process_and_write_batch in langID_classify)
# ---------------------------------------------------------------------------


def _classify_line(
    text: str,
    ppl: float,
    *,
    ft_model,
    ppl_model,
    tokenizer,
    device: str,
) -> Dict[str, Any]:
    """
    Run the full unified classification pipeline on a single text line and
    return all quality metrics.

    categorize_line signature (from text_util_langID):
        categorize_line(qs, txt, wc, vowel_ratio, perplexity, *, weird_ratio=0.0,
                        return_reason=False, valid_word_ratio=1.0, lang_score=1.0,
                        orig_lang_score=1.0, gibberish_present=False,
                        garbage_density=0.0, is_upright_czech=False,
                        ghost_dominated=False)
    """
    # 1. Language Identification
    labels, scores = ft_model.predict([text.lower()], k=1)
    lang = labels[0][0].replace("__label__", "")
    lang_score = float(scores[0][0])

    # 2. Structural Metrics
    sym_count = detect_strange_symbols(text)
    upper_count = detect_mid_uppercase(text)
    rep_count = detect_repeated_chars(text)
    fuse_count = detect_letter_digit_letter(text)
    gibb_count = detect_gibberish_words(text)
    wx_count = detect_wx_words(text)
    fused_words = detect_fused_words(text)
    g_density = compute_garbage_density(text)
    vowel_ratio = compute_vowel_ratio(text)

    wc = len(text.split())
    cc = len(text)

    # 3. Weirdness, validity, rotation
    word_scores = score_words_in_line(text)
    weird_ratio = compute_word_weird_ratio(word_scores)
    valid_ratio = compute_valid_ratio(text)
    is_upright_czech, ghost_dominated = analyze_rotation_signals(text)

    # 4. Quality score
    q_score = compute_quality_score(
        valid_word_ratio=valid_ratio,
        perplexity=ppl,
        text_length=cc,
        weird_ratio=weird_ratio,
        vowel_ratio=vowel_ratio,
        garbage_density=g_density,
        lang_score=lang_score,
        gibberish_ratio=(gibb_count + wx_count) / max(wc, 1),
        fused_ratio=fused_words / max(wc, 1),
        is_upright_czech=is_upright_czech,
    )

    # 5. Categorisation — positional args match the real signature exactly
    categ, q_score = _categorize_line_struct(
        q_score,  # qs
        text,  # txt
        wc,  # wc
        vowel_ratio,  # vowel_ratio
        ppl,  # perplexity
        weird_ratio=weird_ratio,
        valid_word_ratio=valid_ratio,
        lang_score=lang_score,
        gibberish_present=(gibb_count + wx_count) > 0,
        garbage_density=g_density,
        is_upright_czech=is_upright_czech,
        ghost_dominated=ghost_dominated,
    )

    return {
        "text": text,
        "lang": lang,
        "lang_score": round(lang_score, 4),
        "perplexity": round(ppl, 2),
        "garbage_density": round(g_density, 4),
        "sym_count": sym_count,
        "upper_count": upper_count,
        "repeated_count": rep_count,
        "ldl_fuses": fuse_count,
        "gibberish": gibb_count,
        "word_weird": round(weird_ratio, 4),
        "quality_score": round(q_score, 4),
        "category": categ,
    }


# Module-level singleton used by text_api.py
text_manager = TextModelManager()
