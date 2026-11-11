"""College-and-career preparation checklist and month-by-month plan, built from the student's grade.

This is general, widely-applicable guidance (not facts about any specific program), written once here so it
works with no model and no internet. It never states a date for a real deadline: those come only from sources
(see deadlines.py). Items are written with "your" meaning the student; for a parent it becomes "your child's"."""

from __future__ import annotations

import re
from datetime import date

from core.models import Profile

CHECKLIST = {
    "middle": [
        "Explore a few careers you're curious about and write down what you like about each.",
        "Keep grades steady, especially in math, reading, and writing.",
        "Try one new club, team, or activity this year.",
        "Ask the school counselor which high school courses, programs, and career pathways are offered.",
        "Look for free summer programs and library programs.",
        "Start a folder (paper or digital) for awards, projects, and activities.",
    ],
    9: [
        "Meet the school counselor and share your interests.",
        "Build a four-year course plan; ask about honors, AP, dual enrollment, and career pathway classes.",
        "Join one or two activities and stick with them.",
        "Keep a running list of activities, volunteering, and awards.",
        "Learn how your school calculates GPA.",
        "Look for free summer programs.",
    ],
    10: [
        "Review your four-year course plan with the counselor.",
        "Ask when the PSAT and college-entrance tests are offered and how to sign up.",
        "Explore careers and college majors; talk to someone who does a job you like.",
        "Take on a leadership role or a longer project in an activity.",
        "Learn the basics of financial aid and start a list of scholarships to check.",
    ],
    11: [
        "Ask the counselor for SAT/ACT dates and make a prep plan.",
        "Build a list of colleges and training options (2-year, 4-year, technical, apprenticeship) and compare costs.",
        "Visit campuses or join virtual visits and college fairs.",
        "Ask teachers you trust about recommendation letters.",
        "Keep a scholarship list with each deadline.",
        "Learn what the FAFSA is and which documents the family will need.",
    ],
    12: [
        "Finalize your college and training list with the counselor.",
        "Complete applications and track every deadline in one place.",
        "Fill out the FAFSA and any state aid forms as soon as the counselor confirms they are open.",
        "Apply for scholarships every month.",
        "Compare financial aid offers and ask the financial aid office questions.",
        "Send transcripts and confirm your final plan.",
    ],
}

_GENERIC_MONTHS = {
    1: "Start the new semester: review your goals and check your grades.",
    2: "Look for spring and summer programs. Many have early application dates, so check each program's page.",
    3: "Scholarship check: look for new scholarships and write each deadline in one list.",
    4: "Plan your summer: choose a program, job, volunteer role, or learning project.",
    5: "Finish the school year strong and update your activities list.",
    6: "Summer: do one thing connected to your interests and write down what you learned.",
    7: "Summer: read or watch something about a career you're curious about.",
    8: "Back to school: meet the counselor and review your plan.",
    9: "Join or restart one activity and set one goal for the semester.",
    10: "Explore careers and colleges: talk with someone who does a job you like.",
    11: "Scholarship check and update your activities list.",
    12: "Reflect: what did you enjoy this semester? Adjust your plan.",
}
_MIDDLE = {
    10: "Try an interest quiz or read about a career you've never heard of.",
    2: "Ask a teacher about clubs, summer programs, or competitions in math, science, or arts.",
    4: "Pick one summer activity that sounds fun: a camp, a library program, or a project at home.",
}
_GRADE_11 = {
    1: "Start your college and training list; note costs for each.",
    3: "Visit campuses or join virtual tours; ask the counselor for test dates.",
    4: "Ask teachers you trust about recommendation letters before the school year ends.",
    6: "Summer: draft a college essay and research scholarships.",
    9: "Meet the counselor to plan tests and your college list.",
    10: "Ask the counselor about test dates and prep.",
}
_GRADE_12 = {
    1: "Complete the FAFSA and state aid forms if not done; keep applying for scholarships.",
    2: "Keep applying for scholarships and respond to any requests from colleges.",
    3: "Compare financial aid offers and ask questions.",
    4: "Make your final decision and follow the steps each school gives you.",
    9: "Finalize your college and training list and application dates with the counselor.",
    10: "Work on applications and ask for recommendation letters early. Ask the counselor when the FAFSA opens.",
    11: "Submit applications early and track every deadline.",
    12: "Finish remaining applications and thank the people who helped.",
}


def voice(text: str, profile: Profile) -> str:
    """Parents read 'your child's'; students read 'your'."""
    if profile.audience != "parent":
        return text
    text = re.sub(r"\byour\b", "your child's", text)
    text = re.sub(r"\bYour\b", "Your child's", text)
    return text.replace("you're curious", "your child is curious").replace("you like", "your child likes") \
        .replace("you've", "your child has").replace("you learned", "your child learned").replace("you enjoy", "your child enjoyed")


def _band_key(profile: Profile):
    if profile.grade is None or profile.grade <= 8:
        return "middle"
    return profile.grade


def checklist(profile: Profile) -> list[str]:
    return [voice(i, profile) for i in CHECKLIST[_band_key(profile)]]


def monthly_plan(profile: Profile, today: date, months: int = 6) -> list[dict]:
    """The next `months` months, starting this month: [{"date": date, "month": "November 2026", "action": str}]."""
    key = _band_key(profile)
    overrides = _MIDDLE if key == "middle" else _GRADE_11 if key == 11 else _GRADE_12 if key == 12 else {}
    plan, y, m = [], today.year, today.month
    for i in range(months):
        when = today if i == 0 else date(y, m, 1)
        action = overrides.get(m) or _GENERIC_MONTHS[m]
        plan.append({"date": when, "month": f"{date(y, m, 1):%B %Y}", "action": voice(action, profile)})
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return plan
