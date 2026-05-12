"""
Stage 6: Compute similarity between a current-period vector and reference vectors.

Similarity is a weighted combination of normalized sub-scores across feature categories.
The result is a score in [0.0, 1.0] where 1.0 means identical to the reference pattern.

Feature weights (from spec §8, Stage 7 calibration pending):
    silent_signals          40%   (OSINT; None → excluded from denominator)
    confluence              25%
    cross_lang_correlation  10%   (proxy: ratio of non-zero language counts)
    raw_volume              10%
    source_diversity        10%
    tone                     5%

When silent_signals is None (unavailable), the remaining weights are renormalized
to sum to 1.0 so the score stays in [0, 1].
"""

import json
import os
import math

WEIGHTS = {
    "silent_signals":         0.40,
    "confluence":             0.25,
    "cross_lang_correlation": 0.10,
    "raw_volume":             0.10,
    "source_diversity":       0.10,
    "tone":                   0.05,
}

WARN_THRESHOLD = 0.70   # similarity to any PRE_* period above this → alert


def _sub_score_volume(current: dict, reference: dict) -> float:
    """Ratio of current to reference volume, capped at 1.0 (higher current = higher similarity)."""
    ref_vol = reference.get("volume_total", 0)
    cur_vol = current.get("volume_total", 0)
    if ref_vol == 0:
        return 1.0 if cur_vol == 0 else 0.0
    return min(cur_vol / ref_vol, 1.0)


def _sub_score_confluence(current: dict, reference: dict) -> float:
    """
    1 - |current_confluence - reference_confluence| normalized.
    Confluence of 0 vs 0 = perfect match; divergence penalizes score.
    """
    cur = current.get("confluence_score", 0.0) or 0.0
    ref = reference.get("confluence_score", 0.0) or 0.0
    return 1.0 - abs(cur - ref)


def _sub_score_cross_lang_correlation(current: dict, reference: dict) -> float:
    """
    Proxy: cosine similarity of the (articles_en, articles_he, articles_fa) vectors.
    Measures whether the same language balance pattern holds.
    """
    def vec(d):
        return (
            d.get("articles_en", 0) or 0,
            d.get("articles_he", 0) or 0,
            d.get("articles_fa", 0) or 0,
        )
    c = vec(current)
    r = vec(reference)
    dot = sum(a * b for a, b in zip(c, r))
    mag_c = math.sqrt(sum(a * a for a in c))
    mag_r = math.sqrt(sum(b * b for b in r))
    if mag_c == 0 or mag_r == 0:
        return 1.0 if mag_c == mag_r == 0 else 0.0
    return dot / (mag_c * mag_r)


def _sub_score_source_diversity(current: dict, reference: dict) -> float:
    """Ratio of current to reference unique domains, capped at 1.0."""
    ref_dom = reference.get("unique_domains_total", 0)
    cur_dom = current.get("unique_domains_total", 0)
    if ref_dom == 0:
        return 1.0 if cur_dom == 0 else 0.0
    return min(cur_dom / ref_dom, 1.0)


def _sub_score_tone(current: dict, reference: dict) -> float:
    """
    Similarity of mean tone. Both values are typically negative.
    Uses 1 - normalized absolute difference, bounded to [0, 1].
    Maximum plausible tone range assumed to be 20 units.
    """
    cur_tone = current.get("tone_mean")
    ref_tone = reference.get("tone_mean")
    if cur_tone is None or ref_tone is None:
        return 0.5   # neutral when data missing
    diff = abs(cur_tone - ref_tone)
    return max(0.0, 1.0 - diff / 20.0)


def compute_similarity(current: dict, reference: dict) -> dict:
    """
    Compare current period vector against a reference vector.
    Returns a result dict with the composite score and all sub-scores.
    """
    sub_scores = {
        "silent_signals":         current.get("silent_signals"),  # pass-through if present
        "confluence":             _sub_score_confluence(current, reference),
        "cross_lang_correlation": _sub_score_cross_lang_correlation(current, reference),
        "raw_volume":             _sub_score_volume(current, reference),
        "source_diversity":       _sub_score_source_diversity(current, reference),
        "tone":                   _sub_score_tone(current, reference),
    }

    # Compute weighted sum; exclude silent_signals if None (renormalize weights)
    active_weights = {k: v for k, v in WEIGHTS.items()
                      if not (k == "silent_signals" and sub_scores[k] is None)}
    weight_sum = sum(active_weights.values())
    if weight_sum == 0:
        composite = 0.0
    else:
        composite = sum(
            sub_scores[k] * w / weight_sum
            for k, w in active_weights.items()
            if sub_scores[k] is not None
        )

    return {
        "reference_id": reference.get("period_id"),
        "reference_type": _period_type(reference.get("period_id", "")),
        "composite_score": round(composite, 4),
        "is_pre_round": _period_type(reference.get("period_id", "")) == "pre-round",
        "warn": composite >= WARN_THRESHOLD and _period_type(reference.get("period_id", "")) == "pre-round",
        "sub_scores": {k: round(v, 4) if v is not None else None for k, v in sub_scores.items()},
        "weights_applied": {k: round(w / weight_sum, 4) for k, w in active_weights.items()},
    }


def _period_type(period_id: str) -> str:
    if period_id.startswith("PRE_"):
        return "pre-round"
    if period_id.startswith("POST_"):
        return "post-ceasefire"
    return "quiet"


def load_reference_vectors(ref_dir: str) -> dict[str, dict]:
    """Load all reference JSON files from ref_dir. Returns {period_id: vector}."""
    vectors = {}
    if not os.path.isdir(ref_dir):
        return vectors
    for fname in os.listdir(ref_dir):
        if fname.endswith(".json"):
            with open(os.path.join(ref_dir, fname), encoding="utf-8") as f:
                vec = json.load(f)
            vectors[vec.get("period_id", fname[:-5])] = vec
    return vectors


def rank_similarities(current: dict, references: dict[str, dict]) -> list[dict]:
    """
    Compare current against all reference vectors.
    Returns results sorted by composite_score descending.
    """
    results = [compute_similarity(current, ref) for ref in references.values()]
    results.sort(key=lambda r: r["composite_score"], reverse=True)
    return results
