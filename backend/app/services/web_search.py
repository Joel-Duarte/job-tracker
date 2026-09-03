import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scraper import scrape_job_url
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)


def _sync_ddgs_text(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Executes synchronous DDGS text search in a dedicated thread to avoid blocking asyncio loop."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS  # Fallback import

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            sanitized: list[dict[str, str]] = []
            for item in raw_results:
                title = str(item.get("title", "")).strip()[:150]
                body = str(item.get("body", "")).strip()[:350]
                href = str(item.get("href", "")).strip()
                if title or body:
                    sanitized.append(
                        {
                            "title": title,
                            "snippet": body,
                            "url": href,
                        }
                    )
            return sanitized
    except Exception as err:
        logger.warning("DuckDuckGo search query '%s' failed: %s", query, err)
        return []


async def search_web(
    query: str,
    max_results: int = 5,
    db: AsyncSession | None = None,
) -> list[dict[str, str]]:
    """
    Asynchronously queries DuckDuckGo and returns top sanitized search results.
    Bounded character limits prevent LLM context exhaustion.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    async with trace_operation(
        category="scraper",
        name="search_web",
        inputs={"query": clean_query, "max_results": max_results},
        db=db,
    ) as ctx:
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(_sync_ddgs_text, clean_query, max_results),
                timeout=12.0,
            )
            ctx["outputs"] = {
                "result_count": len(results),
                "urls": [r.get("url") for r in results if r.get("url")],
            }
            return results
        except TimeoutError:
            logger.warning("DuckDuckGo search timed out for query: %s", clean_query)
            ctx["error"] = "Search query timed out"
            return []
        except Exception as err:
            logger.error("Web search failed unexpectedly: %s", err)
            ctx["error"] = str(err)
            return []


async def fetch_webpage_content(
    url: str,
    max_chars: int = 4000,
    db: AsyncSession | None = None,
) -> str:
    """
    Scrapes and cleans webpage markdown/text from a target URL using Camofox with HTTP fallback.
    Safeguarded with SSRF validation and character bounding.
    """
    clean_url = url.strip()
    if not clean_url:
        return ""

    async with trace_operation(
        category="scraper",
        name="fetch_webpage_content",
        inputs={"url": clean_url, "max_chars": max_chars},
        db=db,
    ) as ctx:
        try:
            scraped = await scrape_job_url(clean_url, timeout_seconds=15.0)
            text_content = scraped.text.strip() if scraped and scraped.text else ""
            if len(text_content) > max_chars:
                text_content = (
                    text_content[:max_chars] + "\n\n... [Truncated for brevity]"
                )

            ctx["outputs"] = {
                "title": scraped.title if scraped else "",
                "char_count": len(text_content),
                "scraped_via": scraped.scraped_via if scraped else "unknown",
            }
            return text_content
        except Exception as err:
            logger.warning("Failed to fetch webpage content for %s: %s", clean_url, err)
            ctx["error"] = str(err)
            return ""
