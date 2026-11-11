"""Router: decides which specialists answer. Plain keyword matching: instant, no model call,
and it behaves the same on every machine."""

from __future__ import annotations

import re

from agents.specialists import LAST_STAGE, SEARCHING, SPECIALISTS
from core.models import Plan

MAX_SEARCHES = 4  # keeps one question to a few quick searches

CLARIFY = ("I'm best at careers, school, college, training, programs and scholarships. Could you tell me a bit more about "
           "what you'd like to know? For example: what careers fit you, what classes to take, programs near you, "
           "how to pay for college, or a month-by-month plan.")

_M = r"\b(?:"
_PATTERNS = {
    "quiz": re.compile(_M + r"quiz|assessment|interest (?:test|survey|inventory)|career test|personality test)"),
    "career_explorer": re.compile(_M + r"career|jobs?\b|work as|become|profession|occupation|what should i be|what do i want to be|what i want to be|fit me|good at|interest|field\b)"),
    "education": re.compile(_M + r"degrees?\b|college|universit|certificat|requirements?\b|trade school|apprentic|train(?:ing)?\b|dual enroll|diploma|what school|which school|school or|study|education|what do i need|need to get there)"),
    "courses": re.compile(_M + r"class(?:es)?\b|courses?\b|majors?\b|elective|honors|gpa|ap\b|what to take|prerequisite)"),
    "programs": re.compile(_M + r"programs?\b|summer|camps?\b|internships?\b|mentor|clubs?\b|workshops?\b|after.?school|community(?! college)|near (?:me|us)|nearby|local\b|enrichment|opportunit)"),
    "resources": re.compile(_M + r"learn|resources?\b|tutorials?\b|khan|videos?\b|websites?\b|books?\b|online|practice|study guide)"),
    "funding": re.compile(_M + r"scholarship|afford|costs?\b|pay for|paying|financial aid|fafsa|grants?\b|tuition|loans?\b|money for|hope scholarship)"),
    "next_steps": re.compile(_M + r"next steps?|what should i do|what can i do|how do i (?:get|start|become)|get started|this year)"),
    "plan": re.compile(_M + r"roadmap|checklist|month.?by.?month|timeline|action plan|step.?by.?step|schedule|calendar|remind|deadlines?|due dates?|prepare|preparation|prep\b|plan\b|plans\b|get ready|ready for college)"),
}
_DEADLINE = re.compile(r"\b(?:deadlines?|due dates?|remind)")
_UNDECIDED = re.compile(r"(?:don'?t|do not) (?:know|have) (?:what|an idea)|not sure what|no idea what|undecided|can'?t decide|what i want to be|what do i want to be")
_ORDER = list(SPECIALISTS)


def route(question: str, role: str = "student") -> Plan:
    low = question.lower()
    hits = {name for name, rx in _PATTERNS.items() if rx.search(low)}
    if "quiz" in hits:
        return Plan(agents=["quiz"])
    if not hits:
        return Plan(clarifying_question=CLARIFY)
    offer_quiz = bool(_UNDECIDED.search(low))
    if hits == {"next_steps"}:   # steps need something to build on
        hits |= {"career_explorer", "education"}
    if hits == {"plan"}:         # a bare "roadmap/plan" gets the material a good plan is built from
        hits |= {"courses", "programs", "funding"} if role == "parent" else {"career_explorer", "courses", "funding"}
    if _DEADLINE.search(low):    # deadlines come from scholarship / program sources
        hits |= {"funding", "plan"}
    agents = [a for a in _ORDER if a in hits]
    searches = [a for a in agents if a in SEARCHING][:MAX_SEARCHES]
    agents = searches + [a for a in agents if a in LAST_STAGE]
    return Plan(agents=agents, offer_quiz=offer_quiz)


def asks_deadlines(question: str) -> bool:
    return bool(_DEADLINE.search(question.lower()))
