"""Web search with source ranking and a small in-memory cache (identical searches are free)."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict

import config
from tools.source_ranker import rank_results


def ddg_backend(query: str, max_results: int) -> list[dict]:
    try:
        from ddgs import DDGS  # imported lazily: it is slow to import and not needed until a search runs
    except ImportError:
        from duckduckgo_search import DDGS
    return DDGS().text(query, max_results=max_results)


def make_search(backend=None, retry_delay: float = 1.0):
    """Return search(query) -> ranked [{title, url, snippet, quality}]. Raises RuntimeError on failure."""
    backend = backend or ddg_backend
    cache: OrderedDict = OrderedDict()
    lock = threading.Lock()

    def search(query: str) -> list[dict]:
        key = query.strip().lower()
        now = time.monotonic()
        with lock:
            hit = cache.get(key)
            if hit and now - hit[0] < config.SEARCH_CACHE_TTL:
                cache.move_to_end(key)
                return hit[1]
        last = None
        for attempt in range(2):
            try:
                raw = backend(query, config.RESULTS_PER_QUERY * 2)  # over-fetch, keep the best-ranked
                break
            except Exception as e:
                last = e
                if attempt == 0:
                    time.sleep(retry_delay)
        else:
            raise RuntimeError(f"search failed: {last}")
        results = [{"title": (r.get("title") or "")[:120], "url": r.get("href") or r.get("url"),
                    "snippet": (r.get("body") or r.get("snippet") or "")[: config.SNIPPET_CHARS],
                    "text": (r.get("body") or r.get("snippet") or "")[:500]} for r in raw]
        results = rank_results([r for r in results if r["url"]])[: config.RESULTS_PER_QUERY]
        with lock:
            cache[key] = (now, results)
            while len(cache) > config.SEARCH_CACHE_MAX:
                cache.popitem(last=False)
        return results

    return search
