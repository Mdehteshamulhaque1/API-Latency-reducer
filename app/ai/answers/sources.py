"""
Crawler sources other than Wikipedia, plus page fetching.

Every function here is pure I/O over an ``httpx.AsyncClient`` the crawler
owns, returns plain data (``SearchResult`` or extracted text) and raises
``ExternalServiceError`` on failure so the crawler can decide whether one
failed source matters. No secrets or page bodies are logged.

Sources
-------
* DuckDuckGo Instant Answers: free JSON API, no key. Gives a short abstract
  (often from Wikipedia or another reference site) and related topics.
* Wikidata: free, no key. Entity labels and descriptions: good for "who is",
  "what is" facts about people, places and organisations.
* Keyed web search (Brave Search API or Google Programmable Search): results
  from the open web, including government and institutional sites. The
  crawler ranks trusted domains first and can fetch the result pages.

Page text extraction uses only the standard library ``html.parser`` so no
new dependency is needed.
"""
import ipaddress
import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional, Tuple
from urllib.parse import urlsplit

import httpx

from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

DUCKDUCKGO_URL = "https://api.duckduckgo.com/"
WIKIDATA_URL = "https://www.wikidata.org/w/api.php"
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

SOURCE_WIKIPEDIA = "wikipedia"
SOURCE_DUCKDUCKGO = "duckduckgo"
SOURCE_WIKIDATA = "wikidata"
SOURCE_WEB = "web"

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")
_QUESTION_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "who", "how", "why", "when", "where", "which",
    "does", "did", "do", "of", "in", "on", "for", "to", "and", "or", "me", "tell", "about", "please",
    "can", "you", "it", "this", "that", "with", "from", "by", "explain", "define", "meaning",
}
_NAME_CONNECTORS = {"van", "von", "de", "der", "den", "da", "di", "du", "del", "della", "la", "le", "of", "al", "bin", "ibn"}
_SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside", "svg", "form", "iframe", "template"}
_BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "td", "th", "section", "article", "blockquote", "pre"}
MIN_LINE_WORDS = 4


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = SOURCE_WEB


def keywords(question: str) -> str:
    """The question without question words, for entity search (Wikidata)."""
    words = [w for w in _WORD.findall(question) if w.lower() not in _QUESTION_WORDS]
    return " ".join(words) or question.strip()


MAX_QUERY_CANDIDATES = 3


def query_candidates(question: str) -> List[str]:
    """Short topic queries to try, in order, for APIs that answer topics rather than questions.

    DuckDuckGo Instant Answers and Wikidata know "Lisbon" or "income tax" but
    not "What is the capital city of Portugal?". Candidates: the question's
    keywords, then its proper nouns (capitalised words after the first), then
    the last two keywords. Duplicates are dropped and at most three are kept.
    """
    tokens = _WORD.findall(question)
    content = [w for w in tokens if w.lower() not in _QUESTION_WORDS]
    candidates: List[str] = []

    def add(text: str) -> None:
        text = text.strip()
        if text and text.lower() not in {c.lower() for c in candidates}:
            candidates.append(text)

    add(" ".join(content))
    # Proper-noun runs ("Guido van Rossum", "New York"), then each proper noun alone.
    runs: List[List[str]] = []
    current: List[str] = []
    for word in tokens[1:]:
        if word[:1].isupper() and word.lower() not in _QUESTION_WORDS:
            current.append(word)
        elif current and word.lower() in _NAME_CONNECTORS:
            current.append(word)
        else:
            if current:
                runs.append(current)
            current = []
    if current:
        runs.append(current)
    for run in runs:
        while run and run[-1].lower() in _NAME_CONNECTORS:
            run.pop()
        if len(run) > 1:
            add(" ".join(run))
    for run in runs:
        for word in run:
            if word.lower() not in _NAME_CONNECTORS:
                add(word)
    if len(content) > 2:
        add(" ".join(content[-2:]))
    if not candidates:
        add(question)
    return candidates[:MAX_QUERY_CANDIDATES]


def host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def is_trusted(url: str, trusted_domains: List[str]) -> bool:
    host = host_of(url)
    if not host:
        return False
    for suffix in trusted_domains:
        suffix = suffix.lower().lstrip("*")
        if host == suffix.lstrip(".") or host.endswith(suffix) or (not suffix.startswith(".") and host.endswith("." + suffix)):
            return True
    return False


