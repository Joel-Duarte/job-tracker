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
    "remoteok.com",
    "weworkremotely.com",
    "cord.co",
    "workingnomads.com",
    "startup.jobs",
    "remotive.com",
    "techstars.com",
    "join.com",
    "jobgether.com",
    "hired.com",
    "dice.com",
    "joinhandshake.com",
    "handshake.com",
    "themuse.com",
    "careerbuilder.com",
    "simplyhired.com",
    "snagajob.com",
    "adzuna.com",
    "stepstone.de",
    "totaljobs.com",
    "reed.co.uk",
    "jobsite.co.uk",
    "infojobs.net",
    "github.com",
    "reddit.com",
}


def _host_matches_domain(host: str, domain: str) -> bool:
    """Match an exact domain or one of its subdomains, never a lookalike suffix."""
    host = host.lower().rstrip(".")
    return host == domain or host.endswith(f".{domain}")


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
    """Checks if a given hostname belongs to a known ATS or job board."""
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


def is_aggregator_hostname(hostname: str, company_name: str | None = None) -> bool:
    """Checks if a given hostname belongs to a known ATS, aggregator, job board, media, or social platform."""
    if not hostname:
        return False

    clean_host = clean_domain(hostname)
    if not clean_host:
        return False

    if company_name and is_ats_vendor_match(company_name, clean_host):
        return False

    for agg in KNOWN_AGGREGATOR_DOMAINS:
        if clean_host == agg or clean_host.endswith(f".{agg}"):
            return True

    return False


def is_domain_match_for_company(domain: str | None, company_name: str | None) -> bool:
    """Checks whether a domain root or host plausibly matches a company name/slug,
    preventing job board or aggregator hostnames from being attributed to employers.
    """
    if not domain or not company_name:
        return False
    clean_d = clean_domain(domain)
    if not clean_d:
        return False

    # Extract primary label before first dot (e.g. 'stripe.com' -> 'stripe', 'datadoghq.com' -> 'datadoghq')
    domain_base = clean_d.split(".")[0].lower()
    norm_company = re.sub(r"[^a-z0-9]", "", company_name.lower())
    if not norm_company or not domain_base:
        return False

    # Exact or substring containment
    if norm_company in domain_base or domain_base in norm_company:
        return True

    # Token overlap for multi-word company names (e.g. "The Browser Company" -> "browser")
    company_tokens = [
        t
        for t in re.split(r"[^a-z0-9]+", company_name.lower())
        if len(t) >= 3
        and t
        not in {
            "the",
            "and",
            "inc",
            "llc",
            "ltd",
            "corp",
            "corporation",
            "group",
            "holdings",
            "company",
            "technologies",
            "technology",
            "tech",
            "labs",
            "software",
            "systems",
            "solutions",
            "global",
        }
    ]
    if any(token in domain_base for token in company_tokens):
        return True

    import difflib

    if difflib.SequenceMatcher(None, norm_company, domain_base).ratio() >= 0.7:
        return True

    return False


def extract_domain_from_url(
    url: str | None, company_name: str | None = None
) -> str | None:
    """Extracts the company domain from a job posting URL if it is not an ATS or aggregator (or if the company is the ATS vendor)."""
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

        # If it's a known ATS or job aggregator not caught above
        if is_aggregator_hostname(cleaned, company_name=company_name):
            return None

        # Strip standard subdomains like careers., jobs., info., app.
        parts = cleaned.split(".")
        candidate = cleaned
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
                candidate = ".".join(parts[1:])

        # If company_name is provided, ensure domain actually matches company
        if company_name and not is_domain_match_for_company(candidate, company_name):
            return None

        return candidate
    except Exception as e:
        logger.debug(f"Failed to parse domain from URL {url}: {e}")
        return None


