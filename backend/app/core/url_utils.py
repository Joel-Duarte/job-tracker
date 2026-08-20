import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Query parameters that track sources, marketing, analytics, or referrals
TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_reader",
    "utm_referrer",
    "utm_name",
    "ref",
    "referrer",
    "reference",
    "source",
    "src",
    "from",
    "origin",
    "gclid",
    "fbclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "twclid",
    "yclid",
    "li_fat_id",
    "s_kwcid",
    "trk",
    "rc",
    "referralcode",
    "referral_code",
    "ref_id",
    "referral",
    "subid",
    "affiliate",
    "gh_src",
    "lever-origin",
    "lever-source",
    "ashby_jid",
    "ncid",
    "icid",
}


def normalize_job_url(url: str | None) -> str | None:
    """
    Normalizes a job posting URL to ensure consistent duplicate detection.
    - Strips leading/trailing whitespace.
    - Preserves non-HTTP/HTTPS placeholder strings (e.g. lead-*, clip-*, app-*).
    - Normalizes scheme (defaults to https if scheme is missing) and lowercases scheme & host.
    - Removes URL fragments (#...).
    - Removes trailing slashes from path unless path is root.
    - Filters out known tracking, analytics, and referral query parameters (e.g., utm_*, ref, source, gclid).
    - Preserves core job identifier query parameters (e.g. gh_jid, jobId, id, jk) and unrecognized params.
    - Alphabetically sorts remaining query parameters for canonical string matching.
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    # Preserve internal lead/app/clip placeholder strings
    if re.match(r"^(lead|app|clip|paste|test|msg)-", cleaned, re.IGNORECASE):
        return cleaned

    # Default scheme to https if missing (e.g. "company.com/jobs/123")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        cleaned = "https://" + cleaned

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return cleaned

    # Support http and https schemes
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()

    if not netloc:
        return url.strip()

    # Normalize path (remove trailing slashes unless path is empty or '/')
    path = parsed.path
    if path and path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Parse and filter query parameters
    filtered_query = []
    if parsed.query:
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        for k, v in pairs:
            k_lower = k.lower()
            if (
                k_lower.startswith("utm_")
                or k_lower.startswith("lkd_")
                or k_lower.startswith("trk_")
            ):
                continue
            if k_lower in TRACKING_QUERY_PARAMS:
                continue
            filtered_query.append((k, v))

    # Sort query parameters for canonical consistency
    filtered_query.sort(key=lambda item: (item[0], item[1]))
    new_query = urlencode(filtered_query) if filtered_query else ""

    # Reassemble URL without fragment
    normalized = urlunparse((scheme, netloc, path, parsed.params, new_query, ""))
    return normalized
