import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scraper import scrape_job_url
from app.services.telemetry import trace_operation
from app.services.web_limiter import web_operation_limiter

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


async def _query_searxng(
    query: str, searxng_url: str, max_results: int = 5
) -> list[dict[str, str]]:
    """Asynchronously queries SearXNG JSON API endpoint with timeout."""
    import httpx

    clean_url = searxng_url.strip().rstrip("/")
    search_endpoint = f"{clean_url}/search"
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        resp = await client.get(
            search_endpoint,
            params={"q": query, "format": "json"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        raw_results = data.get("results", []) if isinstance(data, dict) else []
        sanitized: list[dict[str, str]] = []
        for item in raw_results[:max_results]:
            title = str(item.get("title", "")).strip()[:150]
            content = str(item.get("content", "") or item.get("snippet", "")).strip()[
                :350
            ]
            href = str(item.get("url", "")).strip()
            if title or content:
                sanitized.append(
                    {
                        "title": title,
                        "snippet": content,
                        "url": href,
                    }
                )
        return sanitized


async def validate_searxng_connection(searxng_url: str) -> tuple[bool, str, float]:
    """Validates SearXNG instance connectivity and JSON format availability."""
    import httpx

    clean_url = searxng_url.strip().rstrip("/")
    if not clean_url:
        return False, "SearXNG URL is empty", 0.0

    test_url = f"{clean_url}/search"
    start_time = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            response = await client.get(
                test_url,
                params={"q": "test", "format": "json"},
                headers={"Accept": "application/json"},
            )
            latency_ms = round((time.monotonic() - start_time) * 1000, 1)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "results" in data:
                    return (
                        True,
                        f"SearXNG connection successful ({latency_ms}ms)",
                        latency_ms,
                    )
                return (
                    False,
                    "SearXNG responded with HTTP 200 but JSON output format is not enabled in settings.yml",
                    latency_ms,
                )
            elif response.status_code in (403, 406):
                return (
                    False,
                    f"SearXNG responded with HTTP {response.status_code}: JSON format may be disabled in settings.yml (search.formats: [html, json])",
                    latency_ms,
                )
            else:
                return (
                    False,
                    f"SearXNG responded with HTTP {response.status_code}",
                    latency_ms,
                )
    except httpx.ConnectError:
        latency_ms = round((time.monotonic() - start_time) * 1000, 1)
        return (
            False,
            f"Unable to connect to SearXNG at {clean_url}. Check host, port, and network reachability.",
            latency_ms,
        )
    except httpx.TimeoutException:
        latency_ms = round((time.monotonic() - start_time) * 1000, 1)
        return (
            False,
            f"Connection to SearXNG at {clean_url} timed out (> 6s).",
            latency_ms,
        )
    except Exception as exc:
        latency_ms = round((time.monotonic() - start_time) * 1000, 1)
        return False, f"SearXNG check failed: {exc}", latency_ms


async def resolve_search_provider_settings(
    db: AsyncSession | None = None,
) -> tuple[str, str | None]:
    """Resolves effective search provider and searxng_url from system settings."""
    from app.core.config_manager import load_settings

    try:
        settings = await load_settings(db)
        provider = str(settings.get("search_provider") or "automatic").strip().lower()
        searxng_url = settings.get("searxng_url")
        if isinstance(searxng_url, str):
            searxng_url = searxng_url.strip() or None

        if provider == "automatic":
            if searxng_url:
                return "searxng", searxng_url
            return "ddgs", None
        elif provider == "searxng":
            return "searxng", searxng_url
        else:
            return "ddgs", None
    except Exception as err:
        logger.debug(
            "Could not load search provider settings, defaulting to ddgs: %s", err
        )
        return "ddgs", None


async def search_web(
    query: str,
    max_results: int = 5,
    db: AsyncSession | None = None,
    concurrency_limit: int = 1,
) -> list[dict[str, str]]:
    """
    Asynchronously queries configured search provider (SearXNG or DDGS) and returns top sanitized results.
    Automatically falls back to DDGS if SearXNG is unavailable, logging telemetry traces.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    target_provider, searxng_url = await resolve_search_provider_settings(db)

    async with trace_operation(
        category="scraper",
        name="search_web",
        inputs={
            "query": clean_query,
            "max_results": max_results,
            "configured_provider": target_provider,
        },
        db=db,
    ) as ctx:
        results: list[dict[str, str]] = []
        provider_used = target_provider
        fallback_occurred = False

        if target_provider == "searxng" and searxng_url:
            try:
                async with web_operation_limiter.acquire("searxng", concurrency_limit):
                    results = await _query_searxng(
                        clean_query, searxng_url, max_results
                    )
                if results:
                    provider_used = "searxng"
                else:
                    logger.info(
                        "SearXNG returned 0 results for '%s'; falling back to DuckDuckGo",
                        clean_query,
                    )
                    fallback_occurred = True
                    provider_used = "ddgs"
            except Exception as searx_err:
                logger.warning(
                    "SearXNG query failed (%s); falling back to DuckDuckGo for '%s'",
                    searx_err,
                    clean_query,
                )
                fallback_occurred = True
                provider_used = "ddgs"

        if not results and (target_provider == "ddgs" or fallback_occurred):
            try:
                async with web_operation_limiter.acquire("ddgs", concurrency_limit):
                    results = await asyncio.wait_for(
                        asyncio.to_thread(_sync_ddgs_text, clean_query, max_results),
                        timeout=12.0,
                    )
                provider_used = "ddgs"
            except TimeoutError:
                logger.warning("DuckDuckGo search timed out for query: %s", clean_query)
                ctx["error"] = "Search query timed out"
            except Exception as err:
                logger.error("DuckDuckGo search failed unexpectedly: %s", err)
                ctx["error"] = str(err)

        ctx["outputs"] = {
            "result_count": len(results),
            "provider_used": provider_used,
            "fallback_occurred": fallback_occurred,
            "urls": [r.get("url") for r in results if r.get("url")],
        }
        return results


async def fetch_webpage_content(
    url: str,
    max_chars: int = 4000,
    db: AsyncSession | None = None,
    concurrency_limit: int = 1,
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
            async with web_operation_limiter.acquire("camofox", concurrency_limit):
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
