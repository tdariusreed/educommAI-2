"""Verifier: every link in the answer must come from a search result.

The model only writes source NUMBERS; this step turns them into real links from our own results,
removes numbers that don't exist, and strips any URL the model made up."""

from __future__ import annotations

import re

from core.tracing import Trace

_CITE = re.compile(r"\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\](?!\()")
_URL = re.compile(r"https?://[^\s\"'\\<>)\]]+")
CAUTION = "\n\n_Note: I couldn't match this to a specific source, so please double-check it with a counselor or an official website._"


def finalize(text: str, evidence: list[dict], trace: Trace | None = None) -> tuple[str, list[str], list[str]]:
    """Returns (final text, cited source URLs, issues)."""
    trace = trace or Trace()
    by_n = {e["n"]: e["url"] for e in evidence}
    allowed = set(by_n.values())
    issues: list[str] = []
    bad_numbers = 0

    def link(m):
        nonlocal bad_numbers
        out = []
        for n in (int(x) for x in re.split(r"\s*,\s*", m.group(1))):
            if n in by_n:
                out.append(f"[{n}]({by_n[n]})")
            else:
                bad_numbers += 1
        return " ".join(out)

    text = _CITE.sub(link, text)
    if bad_numbers:
        issues.append(f"removed {bad_numbers} citation(s) pointing to nothing")

    removed = 0
    for url in sorted({u.rstrip(".,;:") for u in _URL.findall(text)} - allowed):
        removed += 1
        text = re.sub(rf"\[([^\]]*)\]\({re.escape(url)}\)", r"\1", text).replace(url, "")
    if removed:
        issues.append(f"removed {removed} link(s) that were not in any search result")

    text = re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", text)).strip()
    cited = [by_n[n] for n in sorted(by_n) if by_n[n] in text]
    if evidence and not cited:
        issues.append("no cited source")
        text += CAUTION
    trace.add("verification", "verifier", cited=len(cited), issues=issues)
    return text, cited, issues
