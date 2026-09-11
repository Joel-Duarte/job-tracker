"""
Deterministic Compensation Parser.
Extracts clean numerical salary ranges (min, max), currency symbols,
and payment intervals ('YEARLY', 'MONTHLY', 'HOURLY', 'NOT_SPECIFIED')
from human-written job posting compensation text.
"""

from __future__ import annotations

import re
from typing import Any

# Currency symbol and code mappings
CURRENCY_MAP = {
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "$": "USD",
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "£": "GBP",
    "gbp": "GBP",
    "pound": "GBP",
    "pounds": "GBP",
    "cad": "CAD",
    "c$": "CAD",
    "aud": "AUD",
    "a$": "AUD",
    "chf": "CHF",
    "sek": "SEK",
    "nok": "NOK",
    "dkk": "DKK",
    "pln": "PLN",
    "inr": "INR",
    "₹": "INR",
    "jpy": "JPY",
    "¥": "JPY",
    "cny": "CNY",
    "brl": "BRL",
    "r$": "BRL",
}

# Period keywords mappings
YEAR_KEYWORDS = {
    "year",
    "yr",
    "annum",
    "annual",
    "annually",
    "yearly",
    "p.a.",
    "pa",
    "per annum",
    "per year",
}
MONTH_KEYWORDS = {"month", "mo", "monthly", "p.m.", "pm", "per month"}
HOUR_KEYWORDS = {"hour", "hr", "hourly", "p.h.", "ph", "per hour"}


def _detect_currency(text: str) -> str | None:
    """Detects currency code from text string."""
    text_lower = text.lower()
    # Check explicit symbols first
    for sym in ["€", "£", "₹", "¥", "r$"]:
        if sym in text_lower:
            return CURRENCY_MAP[sym]

    # Check for CAD or AUD prefix before generic $
    if "cad" in text_lower or "c$" in text_lower:
        return "CAD"
    if "aud" in text_lower or "a$" in text_lower:
        return "AUD"

    if "$" in text_lower:
        return "USD"

    # Check 3-letter currency codes as whole words
    for code in [
        "eur",
        "usd",
        "gbp",
        "chf",
        "sek",
        "nok",
        "dkk",
        "pln",
        "inr",
        "jpy",
        "cny",
        "cad",
        "aud",
        "brl",
    ]:
        if re.search(r"\b" + code + r"\b", text_lower):
            return CURRENCY_MAP[code]

    return None


def _detect_period(text: str, num_sample: float | None = None) -> str:
    """
    Detects payment interval from text keywords.
    Falls back to heuristics if keyword is ambiguous.
    """
    text_lower = text.lower()

    for kw in YEAR_KEYWORDS:
        if (
            re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
            or f"/{kw}" in text_lower
        ):
            return "YEARLY"

    for kw in MONTH_KEYWORDS:
        if (
            re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
            or f"/{kw}" in text_lower
        ):
            return "MONTHLY"

    for kw in HOUR_KEYWORDS:
        if (
            re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
            or f"/{kw}" in text_lower
        ):
            return "HOURLY"

    # Heuristic fallback if number magnitude is overwhelmingly clear
    if num_sample is not None:
        if num_sample >= 25000:
            return "YEARLY"
        if 15 <= num_sample <= 300:
            return "HOURLY"
        if 1000 <= num_sample <= 15000:
            return "MONTHLY"

    return "NOT_SPECIFIED"


def _clean_number(num_str: str) -> float | None:
    """Converts a matched number string like '66,500', '66.500', '150k' into float."""
    s = num_str.strip().lower()
    multiplier = 1.0
    if s.endswith("k"):
        multiplier = 1000.0
        s = s[:-1].strip()
    elif s.endswith("m"):
        multiplier = 1000000.0
        s = s[:-1].strip()

    # Handle multiple separators (e.g. 1.250.000 or 1,250,000)
    if s.count(".") > 1 and "," not in s:
        s = s.replace(".", "")
    elif s.count(",") > 1 and "." not in s:
        s = s.replace(",", "")
    # Single separator European check vs decimal: e.g. 66.500 vs 66.5
    elif "." in s and "," not in s:
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            s = parts[0] + parts[1]
    elif "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            s = parts[0] + parts[1]
    elif "," in s and "." in s:
        # e.g. 1,250.50 (US) or 1.250,50 (EU)
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")

    # Remove non-numeric except decimal dot
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return None

    try:
        val = float(s) * multiplier
        return val if val > 0 else None
    except ValueError:
        return None


