"""Find dates in the sources we actually retrieved. We never invent a deadline: a date counts only if it
appears in a source sentence that also says what it is (deadline, due, opens, closes, apply by...)."""

from __future__ import annotations

import re
from datetime import date

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MONTH_RX = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE = re.compile(rf"\b({_MONTH_RX})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d{{2}}))?\b", re.I)
_KEY = re.compile(rf"\b(?:deadlines?|due|apply by|submit by|register by|closes?|closing|opens?|opening|application period)\b"
                  rf"|\bby\s+{_MONTH_RX}\b", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _resolve(month: int, day: int, year: int | None, today: date) -> tuple[date | None, bool]:
    """(date, year_was_guessed). With no year given, use the next time that date comes around."""
    try:
        if year:
            return date(year, month, day), False
        d = date(today.year, month, day)
        return (d if d >= today else date(today.year + 1, month, day)), True
    except ValueError:
        return None, False


def extract(evidence: list[dict], today: date, limit: int = 5) -> list[dict]:
    found, seen = [], set()
    for e in evidence:
        for sentence in _SENTENCE.split(e.get("text") or e.get("snippet") or ""):
            if not _KEY.search(sentence):
                continue
            for m in _DATE.finditer(sentence):
                when, guessed = _resolve(_MONTHS[m.group(1).lower()[:3]], int(m.group(2)),
                                         int(m.group(3)) if m.group(3) else None, today)
                if when is None or (when, e["url"]) in seen:
                    continue
                seen.add((when, e["url"]))
                found.append({"n": e["n"], "url": e["url"], "title": e["title"], "date": when,
                              "year_guessed": guessed, "context": sentence.strip()[:180]})
    found.sort(key=lambda d: d["date"])
    return found[:limit]
