import asyncio
import logging
import re

import httpx
from app.core.config import settings
from bs4 import BeautifulSoup
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# In-browser evaluation script executed inside Camofox (Firefox)
EXPAND_JS = """
(() => {
    try {
        // Scroll to trigger lazy loading
        window.scrollTo(0, document.body.scrollHeight / 3);

        // 1. Dismiss common cookie banners and consent overlays
        const dialogSelectors = [
            '[role="dialog"]', '.cookie-banner', '.consent-banner', '#onetrust-consent-sdk',
            '.modal-backdrop', '.cc-banner', '#cookie-notice', '.cookie-notice', '#onetrust-banner-sdk',
            '.msg-overlay-list-bubble', '#didomi-notice'
        ];
        dialogSelectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                try { el.remove(); } catch(e) {}
            });
        });

        // 2. Expand truncated job description buttons (LinkedIn, Lever, Greenhouse, Indeed, etc.)
        const expandKeywords = [
            'show more', 'read more', 'see more', 'view more', 'view full description',
            'read full job description', 'expand description', 'show entire description',
            'read all', 'show full description'
        ];

        // LinkedIn specific "Show more" button inside job description
        const linkedinBtn = document.querySelector('button.show-more-less-html__button');
        if (linkedinBtn) {
            try { linkedinBtn.click(); } catch(e) {}
        }

        const buttons = Array.from(document.querySelectorAll('button, a, [role="button"], span'));
        let clicked = false;
        for (const btn of buttons) {
            const txt = (btn.innerText || btn.textContent || '').trim().toLowerCase();
            if (expandKeywords.some(k => txt === k || (txt.length < 40 && txt.includes(k)))) {
                try {
                    btn.click();
                    clicked = true;
                } catch (e) {}
            }
        }
        return clicked;
    } catch(err) {
        return false;
    }
})()
"""

EXTRACT_JS = """
(() => {
    try {
        // 3. Remove non-content clutter: scripts, styles, SVGs, nav, footer, headers
        const clutter = document.querySelectorAll('script, style, noscript, svg, nav, footer, header, iframe, canvas, aside, form');
        clutter.forEach(el => {
            try { el.remove(); } catch(e) {}
        });

        // 4. Extract primary content if present, otherwise body text
        const mainSelectors = [
            'main', '[role="main"]', 'article',
            '#job-description', '#job-details', '.job-description',
            '.posting-content', '.job-details', '.description',
            '[data-test="job-description"]', '.core-section-container',
            '.show-more-less-html__markup'
        ];

        let target = null;
        for (const sel of mainSelectors) {
            const el = document.querySelector(sel);
            if (el && el.innerText.trim().length > 150) {
                target = el;
                break;
            }
        }
        if (!target) {
            target = document.body;
        }

        const text = target ? (target.innerText || target.textContent || '') : '';
        const title = document.title || '';

        return JSON.stringify({
            title: title,
            text: text
        });
    } catch(err) {
        return JSON.stringify({
            title: document.title || '',
            text: document.body ? (document.body.innerText || '') : '',
            error: String(err)
        });
    }
})()
"""


class ScrapedJobContent(BaseModel):
    title: str = ""
    text: str = ""
    source_url: str
    scraped_via: str  # "camofox" or "http_fallback"


