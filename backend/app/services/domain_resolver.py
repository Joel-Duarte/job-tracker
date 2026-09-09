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
from sqlalchemy.ext.asyncio import AsyncSession

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

# General aggregator domains, job boards, media, and encyclopedias that should NEVER be treated as a company domain
KNOWN_AGGREGATOR_DOMAINS = KNOWN_ATS_DOMAINS | {
    "wikipedia.org",
    "crunchbase.com",
    "levels.fyi",
    "bloomberg.com",
    "reuters.com",
    "forbes.com",
    "pitchbook.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "medium.com",
    "ycombinator.com",
    "businessinsider.com",
    "techcrunch.com",
}

# Mapping of canonical ATS vendor domain to set of normalized vendor name identifiers/aliases
ATS_VENDOR_DOMAINS: dict[str, set[str]] = {
    "ashbyhq.com": {"ashby", "ashbyhq", "ashbytechnologies"},
    "greenhouse.io": {"greenhouse", "greenhousesoftware"},
    "lever.co": {"lever"},
    "workday.com": {"workday"},
    "smartrecruiters.com": {"smartrecruiters"},
    "bamboohr.com": {"bamboohr"},
    "rippling.com": {"rippling"},
    "rippling-ats.com": {"rippling"},
    "jobvite.com": {"jobvite"},
    "icims.com": {"icims"},
    "workable.com": {"workable"},
    "breezy.hr": {"breezy", "breezyhr"},
    "jazzhr.com": {"jazzhr"},
    "pinpointhq.com": {"pinpoint", "pinpointhq"},
    "teamtailor.com": {"teamtailor"},
    "recruitee.com": {"recruitee"},
    "polymer.co": {"polymer"},
    "otta.com": {"otta"},
    "wellfound.com": {"wellfound", "angellist"},
    "linkedin.com": {"linkedin"},
    "indeed.com": {"indeed"},
    "glassdoor.com": {"glassdoor"},
    "ziprecruiter.com": {"ziprecruiter"},
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
    "ashby": "ashbyhq.com",
    "ashbyhq": "ashbyhq.com",
    "greenhouse": "greenhouse.io",
    "greenhousesoftware": "greenhouse.io",
    "lever": "lever.co",
    "workday": "workday.com",
    "smartrecruiters": "smartrecruiters.com",
    "bamboohr": "bamboohr.com",
    "rippling": "rippling.com",
    "jobvite": "jobvite.com",
    "icims": "icims.com",
    "workable": "workable.com",
    "breezyhr": "breezy.hr",
    "jazzhr": "jazzhr.com",
    "pinpoint": "pinpointhq.com",
    "teamtailor": "teamtailor.com",
    "recruitee": "recruitee.com",
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


def is_ats_vendor_match(company_name: str | None, domain_or_host: str | None) -> bool:
    """Checks whether the company name corresponds to the vendor of the given ATS domain."""
    if not company_name or not domain_or_host:
        return False
    norm_name = re.sub(r"[^a-z0-9]", "", company_name.lower())
    clean_host = clean_domain(domain_or_host) or domain_or_host.strip().lower()
    for ats_root, aliases in ATS_VENDOR_DOMAINS.items():
        if clean_host == ats_root or clean_host.endswith(f".{ats_root}"):
            if norm_name in aliases:
                return True
    return False


def is_ats_hostname(hostname: str, company_name: str | None = None) -> bool:
    """Checks if a given hostname belongs to a known ATS or job board.

    If company_name is provided and the company itself is the ATS vendor
    (e.g., 'Ashby' applying on 'jobs.ashbyhq.com'), returns False so the
    vendor's domain is not filtered out.
    """
    if not hostname:
        return False

    clean_host = clean_domain(hostname)
    if not clean_host:
        return False

    if company_name and is_ats_vendor_match(company_name, clean_host):
        return False

    for ats in KNOWN_ATS_DOMAINS:
        if clean_host == ats or clean_host.endswith(f".{ats}"):
            return True

    return False


def extract_domain_from_url(
    url: str | None, company_name: str | None = None
) -> str | None:
    """Extracts the company domain from a job posting URL if it is not an ATS (or if the company is the ATS vendor)."""
    if not url:
        return None

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path.split("/")[0]
        cleaned = clean_domain(netloc)
        if not cleaned:
            return None

        # Check if URL is an ATS URL where the vendor itself is the employer
        ats_slug = extract_organization_from_ats_url(url)
        norm_company = (
            re.sub(r"[^a-z0-9]", "", company_name.lower()) if company_name else None
        )

        for ats_root, aliases in ATS_VENDOR_DOMAINS.items():
            if cleaned == ats_root or cleaned.endswith(f".{ats_root}"):
                is_vendor = False
                if ats_slug and ats_slug.lower() in aliases:
                    is_vendor = True
                elif norm_company and norm_company in aliases:
                    is_vendor = True
                if is_vendor:
                    # Return the canonical root domain of the vendor
                    return ats_root
                # It's an ATS for a third-party company
                return None

        # If it's a known ATS or job board not caught above
        if is_ats_hostname(cleaned, company_name=company_name):
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


def clean_company_name(raw_name: str | None) -> str:
    """Cleans and standardizes extracted company names by removing legal entity suffixes,
    recruitment suffixes, and extraneous formatting.
    """
    if not raw_name:
        return ""

    name = raw_name.strip()
    # Remove quotes, backticks, and brackets
    name = re.sub(r"^[\"\'`\(\[\{]+|[\"\'`\)\]\}]+$", "", name).strip()

    # Remove career / job portal suffixes
    name = re.sub(
        r"\s*[-–—:]\s*(Careers|Jobs|Job\s+Openings?|Engineering|Hiring)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    name = re.sub(
        r"\s+(Careers|Jobs|Job\s+Openings?|Team)\s*$", "", name, flags=re.IGNORECASE
    ).strip()

    # Remove common legal entity suffixes: Inc, LLC, Ltd, Corp, Corporation, GmbH, S.A., B.V., Co.
    name = re.sub(
        r"[,.]?\s*\b(inc(\.|\b)|llc(\.|\b)|ltd(\.|\b)|limited\b|corp(\.|\b)|corporation\b|gmbh\b|s\.?a\.?\b|b\.?v\.?\b|co(\.|\b)|p\.?l\.?c\.?\b)\s*$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()

    # Clean trailing punctuation
    name = re.sub(r"[,.\-:–—]+$", "", name).strip()
    return name or raw_name.strip()


def extract_organization_from_ats_url(url: str | None) -> str | None:
    """Extracts the organization/company slug from an Applicant Tracking System (ATS) URL.
    Supports Greenhouse, Lever, Ashby, Workable, BambooHR, Rippling, Teamtailor, Recruitee,
    SmartRecruiters, and Jobvite.
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")
        parts = path.split("/") if path else []

        # Path-based org slug ATSs
        if any(
            ats in host
            for ats in (
                "greenhouse.io",
                "lever.co",
                "ashbyhq.com",
                "workable.com",
                "smartrecruiters.com",
            )
        ):
            if parts and parts[0]:
                slug = parts[0].lower()
                if slug not in {"jobs", "embed", "apply"}:
                    return slug
                elif len(parts) > 1 and parts[1]:
                    return parts[1].lower()

        # Subdomain-based org slug ATSs
        for ats_suffix in (
            "bamboohr.com",
            "rippling-ats.com",
            "teamtailor.com",
            "recruitee.com",
            "jobvite.com",
        ):
            if ats_suffix in host:
                sub = host.split("." + ats_suffix)[0]
                if sub and sub not in {"jobs", "careers", "apply", "www"}:
                    return sub.split(".")[-1].lower()

        if "jobvite.com" in host and parts and parts[0]:
            slug = parts[0].lower()
            if slug not in {"jobs", "careers"}:
                return slug

    except Exception as e:
        logger.debug("Failed to extract org slug from ATS URL %s: %s", url, e)

    return None


async def search_company_domain_and_about(
    company_name: str,
    db: AsyncSession | None = None,
) -> tuple[str | None, str | None]:
    """Searches for the company's official website using the configured search provider.
    Filters out aggregators, job boards, and social media.
    Returns: (canonical_domain, discovered_about_url)
    """
    from app.services.web_search import search_web

    clean_name = clean_company_name(company_name)
    if not clean_name or len(clean_name) < 2:
        return None, None

    query = f"{clean_name} official website"
    try:
        results = await search_web(query, max_results=7, db=db)
    except Exception as e:
        logger.debug("Web search query failed for '%s': %s", clean_name, e)
        return None, None

    if not results:
        return None, None

    canonical_domain = None
    about_url = None

    for res in results:
        r_url = res.get("url") or ""
        try:
            parsed = urlparse(r_url)
            r_host = parsed.netloc.lower()
            if r_host.startswith("www."):
                r_host = r_host[4:]

            # Check if host is an aggregator or ATS
            is_vendor = is_ats_vendor_match(clean_name, r_host)
            is_aggregator = (not is_vendor) and any(
                r_host == agg or r_host.endswith("." + agg)
                for agg in KNOWN_AGGREGATOR_DOMAINS
            )
            if is_aggregator:
                continue

            # First non-aggregator domain is our canonical corporate domain
            if not canonical_domain:
                canonical_domain = r_host

            # Check if this or subsequent result is an about page on the canonical domain
            if canonical_domain and (
                r_host == canonical_domain
                or r_host.endswith("." + canonical_domain)
                or canonical_domain.endswith("." + r_host)
            ):
                path = parsed.path.lower()
                if any(
                    x in path
                    for x in (
                        "/about",
                        "/about-us",
                        "/company",
                        "/our-story",
                        "/who-we-are",
                    )
                ) or r_host.startswith("about."):
                    if not about_url:
                        about_url = r_url

        except Exception:
            continue

    return canonical_domain, about_url


async def query_clearbit_autocomplete(company_name: str) -> str | None:
    """Queries Clearbit's public autocomplete API to find the company's official domain."""
    clean_name = clean_company_name(company_name)
    if not clean_name or len(clean_name) < 2:
        return None

    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(
                "https://autocomplete.clearbit.com/v1/companies/suggest",
                params={"query": clean_name},
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
    db: AsyncSession | None = None,
) -> str | None:
    """Resolves the official company domain using a prioritized multi-stage heuristic:

    1. Static known overrides (e.g. 'Linear' -> 'linear.app', 'Datadog' -> 'datadoghq.com', 'Ashby' -> 'ashbyhq.com')
    2. Direct URL extraction (if source URL is hosted directly on company site or is an ATS vendor posting for itself)
    3. Web Search Verification (searches for company official website via SearXNG/DDG, filtering aggregators)
    4. Clearbit autocomplete lookup (fallback)
    5. Validated ai_domain (if valid domain and not an ATS host unless company is the ATS vendor)
    6. Fallback clean slug domain (e.g. '{company_slug}.com')
    """
    if not company_name:
        return None

    cleaned_name = clean_company_name(company_name)
    norm_name = re.sub(r"[^a-z0-9]", "", cleaned_name.lower())
    if norm_name in KNOWN_COMPANY_OVERRIDES:
        return KNOWN_COMPANY_OVERRIDES[norm_name]

    # Stage 1: Check direct URL if present and not ATS (or if ATS is the employer)
    if source_url:
        direct_domain = extract_domain_from_url(source_url, company_name=cleaned_name)
        if direct_domain:
            return direct_domain

    # Stage 2: Web Search Verification (searches for company official website)
    if allow_network:
        try:
            search_domain, _ = await search_company_domain_and_about(
                cleaned_name, db=db
            )
            if search_domain:
                return search_domain
        except Exception as e:
            logger.debug(
                "Web search domain resolution failed for '%s': %s", cleaned_name, e
            )

        # Stage 3: Clearbit Autocomplete lookup
        clearbit_domain = await query_clearbit_autocomplete(cleaned_name)
        if clearbit_domain:
            return clearbit_domain

    # Stage 4: Validate AI-extracted domain (only if not an ATS and network search didn't find anything)
    if ai_domain:
        cleaned_ai = clean_domain(ai_domain)
        if cleaned_ai and not is_ats_hostname(cleaned_ai, company_name=cleaned_name):
            return cleaned_ai

    # Stage 5: Simple clean slug fallback
    if norm_name and len(norm_name) >= 2:
        return f"{norm_name}.com"

    return None
