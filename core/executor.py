"""Retrieval: each specialist runs its search (in parallel; this is network wait, not CPU),
results are de-duplicated by URL and numbered so the writer can cite them as [1], [2]..."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import config
from agents.specialists import SPECIALISTS
from core.models import Profile
from core.tracing import Trace


def _knowledge_hits(knowledge, query: str) -> list[dict]:
    if knowledge is None:
        return []
    return [{"title": h["title"], "url": h["url"], "snippet": h["text"][: config.SNIPPET_CHARS], "text": h["text"], "quality": "high"}
            for h in knowledge.search(query, k=2) if h["url"]]  # no URL = nothing to cite


def _interleave(lists: list[list[dict]]) -> list[dict]:
    """Round-robin the results of several queries (each query's best first), de-duplicated by URL, so every
    interest the student named is represented near the top."""
    seen, out = set(), []
    for rank in range(max((len(l) for l in lists), default=0)):
        for l in lists:
            if rank < len(l) and l[rank]["url"] not in seen:
                seen.add(l[rank]["url"])
                out.append(l[rank])
    return out


def gather_evidence(agents: list[str], question: str, profile: Profile, search, knowledge, trace: Trace) -> list[dict]:
    specs = [SPECIALISTS[a] for a in agents if a in SPECIALISTS and SPECIALISTS[a].query]

    def run(spec):
        queries = spec.query(question, profile)
        queries = [queries] if isinstance(queries, str) else queries
        query, lists, error = " | ".join(queries), [], None
        for q in queries:
            try:
                lists.append(search(q))
            except Exception as e:  # one failed search must not sink the answer
                error = str(e)
        results = _interleave(lists)
        hits = _knowledge_hits(knowledge, query) + results
        trace.add("search", spec.name, query=query, results=len(results), error=error, urls=[h["url"] for h in hits])
        return spec.name, hits

    if len(specs) > 1:
        with ThreadPoolExecutor(max_workers=min(len(specs), config.MAX_PARALLEL_SEARCHES)) as pool:
            outputs = list(pool.map(run, specs))  # keeps plan order
    else:
        outputs = [run(s) for s in specs]

    evidence, by_url = [], {}
    for name, hits in outputs:
        for h in hits:
            if h["url"] in by_url:
                by_url[h["url"]]["specialists"].add(name)
                continue
            item = {**h, "n": len(evidence) + 1, "specialists": {name}}
            by_url[h["url"]] = item
            evidence.append(item)
    return evidence