def clean_extracted_text(raw_text: str, max_chars: int = 15000) -> str:
    """Normalizes whitespace and removes noise lines from scraped web text."""
    if not raw_text:
        return ""
    # Normalize unicode spaces and consecutive blank lines
    text = re.sub(r"[ \t]+", " ", raw_text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    # Strip leading/trailing lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned = "\n".join(lines)
    return cleaned[:max_chars]


async def _scrape_via_camofox(
    url: str, timeout_seconds: float = 25.0
) -> ScrapedJobContent | None:
    """Scrapes a URL using the running Camofox browser automation server."""
    base_url = settings.CAMOUFOX_ENDPOINT.rstrip("/")
    user_id = "job-tracker"
    tab_id: str | None = None

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            # 1. Open tab and initiate navigation
            open_resp = await client.post(
                f"{base_url}/tabs/open",
                json={"userId": user_id, "url": url},
            )
            if open_resp.status_code != 200:
                logger.warning(
                    "Camofox /tabs/open failed (%d): %s",
                    open_resp.status_code,
                    open_resp.text,
                )
                return None

            open_data = open_resp.json()
            tab_id = open_data.get("tabId") or open_data.get("targetId")
            if not tab_id:
                logger.warning("Camofox returned no tabId: %s", open_data)
                return None

            # 2. Wait for page hydration & dynamic client scripts
            await asyncio.sleep(3.0)

            # 3. Evaluate script to click 'show more' and dismiss banners
            await client.post(
                f"{base_url}/tabs/{tab_id}/evaluate",
                json={"userId": user_id, "expression": EXPAND_JS},
            )

            # Wait for content to expand or load
            await asyncio.sleep(2.0)

            # 4. Evaluate extraction script
            eval_resp = await client.post(
                f"{base_url}/tabs/{tab_id}/evaluate",
                json={"userId": user_id, "expression": EXTRACT_JS},
            )

            if eval_resp.status_code == 200:
                eval_data = eval_resp.json()
                raw_eval_result = eval_data.get("result", "")
                if isinstance(raw_eval_result, str) and raw_eval_result.startswith("{"):
                    import json

                    try:
                        parsed = json.loads(raw_eval_result)
                        page_title = parsed.get("title", "")
                        page_text = clean_extracted_text(parsed.get("text", ""))
                        if page_text:
                            logger.info(
                                "Successfully scraped %s via Camofox (%d chars)",
                                url,
                                len(page_text),
                            )
                            return ScrapedJobContent(
                                title=page_title,
                                text=page_text,
                                source_url=url,
                                scraped_via="camofox",
                            )
                    except Exception as parse_err:
                        logger.warning(
                            "Failed parsing Camofox JS result: %s", parse_err
                        )

    except Exception as err:
        logger.warning("Camofox scraping error for %s: %s", url, err)
    finally:
        # 5. Always close the tab to prevent leaks
        if tab_id:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.delete(f"{base_url}/tabs/{tab_id}?userId={user_id}")
            except Exception as close_err:
                logger.debug(
                    "Non-fatal error closing Camofox tab %s: %s", tab_id, close_err
                )

    return None


async def _scrape_via_http_fallback(
    url: str, timeout_seconds: float = 15.0
) -> ScrapedJobContent:
    """Fallback HTTP scraper using realistic Firefox desktop headers and BeautifulSoup cleaning."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(
        timeout=timeout_seconds, follow_redirects=True
    ) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            raise httpx.HTTPError(f"HTTP fetch failed with status {resp.status_code}")

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(
            ["script", "style", "noscript", "svg", "nav", "footer", "header", "iframe"]
        ):
            tag.decompose()

        title = soup.title.string if soup.title else ""
        main_el = soup.find(
            ["main", "article", "div"],
            class_=re.compile(r"job|posting|description", re.IGNORECASE),
        )
        raw_text = (
            main_el.get_text(separator="\n")
            if main_el
            else soup.get_text(separator="\n")
        )
        cleaned_text = clean_extracted_text(raw_text)

        logger.info(
            "Successfully scraped %s via HTTP fallback (%d chars)",
            url,
            len(cleaned_text),
        )
        return ScrapedJobContent(
            title=title or "",
            text=cleaned_text,
            source_url=url,
            scraped_via="http_fallback",
        )


async def scrape_job_url(url: str, timeout_seconds: float = 25.0) -> ScrapedJobContent:
    """
    Central scraping gateway.
    First attempts stealth browser execution via Camofox (clicks 'Show more', waits for dynamic hydration).
    If Camofox is offline or fails, falls back to direct HTTP request with BeautifulSoup parsing.
    """
    cleaned_url = url.strip()
    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = f"https://{cleaned_url}"

    # 1. Attempt Camofox stealth scraper
    camofox_result = await _scrape_via_camofox(
        cleaned_url, timeout_seconds=timeout_seconds
    )
    if camofox_result and len(camofox_result.text.strip()) > 100:
        return camofox_result

    # 2. Fallback to direct HTTP request
    logger.info("Falling back to HTTP fetch for URL: %s", cleaned_url)
    try:
        return await _scrape_via_http_fallback(
            cleaned_url, timeout_seconds=min(timeout_seconds, 15.0)
        )
    except Exception as fallback_err:
        logger.error(
            "Both Camofox and HTTP fallback failed for %s: %s",
            cleaned_url,
            fallback_err,
        )
        # Return empty content with error note rather than crashing ungracefully
        return ScrapedJobContent(
            title="",
            text="",
            source_url=cleaned_url,
            scraped_via="failed",
        )
