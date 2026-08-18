"""Domain resolution service for extracting and discovering official company website domains.

Uses a multi-tier resolution strategy:
1. Direct URL parsing (extracts domain if the job URL is hosted on the company's own site)
2. ATS detection (filters out third-party ATS hosts like Greenhouse, Lever, Ashby, Workday)
3. AI-extracted domain validation
4. Clearbit Autocomplete API lookup as a non-blocking fallback
"""

import logging
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Known Applicant Tracking Systems (ATS) and job boards
KNOWN_ATS_DOMAINS = {
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workday.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "jobvite.com",
    "icims.com",
    "rippling-ats.com",
    "recruitee.com",
    "applytojob.com",
    "workable.com",
    "breezy.hr",
    "jazzhr.com",
    "pinpointhq.com",
    "teamtailor.com",
    "polymer.co",
    "otta.com",
    "wellfound.com",
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "monster.com",
    "builtin.com",
}

# Static high-confidence domain overrides for common tech employers
KNOWN_COMPANY_OVERRIDES = {
    "stripe": "stripe.com",
    "linear": "linear.app",
    "figma": "figma.com",
    "datadog": "datadoghq.com",
    "airbnb": "airbnb.com",
    "google": "google.com",
    "apple": "apple.com",
    "microsoft": "microsoft.com",
    "amazon": "amazon.com",
    "meta": "meta.com",
    "netflix": "netflix.com",
    "uber": "uber.com",
    "spotify": "spotify.com",
    "notion": "notion.so",
    "slack": "slack.com",
    "github": "github.com",
    "gitlab": "gitlab.com",
    "vercel": "vercel.com",
    "supabase": "supabase.com",
    "postman": "postman.com",
    "openai": "openai.com",
    "anthropic": "anthropic.com",
    "canva": "canva.com",
    "snowflake": "snowflake.com",
    "cloudflare": "cloudflare.com",
    "discord": "discord.com",
    "zoom": "zoom.us",
    "atlassian": "atlassian.com",
}


def clean_domain(raw: str | None) -> str | None:
    """Sanitizes raw domain strings into clean root domains (e.g. 'https://www.stripe.com/jobs' -> 'stripe.com')."""
    if not raw or not isinstance(raw, str):
        return None

    cleaned = raw.strip().lower()
    if not cleaned:
        return None

    # Strip protocol
    cleaned = re.sub(r"^https?://", "", cleaned)
    # Strip paths, query params, hash
    cleaned = cleaned.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
    # Strip leading www.
    cleaned = re.sub(r"^www\.", "", cleaned)

    # Validate basic domain format (must contain at least one dot and valid chars)
    if "." in cleaned and re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", cleaned):
        return cleaned

    return None


def is_ats_hostname(hostname: str) -> bool:
    """Checks if a given hostname belongs to a known ATS or job board."""
    if not hostname:
        return False

    clean_host = clean_domain(hostname)
    if not clean_host:
        return False

    for ats in KNOWN_ATS_DOMAINS:
        if clean_host == ats or clean_host.endswith(f".{ats}"):
            return True

    return False


def extract_domain_from_url(url: str | None) -> str | None:
    """Extracts the company domain from a job posting URL if it is not an ATS."""
    if not url:
        return None

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path.split("/")[0]
        cleaned = clean_domain(netloc)
        if not cleaned:
            return None

        # If it's a known ATS or job board, we cannot treat the hostname as the company domain
        if is_ats_hostname(cleaned):
            return None

        # Strip standard subdomains like careers., jobs., info., app.
        parts = cleaned.split(".")
        if len(parts) > 2:
            subdomain = parts[0]
            if subdomain in {
                "careers",
                "jobs",
                "job",
                "career",
                "apply",
                "about",
                "work",
                "join",
                "app",
            }:
                return ".".join(parts[1:])

        return cleaned
    except Exception as e:
        logger.debug(f"Failed to parse domain from URL {url}: {e}")
        return None


async def query_clearbit_autocomplete(company_name: str) -> str | None:
    """Queries Clearbit's public autocomplete API to find the company's official domain."""
    if not company_name or len(company_name.strip()) < 2:
        return None

    cleaned_name = re.sub(
        r"[,.]?\s*(inc|llc|ltd|corp|co|gmbh|sa|bv)\.?$",
        "",
        company_name.strip(),
        flags=re.I,
    ).strip()
    if not cleaned_name:
        cleaned_name = company_name.strip()

    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(
                "https://autocomplete.clearbit.com/v1/companies/suggest",
                params={"query": cleaned_name},
                headers={"User-Agent": "JobTracker/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    first_match = data[0]
                    domain = first_match.get("domain")
                    if domain:
                        return clean_domain(domain)
    except Exception as e:
        logger.debug(
            f"Clearbit autocomplete lookup skipped/failed for '{company_name}': {e}"
        )

    return None


async def resolve_company_domain(
    company_name: str,
    source_url: str | None = None,
    ai_domain: str | None = None,
    allow_network: bool = True,
) -> str | None:
    """Resolves the official company domain using a prioritized multi-stage heuristic.

    1. Static known overrides (e.g. 'Linear' -> 'linear.app', 'Datadog' -> 'datadoghq.com')
    2. Direct URL extraction (if source URL is hosted directly on company site, e.g. 'stripe.com/jobs')
    3. AI-extracted domain validation (if valid domain and not an ATS host)
    4. Clearbit autocomplete lookup (non-blocking external API check)
    5. Fallback slug domain (e.g. '{company_slug}.com')
    """
    if not company_name:
        return None

    norm_name = re.sub(r"[^a-z0-9]", "", company_name.lower())
    if norm_name in KNOWN_COMPANY_OVERRIDES:
        return KNOWN_COMPANY_OVERRIDES[norm_name]

    # Stage 1: Check direct URL if present and not ATS
    if source_url:
        direct_domain = extract_domain_from_url(source_url)
        if direct_domain:
            return direct_domain

    # Stage 2: Validate AI-extracted domain
    if ai_domain:
        cleaned_ai = clean_domain(ai_domain)
        if cleaned_ai and not is_ats_hostname(cleaned_ai):
            return cleaned_ai

    # Stage 3: Clearbit Autocomplete lookup
    if allow_network:
        clearbit_domain = await query_clearbit_autocomplete(company_name)
        if clearbit_domain:
            return clearbit_domain

    # Stage 4: Simple clean slug fallback
    if norm_name and len(norm_name) >= 2:
        return f"{norm_name}.com"

    return None
