"""The specialists. Each one knows what to look for (a search query built from the student's
profile and question) and what to tell the writer to produce. They do not call a model.
`query=None` means the specialist needs no searching (it builds on the student's profile)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from core.models import Profile

# Words that carry no topic: question words, how people phrase requests, family words, and the names of the
# specialists themselves. What is left is the real subject (e.g. "engineering", "nursing").
_GENERIC = set("""what whats which who how why do does did can could should would will i me my we you your a an the is are am be
to of in on for and or about with from at it that this these those there career careers job jobs work works working fit fits
good best some any tell show help need needs needed want like become requires require required education degree college
school study pay paying afford cost scholarship scholarships aid money get started start next step steps plan plans prepare
typical really more know take learn find look looking out into after high middle make give personalized personal roadmap
checklist month months monthly schedule remind reminder reminders deadline deadlines timeline daughter son child children kid kids
student students teen teenager her his she he they them their parent mom dad near local nearby us program programs summer resource
resources free online class classes course courses major majors please also just want wants thinking ready preparation prep
interested interest interests don't dont not sure what's right one two best top ideas idea options option recommended recommend
where when while during year years grade""".replace("'", "").split())


def content_words(question: str, limit: int = 5) -> list[str]:
    seen, out = set(), []
    for w in re.findall(r"[a-z]{3,}", question.lower()):
        if w not in _GENERIC and w not in seen:
            seen.add(w)
            out.append(w)
    return out[:limit]


def topic(question: str, profile: Profile) -> str:
    """What the student is asking about: specific words from the question, else their interests, else their goal."""
    return " ".join(content_words(question)) or " ".join(profile.interests[:2]) or " ".join(content_words(profile.goal, 3))


def topics(question: str, profile: Profile) -> list[str]:
    """Like topic(), but when the question names no subject, one topic PER interest (up to 2), so a student who likes
    history and art gets results about each, not a generic list matching neither."""
    words = content_words(question)
    if words:
        return [" ".join(words)]
    return list(profile.interests[:2]) or [topic(question, profile)]


def _level(profile: Profile) -> str:
    return "middle school" if profile.band == "middle" else "high school"


@dataclass(frozen=True)
class Specialist:
    name: str
    title: str
    instruction: str  # tells the writer what this section must cover
    query: Callable[[str, Profile], str | list[str]] | None  # None = needs no searching


SPECIALISTS = {s.name: s for s in (
    Specialist("career_explorer", "Careers that fit you",
               "Careers that fit this student (2-4): what the person does, in plain words, and why it fits them.",
               lambda q, p: f"{topic(q, p)} careers what do they do"),
    Specialist("education", "School and training",
               "Typical education or training needed (degrees, certificates, skills) and the different routes to get there; give a lower-cost route first.",
               lambda q, p: f"{topic(q, p)} typical education requirements entry level"),
    Specialist("courses", "Classes and majors",
               "Recommended classes for this grade and college majors or training programs to look at; say what each helps with.",
               lambda q, p: f"recommended {_level(p)} courses to take for {topic(q, p)} college majors"),
    Specialist("programs", "Programs near you",
               "Programs, camps, clubs, or community opportunities (summer and local) the student could join; name only ones found in the sources. Put programs that match the student's interests first; if a program is general, say so, and if none match an interest, say that plainly.",
               lambda q, p: [f"{p.location} {_level(p)} {t} summer programs camps classes community free".replace("  ", " ").strip()
                             for t in topics(q, p)]),
    Specialist("resources", "Free ways to learn",
               "Free or low-cost learning resources (websites, courses, videos) the student can start with; name only ones found in the sources.",
               lambda q, p: [f"free online learning resources {t} for {_level(p)} students" for t in topics(q, p)]),
    Specialist("funding", "Paying for it",
               "Ways to pay (scholarships, aid) or free programs. Name only programs found in the sources and tell the reader to confirm details on the official page.",
               lambda q, p: f"scholarships financial aid {_level(p)} students {p.location} {' '.join((content_words(q, 3) or p.interests[:1]))}".replace("  ", " ").strip()),
    Specialist("next_steps", "Your next steps",
               "End with 3-5 concrete next steps for this student's grade (classes, activities, people to ask, things to look up).",
               None),
    Specialist("plan", "Your plan",
               "Present the CHECKLIST and the MONTH-BY-MONTH PLAN given below (keep the months exactly as given). Work in programs or scholarships from the sources where they fit a month, with their source numbers.",
               None),
)}
SEARCHING = [n for n, s in SPECIALISTS.items() if s.query]
LAST_STAGE = ("next_steps", "plan")