def is_fetchable(url: str) -> bool:
    """Only public http(s) URLs are fetched (no local or private addresses)."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return False
    host = parts.hostname.lower()
    if host in {"localhost", "0.0.0.0"} or host.endswith(".local") or host.endswith(".internal"):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True  # a name, not a literal address
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved)


# ---------------------------------------------------------------------------
# HTTP helper with bounded retries (shared by every JSON source)
# ---------------------------------------------------------------------------

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
BACKOFF_SECONDS = (0.5, 1.5)
MAX_BACKOFF_SECONDS = 3.0


def retry_delay(response: httpx.Response, attempt: int) -> float:
    """Backoff for the next retry: Retry-After when present and small, else a fixed step."""
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), MAX_BACKOFF_SECONDS)
        except ValueError:
            pass  # HTTP-date form: fall through to the fixed backoff
    return BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]


async def get_json(client: httpx.AsyncClient, url: str, params: dict, *, sleep, headers: Optional[dict] = None) -> dict:
    """GET ``url`` and decode JSON, retrying throttles and 5xx a bounded number of times."""
    response: Optional[httpx.Response] = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise ExternalServiceError("Crawler", "The crawler timed out", details={"reason": "timeout"}) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                "Crawler", "The crawler could not reach its source", details={"reason": "network_error"}
            ) from exc
        if response.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
            delay = retry_delay(response, attempt)
            logger.warning(
                "Crawler source %s returned %s; retrying in %.1fs (attempt %d/%d)",
                host_of(url), response.status_code, delay, attempt + 1, MAX_RETRIES,
            )
            await sleep(delay)
            continue
        break
    assert response is not None
    if response.status_code >= 400:
        logger.warning("Crawler source %s returned %s", host_of(url), response.status_code)
        raise ExternalServiceError(
            "Crawler",
            "The crawler's source returned an error",
            details={"reason": f"http_{response.status_code}", "status_code": response.status_code},
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise ExternalServiceError(
            "Crawler", "The crawler's source returned an invalid response", details={"reason": "invalid_response"}
        ) from exc
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# DuckDuckGo Instant Answers
# ---------------------------------------------------------------------------

def _flatten_topics(topics, out: List[dict]) -> None:
    for item in topics if isinstance(topics, list) else []:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("Topics"), list):
            _flatten_topics(item["Topics"], out)
        elif isinstance(item.get("Text"), str) and item.get("FirstURL"):
            out.append(item)


async def duckduckgo(client: httpx.AsyncClient, question: str, *, sleep, max_results: int) -> List[SearchResult]:
    """Instant Answers for the first query candidate that returns anything (the API answers topics, not questions)."""
    for candidate in query_candidates(question):
        results = await _duckduckgo_query(client, candidate, sleep=sleep, max_results=max_results)
        if results:
            return results
    return []


async def _duckduckgo_query(client: httpx.AsyncClient, query: str, *, sleep, max_results: int) -> List[SearchResult]:
    data = await get_json(
        client,
        DUCKDUCKGO_URL,
        {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1, "no_redirect": 1},
        sleep=sleep,
    )
    results: List[SearchResult] = []
    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        title = (data.get("Heading") or data.get("AbstractSource") or "DuckDuckGo").strip()
        url = data.get("AbstractURL") or DUCKDUCKGO_URL
        results.append(SearchResult(title=title, url=url, snippet=abstract, source=SOURCE_DUCKDUCKGO))
    answer = (data.get("Answer") or "").strip()
    if answer and isinstance(answer, str):
        results.append(SearchResult(title="DuckDuckGo answer", url=DUCKDUCKGO_URL, snippet=answer, source=SOURCE_DUCKDUCKGO))
    topics: List[dict] = []
    _flatten_topics(data.get("RelatedTopics"), topics)
    for topic in topics:
        if len(results) >= max_results:
            break
        text = topic["Text"].strip()
        title = text.split(" - ", 1)[0][:120] if " - " in text else text[:80]
        results.append(SearchResult(title=title, url=topic["FirstURL"], snippet=text, source=SOURCE_DUCKDUCKGO))
    return results[:max_results]


# ---------------------------------------------------------------------------
# Wikidata entity search
# ---------------------------------------------------------------------------

async def wikidata(client: httpx.AsyncClient, question: str, *, sleep, max_results: int) -> List[SearchResult]:
    """Entity facts for the first query candidate that matches (entity search wants a name, not a sentence)."""
    for candidate in query_candidates(question):
        results = await _wikidata_query(client, candidate, sleep=sleep, max_results=max_results)
        if results:
            return results
    return []


async def _wikidata_query(client: httpx.AsyncClient, query: str, *, sleep, max_results: int) -> List[SearchResult]:
    data = await get_json(
        client,
        WIKIDATA_URL,
        {
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "uselang": "en",
            "type": "item",
            "limit": max_results,
            "format": "json",
        },
        sleep=sleep,
    )
    results: List[SearchResult] = []
    for entity in data.get("search", []) if isinstance(data.get("search"), list) else []:
        if not isinstance(entity, dict):
            continue
        label = entity.get("label")
        description = entity.get("description")
        if not isinstance(label, str) or not isinstance(description, str) or not description.strip():
            continue
        entity_id = entity.get("id") or ""
        url = entity.get("concepturi") or f"https://www.wikidata.org/wiki/{entity_id}"
        results.append(
            SearchResult(title=f"{label} (Wikidata)", url=url, snippet=f"{label}: {description}.", source=SOURCE_WIKIDATA)
        )
    return results


# ---------------------------------------------------------------------------
# Keyed web search: Brave or Google Programmable Search
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WebSearchConfig:
    provider: str  # "brave" | "google"
    api_key: str
    cse_id: Optional[str] = None


async def web_search(
    client: httpx.AsyncClient, question: str, *, sleep, config: WebSearchConfig, max_results: int
) -> List[SearchResult]:
    provider = config.provider.lower()
    if provider == "brave":
        data = await get_json(
            client,
            BRAVE_URL,
            {"q": question, "count": max_results, "safesearch": "moderate", "text_decorations": 0},
            sleep=sleep,
            headers={"X-Subscription-Token": config.api_key, "Accept": "application/json"},
        )
        raw = data.get("web", {}).get("results", []) if isinstance(data.get("web"), dict) else []
        return [
            SearchResult(title=str(r.get("title") or r.get("url")), url=r["url"], snippet=str(r.get("description") or ""))
            for r in raw
            if isinstance(r, dict) and isinstance(r.get("url"), str)
        ][:max_results]
    if provider == "google":
        data = await get_json(
            client,
            GOOGLE_CSE_URL,
            {"key": config.api_key, "cx": config.cse_id, "q": question, "num": min(max_results, 10)},
            sleep=sleep,
        )
        raw = data.get("items", [])
        return [
            SearchResult(title=str(r.get("title") or r.get("link")), url=r["link"], snippet=str(r.get("snippet") or ""))
            for r in raw
            if isinstance(r, dict) and isinstance(r.get("link"), str)
        ][:max_results]
    raise ExternalServiceError(
        "Crawler", "Unknown web search provider", details={"reason": "unknown_provider"}
    )


# ---------------------------------------------------------------------------
# Page fetching and HTML text extraction (standard library only)
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._chunks: List[str] = []
        self._current: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._skip_depth == 0:
            self._current.append(data)

    def _flush(self) -> None:
        text = " ".join(" ".join(self._current).split())
        self._current = []
        if text:
            self._chunks.append(text)

    def result(self) -> Tuple[str, List[str]]:
        self._flush()
        return " ".join(self.title.split()), self._chunks


def extract_text(html: str, max_chars: int) -> Tuple[str, str]:
    """(title, readable text) from an HTML document.

    Navigation, scripts and styles are dropped; short fragments (menus,
    buttons) are skipped so the text that is left reads like the article.
    """
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - malformed markup: use what was parsed so far
        pass
    title, chunks = parser.result()
    lines = [c for c in chunks if len(c.split()) >= MIN_LINE_WORDS]
    text = "\n".join(lines)
    return title, text[:max_chars].rstrip()


async def fetch_page(
    client: httpx.AsyncClient, url: str, *, max_bytes: int, max_chars: int
) -> Optional[Tuple[str, str]]:
    """Download a public HTML page (bounded size) and return (title, text), or None."""
    if not is_fetchable(url):
        return None
    try:
        async with client.stream("GET", url) as response:
            if response.status_code != 200:
                return None
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type and "text/plain" not in content_type:
                return None
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) >= max_bytes:
                    break
            encoding = response.encoding or "utf-8"
    except httpx.HTTPError as exc:
        logger.info("Crawler page fetch failed for %s: %s", host_of(url), type(exc).__name__)
        return None
    try:
        html = body.decode(encoding, errors="replace")
    except LookupError:
        html = body.decode("utf-8", errors="replace")
    if "text/plain" in content_type:
        return "", " ".join(html.split())[:max_chars]
    title, text = extract_text(html, max_chars)
    if not text:
        return None
    return title, text
