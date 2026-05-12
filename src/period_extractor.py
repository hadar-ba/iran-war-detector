"""
Stage 4: Extract the feature vector for a 21-day analysis period.

Feature vector schema (all fields always present; None = missing/uncollectable):
{
    "period_id": str,
    "start": str,           # YYYYMMDDHHMMSS
    "end": str,
    "extracted_at": str,    # ISO-8601 UTC

    # --- Volume (global, from timelinevol) ---
    "volume_total": float,      # sum of daily intensity values
    "volume_mean_daily": float, # mean over days_active
    "volume_peak": float,       # max single-day intensity
    "days_active": int,         # days with non-zero intensity

    # --- Language article counts (proxy for language-specific volume; artlist cap=250) ---
    "articles_en": int,
    "articles_he": int,
    "articles_fa": int,

    # --- Cross-language confluence ---
    # Fraction of active days where all 3 languages contributed at least 1 article.
    # Computed by binning artlist seendates into days.
    "confluence_score": float,  # 0.0 – 1.0

    # --- Source diversity ---
    "unique_domains_en": int,
    "unique_domains_he": int,
    "unique_domains_fa": int,
    "unique_domains_total": int,  # union across all three languages

    # --- Tone (from timelinetone) ---
    "tone_mean": float | None,
    "tone_min": float | None,
    "tone_max": float | None,

    # --- Silent signals (OSINT; filled in manually or left None) ---
    "silent_signals": float | None,   # 0.0 – 1.0 if available

    # --- Errors encountered during extraction (for logging) ---
    "errors": [str],
}
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from gdelt_client import (
    LANGUAGES,
    get_article_count,
    get_artlist,
    get_domain_counts,
    get_volume_timeline,
    get_volume_timeline_tone,
)


def extract_period(period_id: str, start: str, end: str,
                   is_reference: bool = False) -> dict:
    """
    Extract the full feature vector for the period [start, end].
    Makes up to 8 API calls (1 vol + 1 tone + 3×artlist for counts/domains + 3×artlist reused).
    All artlist data is fetched once and reused (cache handles deduplication).
    """
    errors = []
    now_str = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # 1. Volume timeline (global — sourcelang does not filter timelinevol)
    # ------------------------------------------------------------------
    vol_entries, err = get_volume_timeline(start, end, is_reference=is_reference)
    if err:
        errors.append(f"volume: {err}")
    active = [e for e in vol_entries if e.get("value", 0) > 0]
    volume_total = round(sum(e["value"] for e in active), 4)
    days_active = len(active)
    volume_mean = round(volume_total / days_active, 4) if days_active else 0.0
    volume_peak = round(max((e["value"] for e in active), default=0.0), 4)

    # ------------------------------------------------------------------
    # 2. Tone timeline
    # ------------------------------------------------------------------
    tone_entries, err = get_volume_timeline_tone(start, end, is_reference=is_reference)
    if err:
        errors.append(f"tone: {err}")
    tone_vals = [e["value"] for e in tone_entries if e.get("value") is not None]
    tone_mean = round(sum(tone_vals) / len(tone_vals), 4) if tone_vals else None
    tone_min = round(min(tone_vals), 4) if tone_vals else None
    tone_max = round(max(tone_vals), 4) if tone_vals else None

    # ------------------------------------------------------------------
    # 3. Per-language artlists (fetched once; shared for count, domains, confluence)
    # ------------------------------------------------------------------
    lang_articles: dict[str, list] = {}
    for lang in LANGUAGES:
        arts, err = get_artlist(start, end, lang, max_records=250, is_reference=is_reference)
        if err:
            errors.append(f"artlist/{lang}: {err}")
        lang_articles[lang] = arts

    articles_en = len(lang_articles.get("english", []))
    articles_he = len(lang_articles.get("hebrew", []))
    articles_fa = len(lang_articles.get("persian", []))

    # ------------------------------------------------------------------
    # 4. Source diversity (unique domains per language and total union)
    # ------------------------------------------------------------------
    def _domains(arts: list) -> set:
        from urllib.parse import urlparse
        result = set()
        for art in arts:
            d = art.get("domain", "")
            if not d:
                d = urlparse(art.get("url", "")).netloc.lower().lstrip("www.")
            if d:
                result.add(d)
        return result

    domains_en = _domains(lang_articles.get("english", []))
    domains_he = _domains(lang_articles.get("hebrew", []))
    domains_fa = _domains(lang_articles.get("persian", []))
    domains_all = domains_en | domains_he | domains_fa

    # ------------------------------------------------------------------
    # 5. Cross-language confluence
    # Bin articles by date (YYYYMMDD extracted from seendate field).
    # Confluence = fraction of "active days" where all 3 languages had >= 1 article.
    # ------------------------------------------------------------------
    def _day_set(arts: list) -> set:
        days = set()
        for art in arts:
            seen = art.get("seendate", "")
            if seen:
                # seendate format: "20240323T000000Z" or "20240323000000"
                day = seen[:8]
                if day.isdigit():
                    days.add(day)
        return days

    days_en = _day_set(lang_articles.get("english", []))
    days_he = _day_set(lang_articles.get("hebrew", []))
    days_fa = _day_set(lang_articles.get("persian", []))

    all_lang_days = days_en | days_he | days_fa
    if all_lang_days:
        tri_days = sum(1 for d in all_lang_days if d in days_en and d in days_he and d in days_fa)
        confluence_score = round(tri_days / len(all_lang_days), 4)
    else:
        confluence_score = 0.0

    # ------------------------------------------------------------------
    # 6. Assemble vector
    # ------------------------------------------------------------------
    return {
        "period_id": period_id,
        "start": start,
        "end": end,
        "extracted_at": now_str,
        "volume_total": volume_total,
        "volume_mean_daily": volume_mean,
        "volume_peak": volume_peak,
        "days_active": days_active,
        "articles_en": articles_en,
        "articles_he": articles_he,
        "articles_fa": articles_fa,
        "confluence_score": confluence_score,
        "unique_domains_en": len(domains_en),
        "unique_domains_he": len(domains_he),
        "unique_domains_fa": len(domains_fa),
        "unique_domains_total": len(domains_all),
        "tone_mean": tone_mean,
        "tone_min": tone_min,
        "tone_max": tone_max,
        "silent_signals": None,
        "errors": errors,
    }
