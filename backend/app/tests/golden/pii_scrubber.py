"""Deterministic PII scrubbing & verification helpers for building golden datasets from local DB data."""

from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,3}\d{3,4}(?!\d)"
)
_SOCIAL_HANDLE_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:linkedin\.com/in|github\.com|gitlab\.com|x\.com|twitter\.com)/[^\s)\"'>]+",
    re.IGNORECASE,
)
_GENERIC_URL_RE = re.compile(r"https?://[^\s)\"'>]+", re.IGNORECASE)
_DATA_URI_RE = re.compile(r"data:[a-z]+/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=]+", re.I)
_SIGNATURE_RE = re.compile(
    r"(?im)^(?:best\s+regards|warm\s+regards|kind\s+regards|sincerely|thanks|cheers),?\s*\n+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b"
)


def scrub_pii(
    text: str | None,
    *,
    extra_terms: list[str] | None = None,
    keep_urls: bool = False,
) -> tuple[str, dict[str, int]]:
    """Scrub emails, phone numbers, social profile URLs, signatures, and explicit terms from text."""
    if not text:
        return "", {}

    counts: dict[str, int] = {}
    cleaned = str(text)

    cleaned, n_data = _DATA_URI_RE.subn("[DATA_URI]", cleaned)
    if n_data:
        counts["data_uri"] = n_data

    cleaned, n_social = _SOCIAL_HANDLE_URL_RE.subn("[SOCIAL_PROFILE_URL]", cleaned)
    if n_social:
        counts["social_url"] = n_social

    if not keep_urls:
        cleaned, n_url = _GENERIC_URL_RE.subn("[URL]", cleaned)
        if n_url:
            counts["url"] = n_url

    cleaned, n_email = _EMAIL_RE.subn("[EMAIL]", cleaned)
    if n_email:
        counts["email"] = n_email

    def _replace_phone(match: re.Match[str]) -> str:
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        # Skip short year ranges or salary tokens (fewer than 9 digits)
        if len(digits) < 9 or len(digits) > 15:
            return raw
        counts["phone"] = counts.get("phone", 0) + 1
        return "[PHONE]"

    cleaned = _PHONE_RE.sub(_replace_phone, cleaned)

    cleaned, n_sig = _SIGNATURE_RE.subn("Best regards,\n[PERSON]", cleaned)
    if n_sig:
        counts["signature"] = n_sig

    for term in extra_terms or []:
        t = str(term or "").strip()
        if len(t) < 3:
            continue
        pat = re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE)
        cleaned, n_term = pat.subn("[REDACTED]", cleaned)
        if n_term:
            counts["custom_term"] = counts.get("custom_term", 0) + n_term

    return cleaned, counts


def scrub_nested(
    value: Any,
    *,
    extra_terms: list[str] | None = None,
    keep_urls: bool = False,
) -> Any:
    """Recursively scrub PII from strings inside nested lists and dicts."""
    if isinstance(value, str):
        scrubbed, _ = scrub_pii(value, extra_terms=extra_terms, keep_urls=keep_urls)
        return scrubbed
    if isinstance(value, list):
        return [
            scrub_nested(v, extra_terms=extra_terms, keep_urls=keep_urls) for v in value
        ]
    if isinstance(value, dict):
        return {
            k: scrub_nested(v, extra_terms=extra_terms, keep_urls=keep_urls)
            for k, v in value.items()
        }
    return value


def find_residual_pii(text: str | None) -> list[str]:
    """Return any surviving high-risk PII pattern labels found in scrubbed text."""
    if not text:
        return []
    findings: list[str] = []
    if _EMAIL_RE.search(text):
        findings.append("email")
    if _SOCIAL_HANDLE_URL_RE.search(text):
        findings.append("social_profile_url")
    for m in _PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 9 <= len(digits) <= 15:
            findings.append("phone")
            break
    return findings
