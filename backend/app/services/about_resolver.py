"""Dedicated About Us URL discovery service.

Inspects company homepage navigation/footer links and falls back to site-restricted web search
to locate the authentic company / about us page.
"""

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.domain_resolver import clean_domain
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)

ABOUT_LINK_KEYWORDS = {
    "about",
    "about us",
    "our story",
    "who we are",
    "company",
    "our company",
    "about the company",
    "mission",
    "values",
    "about us.",
}

ABOUT_PATH_PATTERNS = [
    re.compile(r"^/([a-z]{2}(-[a-z]{2})?/)?about(-us|us)?/?$", re.I),
    re.compile(r"^/([a-z]{2}(-[a-z]{2})?/)?company/?$", re.I),
    re.compile(r"^/([a-z]{2}(-[a-z]{2})?/)?our-story/?$", re.I),
    re.compile(r"^/([a-z]{2}(-[a-z]{2})?/)?who-we-are/?$", re.I),
]


def is_permissive_domain_match(candidate_url: str, root_domain: str) -> bool:
    """Checks if candidate_url belongs to the root_domain or its subdomains."""
    if not candidate_url or not root_domain:
        return False
    try:
        parsed = urlparse(candidate_url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        clean_root = clean_domain(root_domain)
        if not clean_root:
            return False
        return host == clean_root or host.endswith("." + clean_root)
    except Exception:
        return False


async def resolve_company_about_url(
    domain: str,
    db: AsyncSession | None = None,
) -> str | None:
    """Discovers the authentic 'About Us' page URL for a company domain.

    1. Fetches homepage HTML and parses navigation/footer anchor tags.
    2. Falls back to site-restricted web search: site:{domain} ("about us" OR "about" OR "our story").
    3. Default fallback: https://{domain}/about.
    """
    clean_dom = clean_domain(domain)
    if not clean_dom or "." not in clean_dom:
        return None

    async with trace_operation(
        category="scraper",
        name="resolve_company_about_url",
        inputs={"domain": clean_dom},
        db=db,
    ) as ctx:
        homepage_url = f"https://{clean_dom}"

        # Tier 1: Fetch homepage HTML and inspect links
        candidate_links: list[tuple[int, str]] = []
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            async with httpx.AsyncClient(
                timeout=8.0, follow_redirects=True, headers=headers
            ) as client:
                resp = await client.get(homepage_url)
                if resp.status_code < 400 and resp.text:
                    final_base_url = str(resp.url)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        if not href or href.startswith(
                            ("#", "mailto:", "javascript:", "tel:")
                        ):
                            continue
                        resolved = urljoin(final_base_url, href)
                        if not is_permissive_domain_match(resolved, clean_dom):
                            continue

                        text = a.get_text(strip=True).lower()
                        path = urlparse(resolved).path.lower()

                        # Priority scoring
                        if text in {"about", "about us"} or any(
                            p.match(path) for p in ABOUT_PATH_PATTERNS[:1]
                        ):
                            candidate_links.append((1, resolved))
                        elif text in ABOUT_LINK_KEYWORDS or any(
                            p.match(path) for p in ABOUT_PATH_PATTERNS[1:]
                        ):
                            candidate_links.append((2, resolved))
                        elif urlparse(resolved).netloc.lower().startswith("about."):
                            candidate_links.append((3, resolved))
                        elif "/about" in path:
                            candidate_links.append((4, resolved))

            if candidate_links:
                candidate_links.sort(key=lambda x: x[0])
                best_url = candidate_links[0][1]
                ctx["outputs"] = {
                    "discovered_url": best_url,
                    "method": "homepage_html_links",
                }
                return best_url

        except Exception as e:
            logger.debug(
                "Failed to extract about link from homepage HTML for %s: %s",
                clean_dom,
                e,
            )

        # Tier 2: Site-restricted web search
        try:
            from app.services.web_search import search_web

            search_query = f'site:{clean_dom} ("about us" OR "about" OR "our story" OR "who we are" OR "company")'
            search_results = await search_web(search_query, max_results=5, db=db)
            if search_results:
                for res in search_results:
                    s_url = res.get("url")
                    if s_url and is_permissive_domain_match(s_url, clean_dom):
                        s_path = urlparse(s_url).path.lower()
                        if any(
                            k in s_path
                            for k in (
                                "/about",
                                "/company",
                                "/our-story",
                                "/who-we-are",
                                "/mission",
                            )
                        ) or urlparse(s_url).netloc.lower().startswith("about."):
                            ctx["outputs"] = {
                                "discovered_url": s_url,
                                "method": "site_search",
                            }
                            return s_url
        except Exception as search_err:
            logger.debug(
                "Site search for about URL failed for %s: %s", clean_dom, search_err
            )

        # Tier 3: Standard fallback
        fallback_url = f"https://{clean_dom}/about"
        ctx["outputs"] = {
            "discovered_url": fallback_url,
            "method": "default_fallback",
        }
        return fallback_url
