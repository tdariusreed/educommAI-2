"""Rank search results by how trustworthy the source is.
Job boards and listing sites are fine for 'what openings exist' but not for facts about
careers or education, so they sink to the bottom."""

from __future__ import annotations

from urllib.parse import urlparse

HIGH_DOMAINS = (
    "onetonline.org", "bls.gov", "studentaid.gov", "collegescorecard.ed.gov", "ed.gov", "nces.ed.gov",
    "careeronestop.org", "gafutures.org", "gsfc.georgia.gov", "usg.edu", "tcsg.edu",
    "bigfuture.collegeboard.org", "collegeboard.org", "consumerfinance.gov",
)
LOW_DOMAINS = (
    "indeed.com", "ziprecruiter.com", "glassdoor.com", "linkedin.com", "monster.com", "simplyhired.com",
    "careerbuilder.com", "reddit.com", "quora.com", "pinterest.com", "facebook.com", "tiktok.com",
)


def _host(url: str) -> str:
    return (urlparse(url or "").hostname or "").lower().removeprefix("www.")


def _matches(host: str, domains: tuple) -> bool:
    return any(host == d or host.endswith("." + d) for d in domains)


def score_url(url: str) -> tuple[int, str]:
    """Return (score, quality label). Higher is more trustworthy."""
    host = _host(url)
    if not host:
        return 0, "low"
    if _matches(host, HIGH_DOMAINS):
        return 100, "high"
    if host.endswith(".gov") or host.endswith(".edu"):
        return 90, "high"
    if _matches(host, LOW_DOMAINS):
        return 10, "low"
    if host.endswith(".org"):
        return 50, "medium"
    return 40, "medium"


def rank_results(results: list[dict]) -> list[dict]:
    """Add a 'quality' label and sort best-first (stable, so ties keep search order)."""
    ranked = []
    for r in results:
        score, label = score_url(r.get("url", ""))
        ranked.append(({**r, "quality": label}, score))
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return [r for r, _ in ranked]
