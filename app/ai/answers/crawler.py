"""
Crawler: find pages that should contain the answer to a question.

Several sources are asked at once (``CRAWLER_SOURCES``) and their pages are
merged, best first:

* Wikipedia's public API (free, plain text, no scraping): one search call to
  pick titles, one call for the introduction of each page.
* DuckDuckGo Instant Answers, Wikidata and a keyed web search (Brave or
  Google) live in ``app.ai.answers.sources``. Web results from trusted
  domains (``CRAWLER_TRUSTED_DOMAINS``: government, academic, reference
  sites) are ranked first and their pages fetched and reduced to text.

Everything is bounded: ``CRAWLER_MAX_RESULTS`` per source, ``MAX_TOTAL_PAGES``
overall, ``CRAWLER_TIMEOUT_SECONDS`` per request, ``CRAWLER_MAX_PAGE_BYTES``
per fetched page, and extracts are truncated to ``MAX_CHARS`` characters.

Failure policy: a source that errors is skipped as long as another one
returned pages. When every source fails, the primary (Wikipedia) error is
raised so the caller sees a 503 with the reason. Throttles (429) and 5xx are
retried with a short backoff (honouring a small ``Retry-After``).
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Sequence

import httpx

from app.ai.answers import sources as src
from app.ai.answers.sources import (
    SOURCE_DUCKDUCKGO,
    SOURCE_WIKIDATA,
    SOURCE_WIKIPEDIA,
    SearchResult,
    WebSearchConfig,
)
from app.config import settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

API_URL = "https://en.wikipedia.org/w/api.php"
MAX_CHARS = 4000
MAX_TOTAL_PAGES = 8
# Kept for callers and tests that import them from here.
RETRY_STATUSES = src.RETRY_STATUSES
MAX_RETRIES = src.MAX_RETRIES
BACKOFF_SECONDS = src.BACKOFF_SECONDS
MAX_BACKOFF_SECONDS = src.MAX_BACKOFF_SECONDS

KNOWN_SOURCES = (SOURCE_WIKIPEDIA, SOURCE_DUCKDUCKGO, SOURCE_WIKIDATA, "websearch")


@dataclass
class Page:
    title: str
    url: str
    text: str
    #: Which provider the page came from: wikipedia | duckduckgo | wikidata | web
    source: str = SOURCE_WIKIPEDIA
    #: True when the URL is on a configured trusted domain.
    trusted: bool = False


def _web_search_config() -> Optional[WebSearchConfig]:
    if not settings.web_search_configured:
        return None
    return WebSearchConfig(
        provider=(settings.web_search_provider or "").lower(),
        api_key=settings.web_search_api_key or "",
        cse_id=settings.google_cse_id,
    )


class Crawler:
    def __init__(
        self,
        *,
        max_results: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        user_agent: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        api_url: str = API_URL,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        sources: Optional[Sequence[str]] = None,
        web_search: Optional[WebSearchConfig] = None,
        fetch_pages: Optional[bool] = None,
        fetch_limit: Optional[int] = None,
        trusted_domains: Optional[Sequence[str]] = None,
        max_page_bytes: Optional[int] = None,
    ):
        self.max_results = max_results or settings.crawler_max_results
        self.timeout = httpx.Timeout(timeout_seconds or settings.crawler_timeout_seconds)
        self.user_agent = user_agent or settings.crawler_user_agent
        self._transport = transport
        self.api_url = api_url
        self._sleep = sleep  # injectable so tests do not wait for real backoff
        self.sources = [s for s in (sources if sources is not None else settings.crawler_source_list) if s in KNOWN_SOURCES]
        if not self.sources:
            self.sources = [SOURCE_WIKIPEDIA]
        self.web_search = web_search if web_search is not None else _web_search_config()
        self.fetch_pages = fetch_pages if fetch_pages is not None else settings.crawler_fetch_pages
        self.fetch_limit = fetch_limit if fetch_limit is not None else settings.crawler_fetch_limit
        self.trusted_domains = list(trusted_domains if trusted_domains is not None else settings.crawler_trusted_domain_list)
        self.max_page_bytes = max_page_bytes or settings.crawler_max_page_bytes

    # ------------------------------------------------------------------ public

    async def crawl(self, question: str, sources: Optional[Sequence[str]] = None) -> List[Page]:
        """Ask the configured sources (or the given subset) and return merged pages, best first."""
        wanted = [s for s in (sources if sources is not None else self.sources) if s in self.sources]
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(
            timeout=self.timeout, transport=self._transport, headers=headers, follow_redirects=True
        ) as client:
            names: List[str] = []
            tasks = []
            for name in wanted:
                if name == "websearch" and self.web_search is None:
                    continue  # not configured: silently skipped
                names.append(name)
                tasks.append(self._run_source(client, name, question))
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        pages_by_source: Dict[str, List[Page]] = {}
        errors: Dict[str, BaseException] = {}
        for name, outcome in zip(names, outcomes):
            if isinstance(outcome, BaseException):
                errors[name] = outcome
                reason = (outcome.details or {}).get("reason") if isinstance(outcome, ExternalServiceError) else None
                logger.warning("Crawler source %s failed: %s", name, reason or type(outcome).__name__)
            else:
                pages_by_source[name] = outcome

        merged = self._merge(pages_by_source)
        if not merged and errors:
            raise self._primary_error(errors)
        return merged

    # ----------------------------------------------------------------- sources

    async def _run_source(self, client: httpx.AsyncClient, name: str, question: str) -> List[Page]:
        if name == SOURCE_WIKIPEDIA:
            return await self._wikipedia(client, question)
        if name == SOURCE_DUCKDUCKGO:
            results = await src.duckduckgo(client, question, sleep=self._sleep, max_results=self.max_results)
            return [self._page_from_result(r) for r in results]
        if name == SOURCE_WIKIDATA:
            results = await src.wikidata(client, question, sleep=self._sleep, max_results=self.max_results)
            return [self._page_from_result(r) for r in results]
        if name == "websearch":
            assert self.web_search is not None
            results = await src.web_search(
                client, question, sleep=self._sleep, config=self.web_search, max_results=self.max_results
            )
            return await self._web_pages(client, results)
        return []

    async def _wikipedia(self, client: httpx.AsyncClient, question: str) -> List[Page]:
        titles = await self._search(client, question)
        if not titles:
            return []
        return await self._fetch(client, titles)

    async def _search(self, client: httpx.AsyncClient, question: str) -> List[str]:
        data = await self._get(
            client,
            {
                "action": "query",
                "list": "search",
                "srsearch": question,
                "srlimit": self.max_results,
                "format": "json",
                "utf8": 1,
            },
        )
        hits = data.get("query", {}).get("search", []) if isinstance(data, dict) else []
        return [hit["title"] for hit in hits if isinstance(hit, dict) and isinstance(hit.get("title"), str)]

    async def _fetch(self, client: httpx.AsyncClient, titles: List[str]) -> List[Page]:
        data = await self._get(
            client,
            {
                "action": "query",
                "prop": "extracts|info",
                "explaintext": 1,
                "exintro": 1,
                "inprop": "url",
                "redirects": 1,
                "titles": "|".join(titles),
                "format": "json",
            },
        )
        raw_pages = data.get("query", {}).get("pages", {}) if isinstance(data, dict) else {}
        by_title = {}
        for page in raw_pages.values() if isinstance(raw_pages, dict) else []:
            if not isinstance(page, dict):
                continue
            text = (page.get("extract") or "").strip()
            title = page.get("title")
            if not text or not isinstance(title, str):
                continue
            url = page.get("fullurl") or f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            by_title[title] = Page(title=title, url=url, text=text[:MAX_CHARS], source=SOURCE_WIKIPEDIA, trusted=True)
        # Keep the search ranking; redirects may rename a title, so fall back to insertion order.
        ordered = [by_title[t] for t in titles if t in by_title]
        for page in by_title.values():
            if page not in ordered:
                ordered.append(page)
        return ordered

    async def _get(self, client: httpx.AsyncClient, params: dict) -> dict:
        """Wikipedia API call with the shared retry policy."""
        return await src.get_json(client, self.api_url, params, sleep=self._sleep)

    async def _web_pages(self, client: httpx.AsyncClient, results: List[SearchResult]) -> List[Page]:
        """Web results as pages: trusted domains first, top ones fetched and reduced to text."""
        ranked = sorted(results, key=lambda r: 0 if src.is_trusted(r.url, self.trusted_domains) else 1)
        pages = [self._page_from_result(r) for r in ranked]
        if not self.fetch_pages or self.fetch_limit <= 0:
            return pages
        to_fetch = pages[: self.fetch_limit]
        fetched = await asyncio.gather(
            *(src.fetch_page(client, p.url, max_bytes=self.max_page_bytes, max_chars=MAX_CHARS) for p in to_fetch),
            return_exceptions=True,
        )
        for page, outcome in zip(to_fetch, fetched):
            if isinstance(outcome, tuple) and outcome[1]:
                title, text = outcome
                page.text = text
                if title and len(title) <= 200:
                    page.title = title
        return pages

    def _page_from_result(self, result: SearchResult) -> Page:
        return Page(
            title=result.title.strip()[:200] or result.url,
            url=result.url,
            text=result.snippet.strip()[:MAX_CHARS],
            source=result.source,
            trusted=src.is_trusted(result.url, self.trusted_domains),
        )

    # ------------------------------------------------------------------- merge

    def _merge(self, groups: Dict[str, List[Page]]) -> List[Page]:
        """Wikipedia, then trusted web pages, other web pages, DuckDuckGo, Wikidata; no duplicate URLs."""
        web = groups.get("websearch", [])
        ordered: List[Page] = (
            groups.get(SOURCE_WIKIPEDIA, [])
            + [p for p in web if p.trusted]
            + [p for p in web if not p.trusted]
            + groups.get(SOURCE_DUCKDUCKGO, [])
            + groups.get(SOURCE_WIKIDATA, [])
        )
        seen = set()
        merged: List[Page] = []
        for page in ordered:
            key = page.url.rstrip("/").lower()
            if not page.text or key in seen:
                continue
            seen.add(key)
            merged.append(page)
            if len(merged) >= MAX_TOTAL_PAGES:
                break
        return merged

    @staticmethod
    def _primary_error(errors: Dict[str, BaseException]) -> ExternalServiceError:
        error = errors.get(SOURCE_WIKIPEDIA) or next(iter(errors.values()))
        if isinstance(error, ExternalServiceError):
            return error
        return ExternalServiceError(
            "Crawler", "The crawler could not reach its sources", details={"reason": "all_sources_failed"}
        )