def parse_compensation_text(raw_text: str | None) -> dict[str, Any]:
    """
    Parses human-written compensation string into structured attributes:
    - salary_min: float | None
    - salary_max: float | None
    - currency: str | None (e.g. 'EUR', 'USD', 'GBP')
    - salary_period: str ('YEARLY', 'MONTHLY', 'HOURLY', 'NOT_SPECIFIED')
    - compensation_text: str | None (original cleaned string)
    """
    default_result: dict[str, Any] = {
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "salary_period": "NOT_SPECIFIED",
        "compensation_text": raw_text.strip() if raw_text else None,
    }

    if not raw_text or not raw_text.strip():
        return default_result

    clean_text = raw_text.strip()
    detected_currency = _detect_currency(clean_text)

    # Match numeric ranges: e.g.
    # '€66,500 – €88,000'
    # '$150k - $200k'
    # '150 - 200k / year'
    # '66500 to 88000'
    # '120,000 - 150,000'
    range_pattern = re.compile(
        r"(?:[\$€£₹¥]?\s*)(\d[\d,\.]*\s*[kmKM]?)\s*(?:-|–|—|to)\s*(?:[\$€£₹¥]?\s*)(\d[\d,\.]*\s*[kmKM]?)",
        re.IGNORECASE,
    )

    match = range_pattern.search(clean_text)
    if match:
        min_str = match.group(1).strip()
        max_str = match.group(2).strip()
        # If max has 'k' and min does not, inherit 'k' (e.g. '150 - 200k')
        if (
            max_str.lower().endswith("k")
            and not min_str.lower().endswith("k")
            and not ("." in min_str or "," in min_str)
        ):
            try:
                if float(min_str) < 1000:
                    min_str = min_str + "k"
            except ValueError:
                pass

        val_min = _clean_number(min_str)
        val_max = _clean_number(max_str)

        if val_min and val_max and val_min > val_max:
            val_min, val_max = val_max, val_min

        period = _detect_period(clean_text, num_sample=val_max or val_min)

        return {
            "salary_min": val_min,
            "salary_max": val_max,
            "currency": detected_currency or "USD",
            "salary_period": period,
            "compensation_text": clean_text,
        }

    # Match single numbers (e.g. 'Up to $180,000', 'From $120k', '$85/hr')
    single_num_pattern = re.compile(
        r"(?:(?:up\s*to|max(?:imum)?)\s*[\$€£₹¥]?\s*|\b(?:from|min(?:imum)?)\s*[\$€£₹¥]?\s*|[\$€£₹¥]\s*)(\d[\d,\.]*\s*[kmKM]?)",
        re.IGNORECASE,
    )

    single_match = single_num_pattern.search(clean_text)
    if not single_match:
        # Fallback single number followed by currency or period
        fallback_pattern = re.compile(
            r"(\d[\d,\.]*\s*[kmKM]?)\s*(?:eur|usd|gbp|chf|sek|cad|aud|\/|per\s*(?:year|month|hour|annum))",
            re.IGNORECASE,
        )
        single_match = fallback_pattern.search(clean_text)

    if single_match:
        num_str = single_match.group(1).strip()
        val = _clean_number(num_str)
        if val:
            period = _detect_period(clean_text, num_sample=val)
            text_lower = clean_text.lower()
            if any(
                prefix in text_lower for prefix in ["up to", "max", "maximum", "upto"]
            ):
                return {
                    "salary_min": None,
                    "salary_max": val,
                    "currency": detected_currency or "USD",
                    "salary_period": period,
                    "compensation_text": clean_text,
                }
            elif any(
                prefix in text_lower
                for prefix in ["from", "min", "minimum", "starting"]
            ):
                return {
                    "salary_min": val,
                    "salary_max": None,
                    "currency": detected_currency or "USD",
                    "salary_period": period,
                    "compensation_text": clean_text,
                }
            else:
                return {
                    "salary_min": val,
                    "salary_max": val,
                    "currency": detected_currency or "USD",
                    "salary_period": period,
                    "compensation_text": clean_text,
                }

    return default_result
