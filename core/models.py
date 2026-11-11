"""Shared types and profile validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any

PROFILE_FIELDS = ("role", "grade", "interests", "academics", "location", "constraints", "goal")
ROLES = ("student", "parent")  # "parent" = any adult helping a student (parent, guardian, teacher, counselor)
REQUIRED_FIELDS = ("grade", "interests")


def _clean(value: Any, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()[:limit]


def normalize_updates(raw: Any) -> dict:
    """Keep known fields only, coerced to the right type. Invalid values are dropped."""
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    for key in PROFILE_FIELDS:
        value = raw.get(key)
        if value in (None, "", [], {}):
            continue
        if key == "role":
            if str(value).strip().lower() in ROLES:
                out["role"] = str(value).strip().lower()
        elif key == "grade":
            m = re.match(r"\s*(\d{1,2})", str(value))
            if m and 6 <= int(m.group(1)) <= 12:
                out["grade"] = int(m.group(1))
        elif key == "interests":
            items = re.split(r",|;| and ", value) if isinstance(value, str) else list(value)
            seen, cleaned = set(), []
            for item in items:
                text = _clean(item, 60)
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    cleaned.append(text)
            if cleaned:
                out["interests"] = cleaned[:10]
        elif _clean(value):
            out[key] = _clean(value)
    return out


@dataclass
class Profile:
    role: str = ""
    grade: int | None = None
    interests: list[str] = field(default_factory=list)
    academics: str = ""
    location: str = ""
    constraints: str = ""
    goal: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        return cls(**normalize_updates(data))

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, "", [])}

    def missing_required(self) -> list[str]:
        """Fields intake must still ask for. The role is only asked of brand-new users (old profiles stay complete)."""
        missing = [f for f in REQUIRED_FIELDS if not getattr(self, f)]
        return (["role"] + missing) if missing and not self.role else missing

    @property
    def audience(self) -> str:
        return self.role or "student"

    @property
    def band(self) -> str:
        return "general" if self.grade is None else ("middle" if self.grade <= 8 else "high")

    def to_prompt(self) -> str:
        return json.dumps(self.to_dict()) if self.to_dict() else "unknown"


@dataclass
class Plan:
    agents: list[str] = field(default_factory=list)
    clarifying_question: str = ""
    offer_quiz: bool = False


@dataclass
class TurnResult:
    answer: str
    sources: list[str] = field(default_factory=list)
    agents_used: list[str] = field(default_factory=list)
    blocked: bool = False
    needs_input: bool = False
    used_llm: bool = False
    action: str = ""          # "quiz" = the UI should show the interest quiz
    offer_quiz: bool = False  # suggest the quiz after this answer
    ics: str = ""             # calendar file text (plan reminders + dates found in sources)
    flags: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    trace: Any = None
