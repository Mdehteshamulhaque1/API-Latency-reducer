"""
Question answering pipeline used by POST /api/v1/answers.

    question
      -> semantic cache (Redis): same or similar question already answered?
      -> crawler: search and fetch pages that should contain the answer
      -> composer: build an answer from those pages (LLM when configured)
      -> store in the semantic cache, return

``semantic_cache``: embeddings + cosine similarity (lexical fallback when no
embedding provider is configured), entries live ``ANSWERS_CACHE_TTL`` (2 h).
``crawler``: Wikipedia's API plus the providers in ``sources`` (DuckDuckGo,
Wikidata, keyed web search with page fetching). ``composer``: answer from
the crawled text.
"""
