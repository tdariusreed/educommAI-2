"""Intake: short, friendly onboarding. Deterministic (no model call).
Order: who is asking (student / parent) -> grade -> interests -> city or state (optional, once)."""

from __future__ import annotations

import re

from core.models import Profile, normalize_updates

_Q = {
    "role": {"any": "Are you a student, or a parent or guardian helping a student? (Just type student or parent.)"},
    "grade": {"student": "What grade are you in right now? (6 through 12)",
              "parent": "What grade is your child in right now? (6 through 12)"},
    "interests": {"student": "What are a few things you like or are curious about? School subjects, hobbies, anything. For example: math, video games, helping people.",
                  "parent": "What does your child enjoy, or what are their goals? School subjects, hobbies, or careers they have mentioned. For example: math, art, becoming a nurse."},
    "location": {"student": "What city or state do you live in? This helps me find programs near you. You can type skip.",
                 "parent": "What city or state do you live in? This helps me find programs near you. You can type skip."},
}
GREETING = "Hi! I'm your career-planning helper. I can help with careers, what school or training they need, programs, scholarships, and a plan to get there. First, a quick question so I can help you better."
DONE = {"student": "Thanks, that helps a lot! What would you like to explore? You could ask what careers fit you, what classes to take, programs near you, how to pay for college, or for a month-by-month plan.",
        "parent": "Thanks! What would you like help with? For example: a college-prep checklist and month-by-month plan, scholarships and deadlines, or programs near you."}

_ORDINALS = {"sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
             "freshman": 9, "sophomore": 10, "junior": 11, "senior": 12}
_ORD_RE = re.compile(r"\b(" + "|".join(_ORDINALS) + r")\b")
_GRADE_RE = [re.compile(p) for p in (r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*grade\b", r"\bgrade\s*(\d{1,2})\b", r"^\s*(\d{1,2})\s*(?:st|nd|rd|th)?\s*$")]
_FILLER = re.compile(r"^(?:i(?:'m| am)?\s+)?(?:really\s+)?(?:like|love|enjoy|into|interested in|good at|curious about)\s+", re.I)
_SKIP = re.compile(r"^\s*(?:skip|no|none|n/?a|pass|prefer not.*|rather not.*|i don'?t want.*|not now)\s*[.!]?\s*$", re.I)
_ADULT = (r"parents?|mom|mother|dad|father|guardian|grandparent|grandmother|grandfather|caregiver|aunt|uncle|"
          r"teacher|counselor|mentor|coach")
_PARENT = re.compile(rf"\b(?:my|our)\s+(?:\w+\s+)?(?:daughter|son|child|kids?|children|teen(?:ager)?|student|grandson|granddaughter|niece|nephew|stepson|stepdaughter)\b"
                     rf"|\bi(?:'m| am)\s+(?:a\s+|an\s+|his\s+|her\s+|their\s+)?(?:{_ADULT})\b|\bas a (?:{_ADULT})\b|\b(?:parent|guardian)\b", re.I)
_SUBJ = r"(?:i|she|he|they|we|daughter|son|child|kid|student|teen)"
_LIKES = re.compile(rf"(?:\b{_SUBJ}\s+|\band\s+)(?:really\s+|also\s+)?(?:likes?|loves?|enjoys?)\s+([^.?!;\n]+)|\binterested in\s+([^.?!;\n]+)", re.I)
_CUT = re.compile(r"\s+(?:but|because|so|though|although|however|and (?:i|she|he|they|don'?t|doesn'?t|wants?|needs?))\b.*$", re.I)
_LIVE = re.compile(r"\b(?i:we|i)\s+(?i:live|are living|am living|are located|am located|are based)\s+(?i:in)\s+([A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,3}(?:,\s*[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*)?)?)")
_LOC_FILLER = re.compile(r"^(?:i|we)?\s*(?:live|am|are|'m|'re)?\s*(?:in|from|near|around|at)?\s+", re.I)


def extract_grade(text: str) -> int | None:
    low = text.lower()
    m = _ORD_RE.search(low)
    if m:
        return _ORDINALS[m.group(1)]
    for rx in _GRADE_RE:
        m = rx.search(low)
        if m:
            return int(m.group(1)) if 6 <= int(m.group(1)) <= 12 else None
    return None


def extract_role(text: str) -> str:
    return "parent" if _PARENT.search(text) else "student"


def extract_updates(text: str, awaiting: str | None) -> dict:
    """Parse a direct answer to the question we just asked."""
    if awaiting == "role":
        return {"role": extract_role(text)}
    if awaiting == "grade":
        grade = extract_grade(text)
        return {"grade": grade} if grade else {}
    if awaiting == "interests":
        return normalize_updates({"interests": _FILLER.sub("", text.strip().rstrip(".!"))})
    if awaiting == "location":
        text = text.strip().rstrip(".!")
        return {} if _SKIP.match(text) else {"location": _LOC_FILLER.sub("", text) or text}
    return {}


def extract_freetext(text: str, profile: Profile) -> dict:
    """Pick up facts stated in an ordinary message ("my daughter is in 9th grade and likes math").
    Only fills fields that are still empty, and only from explicit statements."""
    out: dict = {}
    if not profile.role and _PARENT.search(text):
        out["role"] = "parent"
    if not profile.grade:
        grade = extract_grade(text) if len(text.split()) > 1 else None
        if grade:
            out["grade"] = grade
    if not profile.interests:
        m = _LIKES.search(text)
        raw = next((g for g in m.groups() if g), "") if m else ""
        items = [i for i in normalize_updates({"interests": _CUT.sub("", raw)}).get("interests", [])
                 if not re.match(r"(?:to|the|a|an|what|how)\b", i, re.I) and len(i) <= 40]
        if items:
            out["interests"] = items[:4]
    if not profile.location:
        m = _LIVE.search(text)
        if m:
            out["location"] = m.group(1).rstrip(".,")
    return out


def next_field(profile: Profile, session) -> str | None:
    """The next thing to ask, or None when intake is finished. Location is asked once, only of new users."""
    missing = profile.missing_required()
    if missing:
        return missing[0]
    if session.intake_active and not profile.location and not session.location_asked:
        return "location"
    return None


def next_question(profile: Profile, first_contact: bool, session) -> tuple[str | None, str]:
    """(field being asked about or None when done, message to show)."""
    field = next_field(profile, session)
    if field is None:
        return None, DONE[profile.audience]
    q = _Q[field].get(profile.audience) or _Q[field]["any"]
    return field, f"{GREETING}\n\n{q}" if first_contact else q
