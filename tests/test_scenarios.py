"""The three target scenarios, run end to end (fake search and model; nothing here needs a network)."""

from datetime import date

from memory.session_memory import SessionMemory
from tests.conftest import GOOD, SCHOLAR, FakeLLM, FakeSearch


def onboard(a, user, replies):
    s = SessionMemory()
    a.greet(user, s)
    for r in replies:
        turn = a.handle(user, r, s)
    return s, turn


# ---------- Scenario 1: high school student interested in finance ----------------------------------------------
STUDENT = {"role": "student", "grade": 11, "interests": ["finance", "investing", "math"], "location": "Atlanta, Georgia",
           "academics": "B+ average, Algebra II and AP Economics", "constraints": "First-generation; cost matters"}


def test_scenario1_finance_student_gets_pathways_classes_majors_scholarships_and_a_plan(make):
    search = FakeSearch()
    a = make(mode="off")
    a.update_profile("s1", STUDENT)
    t = a.handle("s1", "Make me a personalized roadmap", SessionMemory())
    for part in ("Careers that fit you", "Classes and majors", "Paying for it", "Your plan", "**Checklist**", "**Month by month**",
                 "November 2026", "FAFSA", "Dates found in sources"):
        assert part in t.answer, part
    assert f"[1]({SCHOLAR})" in t.answer or SCHOLAR in t.answer and GOOD in t.answer     # real links, from search results
    assert "March 1, 2027" in t.answer and "BEGIN:VCALENDAR" in t.ics and "20270301" in t.ics and "20261109" in t.ics
    assert t.agents_used == ["career_explorer", "courses", "funding", "plan"] and not t.used_llm


def test_scenario1_location_reaches_the_funding_search(make):
    search = FakeSearch()
    a = make(mode="off", search=search)
    a.update_profile("s1", STUDENT)
    a.handle("s1", "Find scholarships and local programs near me", SessionMemory())
    assert all("Atlanta" in q for q in search.queries) and len(search.queries) >= 2


def test_scenario1_with_the_model_one_call_with_plan_and_dates_in_the_prompt(make):
    llm = FakeLLM(text="Here is your plan. Analysts study markets [1].")
    a = make(llm=llm)
    a.update_profile("s1", STUDENT)
    t = a.handle("s1", "Make me a personalized roadmap", SessionMemory())
    prompt = llm.calls[0][1]["content"]
    assert len(llm.calls) == 1 and t.used_llm and llm.max_tokens == [900]
    assert "MONTH-BY-MONTH PLAN" in prompt and "CHECKLIST" in prompt and "DATES FOUND IN SOURCES" in prompt and "March 1, 2027" in prompt


# ---------- Scenario 2: middle schooler who likes math and science but cannot decide ----------------------------
def test_scenario2_middle_schooler_onboarding_matches_careers_and_offers_the_quiz(make):
    a = make(llm=FakeLLM())
    s, t = onboard(a, "m", ["student", "7th grade", "math and science", "skip"])
    assert "what would you like to explore" in t.answer.lower() and a.get_profile("m").interests == ["math", "science"]
    t = a.handle("m", "I like math and science but don't know what I want to be", s)
    assert t.agents_used == ["career_explorer"] and t.offer_quiz and not t.needs_input and t.sources == [GOOD]


def test_scenario2_summer_programs_and_learning_resources(make):
    search = FakeSearch()
    a = make(mode="off", search=search)
    a.update_profile("m", {"role": "student", "grade": 7, "interests": ["math", "science"], "location": "Macon, Georgia"})
    t = a.handle("m", "Are there summer programs for me?", SessionMemory())
    assert "Programs near you" in t.answer and "Macon, Georgia middle school math summer programs" in search.queries[0]
    t = a.handle("m", "Where can I learn more about engineering for free?", SessionMemory())
    assert "Free ways to learn" in t.answer and "engineering" in search.queries[-1] and "middle school" in search.queries[-1]


