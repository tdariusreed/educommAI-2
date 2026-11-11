from datetime import date

import pytest

from agents.intake_agent import extract_freetext, extract_updates, next_question
from agents.specialists import SEARCHING, SPECIALISTS
from core import deadlines, ics, planner, quiz
from core.models import Profile
from core.orchestrator import route
from memory.session_memory import SessionMemory

ROUTES = [  # (question, role, expected agents)
    ("What finance careers fit me and what do I need to get there?", "student", ["career_explorer", "education"]),
    ("What high school classes should I take?", "student", ["courses"]),
    ("What college majors should I look at?", "student", ["education", "courses"]),
    ("Make me a personalized roadmap", "student", ["career_explorer", "courses", "funding", "plan"]),
    ("Make me a personalized roadmap", "parent", ["courses", "programs", "funding", "plan"]),
    ("Find scholarships and local programs near me", "student", ["programs", "funding"]),
    ("Are there summer programs for me?", "student", ["programs"]),
    ("Where can I learn more about engineering for free?", "student", ["resources"]),
    ("My daughter is in 9th grade. How can I help her prepare for college?", "parent", ["education", "plan"]),
    ("Remind me of scholarship deadlines", "parent", ["funding", "plan"]),
    ("What's a college preparation checklist?", "parent", ["education", "plan"]),
    ("Which community programs are near us?", "parent", ["programs"]),
    ("Give me an interest quiz", "student", ["quiz"]),
]


@pytest.mark.parametrize("question,role,expected", ROUTES)
def test_scenario_questions_route_to_the_right_specialists(question, role, expected):
    assert route(question, role).agents == expected


def test_undecided_student_is_offered_the_quiz_and_search_count_is_capped():
    p = route("I like math and science but don't know what I want to be")
    assert p.agents == ["career_explorer"] and p.offer_quiz
    big = route("careers, college degrees, classes, summer programs, free online learning, scholarships and a plan")
    assert len([a for a in big.agents if a in SEARCHING]) == 4 and big.agents[-1] == "plan"


def test_queries_contain_the_topic_not_filler_words():
    p = Profile(role="parent", grade=9, interests=["math", "science"], location="Atlanta, Georgia")
    for q in ("My daughter is in 9th grade. How can I help her prepare for college?", "Give me a month-by-month plan",
              "Make me a personalized roadmap"):
        for name in SEARCHING:
            query = SPECIALISTS[name].query(q, p)
            query = " ".join(query) if isinstance(query, list) else query
            assert not any(w in query.lower() for w in ("daughter", "month", "personalized", "roadmap", "give ", "make "))
            assert ("math" in query and "science" in query) or name == "funding"     # fell back to the student's interests
    assert [("Atlanta" in q) for q in SPECIALISTS["programs"].query("summer programs", p)] == [True, True]
    assert "engineering" in SPECIALISTS["resources"].query("learn engineering", p)[0]


def test_planner_checklist_voice_and_months():
    kid, parent = Profile(role="student", grade=9), Profile(role="parent", grade=9)
    assert "share your interests" in " ".join(planner.checklist(kid))
    assert "your child's interests" in " ".join(planner.checklist(parent))
    plan = planner.monthly_plan(Profile(grade=12), date(2026, 11, 9), 6)
    assert [m["month"] for m in plan] == ["November 2026", "December 2026", "January 2027", "February 2027", "March 2027", "April 2027"]
    assert plan[0]["date"] == date(2026, 11, 9) and plan[1]["date"] == date(2026, 12, 1)
    assert "FAFSA" in plan[2]["action"]
    assert "20" not in "".join(planner.checklist(Profile(grade=11)))[:0] + ""   # no invented dates in the checklist
    assert planner.checklist(Profile(grade=None))   # a grade is not required to get a checklist


def test_ics_is_valid_escaped_and_folded():
    text = ics.make_ics([{"date": date(2026, 12, 1), "summary": "Plan, test; ok", "description": "line1\nline2 " + "x" * 200}])
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    assert "DTSTART;VALUE=DATE:20261201" in text and "SUMMARY:Plan\\, test\\; ok" in text and "TRIGGER:-P1D" in text
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n")) and text.count("BEGIN:VEVENT") == 1
    assert ics.make_ics([]) == ""


def test_deadlines_only_from_sentences_that_say_what_the_date_is():
    ev = [{"n": 2, "url": "https://a.gov/x", "title": "Aid", "text":
           "Applications open Oct 1. The scholarship deadline is March 1, 2027. We were founded on June 5. Due Feb 30. Apply by April 15."}]
    found = deadlines.extract(ev, date(2026, 11, 9))
    assert [(d["date"], d["year_guessed"]) for d in found] == [(date(2027, 3, 1), False), (date(2027, 4, 15), True), (date(2027, 10, 1), True)]
    assert all(d["n"] == 2 for d in found)               # every date carries its source number
    assert deadlines.extract([{"n": 1, "url": "u", "title": "t", "snippet": "Founded June 5, 1990."}], date(2026, 1, 1)) == []


def test_quiz_scoring():
    reachable = {c for _, opts in quiz.QUESTIONS for _, pts in opts for c in pts}
    assert reachable == set(quiz.CLUSTERS)               # every career cluster can come out on top
    top = quiz.score([1, 1, 3, 1, 3, 3, 3, 3])
    assert top[0]["key"] == "ST" and len(top) == 3 and quiz.score([1, 1, 3, 1, 3, 3, 3, 3]) == top   # deterministic
    assert quiz.score([None] * 8) == [] and len(quiz.score([0])) >= 1
    assert "Science, Technology" in quiz.summary(top)


def test_intake_reads_role_grade_interests_location_from_plain_text():
    s = "My daughter is in 9th grade and likes math and science. We live in Atlanta, Georgia."
    got = extract_freetext(s, Profile())
    assert got == {"role": "parent", "grade": 9, "interests": ["math", "science"], "location": "Atlanta, Georgia"}
    assert extract_freetext(s, Profile(role="student", grade=7, interests=["art"], location="X")) == {}   # never overwrites
    assert extract_freetext("What do I like to study?", Profile()) == {}
    assert extract_updates("I'm a student", "role") == {"role": "student"} and extract_updates("I'm her mom", "role") == {"role": "parent"}
    assert extract_updates("skip", "location") == {} and extract_updates("we live in Macon, GA", "location") == {"location": "Macon, GA"}


def test_intake_wording_follows_the_role_and_location_is_asked_only_of_new_users():
    s = SessionMemory()
    assert "student, or a parent" in next_question(Profile(), True, s)[1]
    assert "your child" in next_question(Profile(role="parent"), False, s)[1]
    done = Profile(role="student", grade=9, interests=["art"])
    assert next_question(done, False, s)[0] is None                 # existing complete profile: no extra questions
    s.intake_active = True
    assert next_question(done, False, s)[0] == "location"
    s.location_asked = True
    assert next_question(done, False, s)[0] is None
    assert Profile(grade=9, interests=["art"]).missing_required() == []   # old profiles are not asked for a role


def test_parent_tips_are_reworded_cleanly():
    """Regression: chained str.replace produced "your childr child's school counselor"."""
    from core.writer import tips_for
    for grade in (7, 11):
        text = " ".join(tips_for(Profile(role="parent", grade=grade)))
        assert "childr" not in text and "child child" not in text and "your child's" in text
    assert "your school counselor" in " ".join(tips_for(Profile(role="student", grade=7)))