def clean_company_name(raw_name: str | None) -> str:
    """Cleans and standardizes extracted company names by removing legal entity suffixes,
    recruitment suffixes, and extraneous formatting.
    """
    if not raw_name:
        return ""

    # Company labels are short; cap work on malformed extracted content.
    name = raw_name.strip()[:512]
    # Remove quotes, backticks, and brackets
    name = name.strip("\"'`([{)]}").strip()

    # Remove career / job portal suffixes
    portal_suffixes = (
        "job openings",
        "job opening",
        "careers",
        "jobs",
        "engineering",
        "hiring",
        "team",
    )
    name_lower = name.lower()
    for suffix in portal_suffixes:
        if name_lower.endswith(suffix):
            idx = len(name) - len(suffix)
            if idx > 0 and name[idx - 1] in " \t-–—:":
                prefix = name[:idx].rstrip(",.-:–— ").strip()
                if prefix:
                    name = prefix
                    name_lower = name.lower()
                    break

    # Remove common domain TLD suffixes when dot-attached (e.g., 'Zero.inc', 'Linear.app', 'Zero.io')
    dot_tlds = (
        ".inc",
        ".llc",
        ".ltd",
        ".corp",
        ".com",
        ".io",
        ".ai",
        ".app",
        ".dev",
        ".org",
        ".net",
        ".tech",
        ".co",
        ".so",
        ".sh",
        ".xyz",
        ".gg",
    )
    for tld in dot_tlds:
        if name_lower.endswith(tld) and len(name) > len(tld):
            prefix = name[: -len(tld)].rstrip(",.-:–— ").strip()
            if prefix:
                name = prefix
                name_lower = name.lower()
                break

    # Remove common legal entity suffixes
    legal_suffixes = (
        "corporation",
        "limited",
        "p.l.c.",
        "s.a.",
        "b.v.",
        "gmbh",
        "corp.",
        "corp",
        "inc.",
        "inc",
        "llc.",
        "llc",
        "ltd.",
        "ltd",
        "s.a",
        "b.v",
        "plc",
        "co.",
        "co",
        "sa",
        "bv",
    )
    for suffix in legal_suffixes:
        if name_lower.endswith(suffix):
            idx = len(name) - len(suffix)
            if idx > 0 and name[idx - 1] in " \t,.-/":
                prefix = name[:idx].rstrip(",.-:–— ").strip()
                if prefix:
                    name = prefix
                    name_lower = name.lower()
                    break

    # Clean trailing punctuation
    name = name.rstrip(",.-:–— ").strip()
    return name or raw_name.strip()[:512]


_EMAIL_IGNORE_DOMAINS = KNOWN_AGGREGATOR_DOMAINS | {
    "gmail.com",
    "googlemail.com",
    "google.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "yahoo.com",
    "ymail.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "proton.me",
    "protonmail.com",
    "aol.com",
    "zoho.com",
    "fastmail.com",
    "hey.com",
    "gmx.com",
    "mail.com",
    "sendgrid.net",
    "sendgrid.com",
    "mailgun.org",
    "mailgun.com",
    "mailchimp.com",
    "list-manage.com",
    "mandrillapp.com",
    "amazonses.com",
    "postmarkapp.com",
    "sparkpostmail.com",
    "customeriomail.com",
    "hubspotemail.net",
    "hubspot.com",
    "intercom-mail.com",
    "intercom.io",
    "calendly.com",
    "zoom.us",
    "microsoft.com",
    "office.com",
    "w3.org",
    "schema.org",
}

_EMAIL_SUBDOMAIN_PREFIXES = {
    "mail",
    "email",
    "em",
    "mg",
    "notifications",
    "notify",
    "no-reply",
    "noreply",
    "bounce",
    "bounces",
    "careers",
    "jobs",
    "job",
    "career",
    "talent",
    "recruiting",
    "recruitment",
    "hr",
    "apply",
    "hire",
    "hiring",
    "links",
    "click",
    "track",
    "t",
}

_HREF_URL_RE = re.compile(r'href=["\'](https?://[^"\'\s<>]+)["\']', re.IGNORECASE)
_PLAIN_URL_RE = re.compile(r'https?://[^\s<>"\'\)\]]+', re.IGNORECASE)
_EMAIL_ADDR_RE = re.compile(r"[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")


def _normalize_company_email_domain(raw_host: str | None) -> str | None:
    """Normalizes an email sender or link host to a canonical company root domain, filtering mail/ATS/tracker hosts."""
    cleaned = clean_domain(raw_host)
    if not cleaned:
        return None
    parts = cleaned.split(".")
    while len(parts) > 2 and parts[0] in _EMAIL_SUBDOMAIN_PREFIXES:
        parts = parts[1:]
    candidate = ".".join(parts)
    for ignored in _EMAIL_IGNORE_DOMAINS:
        if candidate == ignored or candidate.endswith(f".{ignored}"):
            return None
    if is_aggregator_hostname(candidate):
        return None
    return candidate