def test_scenario2_interest_quiz_end_to_end(make):
    a = make(mode="off")
    a.update_profile("m", {"role": "student", "grade": 7, "interests": ["art"]})
    s = SessionMemory()
    t = a.handle("m", "Give me an interest quiz", s)
    assert t.action == "quiz" and t.needs_input
    answers = [1, 1, 3, 1, 3, 3, 3, 3]                       # science / tech leaning
    assert len(a.quiz_questions()) == len(answers)
    t = a.finish_quiz("m", answers, s)
    assert t.answer.startswith("**Your top career clusters**") and "Science, Technology, Engineering & Math" in t.answer
    assert "Careers that fit you" in t.answer and t.sources                       # followed by sourced careers
    assert "science" in a.get_profile("m").interests and "art" in a.get_profile("m").interests


# ---------- Scenario 3: a busy parent --------------------------------------------------------------------------
def test_scenario3_parent_gets_a_plan_checklist_calendar_in_parent_voice(make):
    a = make(mode="off")
    s = SessionMemory()
    greeting = a.greet("p", s)
    assert "student, or a parent" in greeting.answer
    t = a.handle("p", "My daughter is in 9th grade and likes math and science. How can I help her prepare for college?", s)
    assert t.needs_input and "city or state" in t.answer                          # location asked once; the question is kept
    t = a.handle("p", "skip", s)
    p = a.get_profile("p")
    assert (p.role, p.grade, p.interests, p.location) == ("parent", 9, ["math", "science"], "")
    assert not t.needs_input and t.agents_used == ["education", "plan"]           # the original question was answered
    assert "your child's" in t.answer and "Month by month" in t.answer and "Checklist" in t.answer
    assert "BEGIN:VCALENDAR" in t.ics and "calendar file" in t.answer


def test_scenario3_programs_and_scholarship_list_and_deadlines(make):
    a = make(mode="off")
    a.update_profile("p", {"role": "parent", "grade": 9, "interests": ["math"], "location": "Georgia"})
    t = a.handle("p", "Which community programs are near us?", SessionMemory())
    assert "Programs near you" in t.answer and t.sources
    t = a.handle("p", "Remind me of scholarship deadlines", SessionMemory())
    assert "Dates found in sources" in t.answer and "March 1, 2027" in t.answer and "(the source doesn't give the year" not in t.answer
    assert SCHOLAR in t.answer and "20270301" in t.ics                       # dated, cited, and in the calendar file


def test_deadlines_are_never_invented(make):
    a = make(mode="off", search=FakeSearch(dated=False))
    a.update_profile("p", {"role": "parent", "grade": 9, "interests": ["math"]})
    t = a.handle("p", "Remind me of scholarship deadlines", SessionMemory())
    assert "didn't find specific deadline dates" in t.answer and "March 1" not in t.answer
    assert "BEGIN:VCALENDAR" in t.ics and "Date from a source" not in t.ics   # only the monthly plan reminders


def test_parent_prompt_uses_parent_style(make):
    llm = FakeLLM()
    a = make(llm=llm)
    a.update_profile("p", {"role": "parent", "grade": 9, "interests": ["math"]})
    a.handle("p", "How can I help her prepare for college?", SessionMemory())
    system = llm.calls[0][0]["content"]
    assert "busy parent or guardian of a high school student" in system and "your child" in system


def test_programs_are_searched_once_per_interest_not_one_blended_query(make):
    """Regression: "programs near me" from a student who likes history and art returned generic camp lists."""
    search = FakeSearch()
    a = make(mode="off", search=search)
    a.update_profile("h", {"role": "student", "grade": 7, "interests": ["history", "art"], "location": "Atlanta, Ga"})
    a.handle("h", "programs near me", SessionMemory())
    assert len(search.queries) == 2
    assert "history" in search.queries[0] and "art" not in search.queries[0].split()
    assert "art" in search.queries[1].split() and "history" not in search.queries[1]
    assert all("Atlanta" in q and "middle school" in q for q in search.queries)
