"""Lightweight execution trace (thread-safe; specialists search in parallel)."""

from __future__ import annotations

import json
import threading
import time


class Trace:
    def __init__(self):
        self.events: list[dict] = []
        self._lock = threading.Lock()
        self._start = time.perf_counter()

    def add(self, type: str, agent: str = "", **fields) -> None:
        with self._lock:
            self.events.append({"t": round(time.perf_counter() - self._start, 2), "type": type, "agent": agent, **fields})

    def to_json(self) -> str:
        return json.dumps(self.events, indent=2, ensure_ascii=False, default=str)

    def to_lines(self) -> list[str]:
        lines = []
        for e in self.events:
            extra = {k: v for k, v in e.items() if k not in ("t", "type", "agent") and v not in (None, "", [])}
            who = f" [{e['agent']}]" if e["agent"] else ""
            lines.append(f"+{e['t']:>5}s {e['type']}{who} {json.dumps(extra, ensure_ascii=False, default=str)[:200]}")
        return lines