def extract_email_identity_signals(
    raw_body: str | None,
    sender: str | None = None,
    subject: str | None = None,
    extracted_data: dict | None = None,
) -> dict[str, list[str] | str | None]:
    """Deterministically extracts URLs, company domains, ATS org slugs, and cleaned company names from an email."""
    from app.core.url_utils import normalize_job_url

    extracted = extracted_data if isinstance(extracted_data, dict) else {}

    # 1. Sender domain
    sender_domain: str | None = None
    if sender:
        m = _EMAIL_ADDR_RE.search(sender)
        if m:
            sender_domain = _normalize_company_email_domain(m.group(1))

    # 2. Candidate URLs from newest part of raw_body (before quote blocks) + extracted job_url
    body_text = raw_body or ""
    quote_Match = re.search(
        r"<blockquote|<div[^>]*(?:gmail_quote|yahoo_quoted|divRplyFwdMsg)|^[ \t]*On\s+.+?\bwrote:\s*$",
        body_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    newest_segment = body_text[: quote_Match.start()] if quote_Match else body_text

    raw_urls: list[str] = []
    if extracted.get("job_url"):
        raw_urls.append(str(extracted["job_url"]))
    raw_urls.extend(_HREF_URL_RE.findall(newest_segment))
    raw_urls.extend(_PLAIN_URL_RE.findall(newest_segment))

    candidate_job_urls: list[str] = []
    candidate_domains: list[str] = []
    ats_slugs: list[str] = []
    seen_urls: set[str] = set()

    for u in raw_urls:
        u_clean = u.rstrip(".,;:!?)>'\"")
        u_lower = u_clean.lower()
        if any(
            skip in u_lower
            for skip in (
                "unsubscribe",
                "optout",
                "opt-out",
                "preferences",
                "privacy",
                "terms",
                "mailto:",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".css",
                ".js",
                ".woff",
                ".ico",
            )
        ):
            continue

        norm_u = normalize_job_url(u_clean) or u_clean
        if norm_u in seen_urls:
            continue
        seen_urls.add(norm_u)

        slug = extract_organization_from_ats_url(norm_u)
        if slug and slug not in ats_slugs:
            ats_slugs.append(slug)
            candidate_job_urls.append(norm_u)
            continue

        try:
            parsed = urlparse(norm_u)
            dom = _normalize_company_email_domain(parsed.netloc)
        except Exception:
            dom = None

        if dom:
            if dom not in candidate_domains:
                candidate_domains.append(dom)
            path_l = (parsed.path or "").lower()
            if norm_u == normalize_job_url(str(extracted.get("job_url") or "")) or any(
                k in path_l
                for k in ("/job", "/career", "/role", "/position", "/apply", "/opening")
            ):
                if norm_u not in candidate_job_urls:
                    candidate_job_urls.append(norm_u)

    if sender_domain and sender_domain not in candidate_domains:
        candidate_domains.append(sender_domain)

    raw_comp = str(
        extracted.get("company") or extracted.get("company_name") or ""
    ).strip()
    if raw_comp.lower() in {
        "unknown company",
        "unknown",
        "none",
        "null",
        "n/a",
        "not specified",
    }:
        raw_comp = ""
    cleaned_comp = clean_company_name(raw_comp) if raw_comp else None

    return {
        "sender_domain": sender_domain,
        "detected_domains": candidate_domains,
        "ats_slugs": ats_slugs,
        "candidate_job_urls": candidate_job_urls,
        "detected_job_url": candidate_job_urls[0] if candidate_job_urls else None,
        "cleaned_company": cleaned_comp,
    }


def extract_organization_from_ats_url(url: str | None) -> str | None:
    """Extracts the organization/company slug from an Applicant Tracking System (ATS) URL.
    Supports Greenhouse, Lever, Ashby, Workable, BambooHR, Rippling, Teamtailor, Recruitee,
    SmartRecruiters, and Jobvite.
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path.strip("/")
        parts = path.split("/") if path else []

        # Path-based org slug ATSs
        if any(
            _host_matches_domain(host, ats)
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
            if _host_matches_domain(host, ats_suffix):
                sub = host.split("." + ats_suffix)[0]
                if sub and sub not in {"jobs", "careers", "apply", "www"}:
                    return sub.split(".")[-1].lower()

        if _host_matches_domain(host, "jobvite.com") and parts and parts[0]:
            slug = parts[0].lower()
            if slug not in {"jobs", "careers"}:
                return slug

    except Exception as e:
        logger.debug("Failed to extract org slug from ATS URL %s: %s", url, e)

    return None


async def search_company_domain_and_about(
    company_name: str,
    ai_domain: str | None = None,
    db: AsyncSession | None = None,
) -> tuple[str | None, str | None]:
    """Searches for the company's official website using the configured search provider (SearXNG or DDGS).
    Cross-verifies with AI-extracted domain for high-confidence consensus and filters aggregators.
    Returns: (canonical_domain, discovered_about_url)
    """
    from app.services.web_search import search_web

    clean_name = clean_company_name(company_name)
    if not clean_name or len(clean_name) < 2:
        return None, None

    clean_ai = clean_domain(ai_domain) if ai_domain else None
    if clean_ai and is_aggregator_hostname(clean_ai, company_name=clean_name):
        clean_ai = None

    query = f'"{clean_name}" official website'
    try:
        results = await search_web(query, max_results=3, db=db)
    except Exception as e:
        logger.debug("Web search query failed for '%s': %s", clean_name, e)
        return clean_ai, None

    if not results:
        return clean_ai, None

    canonical_domain = None
    about_url = None

    # Pass 1: Check if any top search result confirms the AI domain
    if clean_ai:
        for res in results:
            r_url = res.get("url") or ""
            try:
                parsed = urlparse(r_url)
                r_host = clean_domain(parsed.netloc) or ""
                if (
                    r_host == clean_ai
                    or r_host.endswith(f".{clean_ai}")
                    or clean_ai.endswith(f".{r_host}")
                ):
                    canonical_domain = clean_ai
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
                        about_url = r_url
                    break
            except Exception:
                continue

    # Pass 2: If no AI consensus, take top non-aggregator matching result
    for res in results:
        r_url = res.get("url") or ""
        try:
            parsed = urlparse(r_url)
            r_host = clean_domain(parsed.netloc) or ""
            if not r_host:
                continue

            # Check if host is an aggregator or ATS
            if is_aggregator_hostname(r_host, company_name=clean_name):
                continue

            # Check semantic match with company name
            if not is_domain_match_for_company(r_host, clean_name):
                continue

            if not canonical_domain:
                canonical_domain = r_host

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

    if (
        not canonical_domain
        and clean_ai
        and is_domain_match_for_company(clean_ai, clean_name)
    ):
        canonical_domain = clean_ai

    return canonical_domain, about_url


async def query_clearbit_autocomplete(company_name: str) -> str | None:
    """Deprecated: Clearbit free autocomplete has been shut down / rate limited.
    Retained for signature compatibility; returns None.
    """
    return None


async def resolve_company_domain_and_about(
    company_name: str,
    source_url: str | None = None,
    ai_domain: str | None = None,
    allow_network: bool = True,
    db: AsyncSession | None = None,
) -> tuple[str | None, str | None]:
    """Resolves the official company domain and optional about_url using a prioritized multi-stage heuristic:

    1. Static known overrides (e.g. 'Linear' -> 'linear.app', 'Datadog' -> 'datadoghq.com', 'Ashby' -> 'ashbyhq.com')
    2. Direct URL extraction (if source URL is hosted directly on company site or is an ATS vendor posting for itself)
    3. Fast Web Search Verification + AI Consensus (searches via SearXNG/DDG, filtering aggregators)
    4. Validated ai_domain (if valid domain, not an aggregator, and matches company)
    5. Fallback clean slug domain (e.g. '{company_slug}.com')
    """
    if not company_name:
        return None, None

    cleaned_name = clean_company_name(company_name)
    norm_name = re.sub(r"[^a-z0-9]", "", cleaned_name.lower())
    if norm_name in KNOWN_COMPANY_OVERRIDES:
        return KNOWN_COMPANY_OVERRIDES[norm_name], None

    # Stage 1: Check direct URL if present, semantically matching, and not ATS/aggregator
    if source_url:
        direct_domain = extract_domain_from_url(source_url, company_name=cleaned_name)
        if direct_domain:
            return direct_domain, None

    # Stage 2: Web Search Verification + AI Consensus
    if allow_network:
        try:
            search_domain, about_url = await search_company_domain_and_about(
                cleaned_name, ai_domain=ai_domain, db=db
            )
            if search_domain:
                return search_domain, about_url
        except Exception as e:
            logger.debug(
                "Web search domain resolution failed for '%s': %s", cleaned_name, e
            )

    # Stage 3: Validate AI-extracted domain (only if not an aggregator and network search didn't find anything)
    if ai_domain:
        cleaned_ai = clean_domain(ai_domain)
        if cleaned_ai and not is_aggregator_hostname(
            cleaned_ai, company_name=cleaned_name
        ):
            if is_domain_match_for_company(cleaned_ai, cleaned_name):
                return cleaned_ai, None

    # Stage 4: Simple clean slug fallback
    if norm_name and len(norm_name) >= 2:
        return f"{norm_name}.com", None

    return None, None


async def resolve_company_domain(
    company_name: str,
    source_url: str | None = None,
    ai_domain: str | None = None,
    allow_network: bool = True,
    db: AsyncSession | None = None,
) -> str | None:
    """Resolves the official company domain using a prioritized multi-stage heuristic."""
    domain, _ = await resolve_company_domain_and_about(
        company_name=company_name,
        source_url=source_url,
        ai_domain=ai_domain,
        allow_network=allow_network,
        db=db,
    )
    return domain
