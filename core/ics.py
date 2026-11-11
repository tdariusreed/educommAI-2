"""Minimal iCalendar (.ics) writer: all-day events with a 1-day-before reminder.
Opens in Apple Calendar, Google Calendar and Outlook. Nothing is sent anywhere; the student downloads it."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone


def _esc(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Lines longer than 75 characters must be folded (RFC 5545)."""
    out, line = [], line.encode("utf-8")
    while len(line) > 75:
        cut = 75
        while cut > 0 and (line[cut] & 0xC0) == 0x80:  # don't split a multi-byte character
            cut -= 1
        out.append(line[:cut].decode("utf-8"))
        line = b" " + line[cut:]
    out.append(line.decode("utf-8"))
    return "\r\n".join(out)


def make_ics(events: list[dict], now: datetime | None = None) -> str:
    """events: [{"date": date, "summary": str, "description": str}]. Returns the file text ('' if no events)."""
    if not events:
        return ""
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//educommAI//Career Planning//EN", "CALSCALE:GREGORIAN"]
    for ev in events:
        day: date = ev["date"]
        uid = hashlib.sha1(f"{day}{ev['summary']}".encode()).hexdigest()[:16] + "@educommai"
        lines += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
                  f"SUMMARY:{_esc(ev['summary'])}", f"DESCRIPTION:{_esc(ev.get('description', ''))}",
                  "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(ev['summary'])}", "TRIGGER:-P1D", "END:VALARM",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"
