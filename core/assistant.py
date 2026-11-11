"""One turn:  safety -> memory -> router -> search (parallel) -> ONE write-up call -> verify -> reply."""

from __future__ import annotations

from datetime import date

import config
from agents.intake_agent import extract_freetext, extract_updates, next_field, next_question
from core import deadlines, ics, planner, quiz, verifier, writer
from core.executor import gather_evidence
from core.llm_client import LLMClient
from core.models import TurnResult
from core.orchestrator import asks_deadlines, route
from core.safety import check_input, check_output
from core.tracing import Trace
from memory.profile_store import ProfileStore
from memory.session_memory import SessionMemory
from memory.vector_store import KnowledgeStore
from tools.search_tool import make_search

_UNSET = object()
QUIZ_INTRO = "Let's find out what you might enjoy! Here is a quick 8-question quiz. There are no wrong answers: pick the option that sounds most like you."
CALENDAR_NOTE = "\n\n📅 I can't send reminders myself, but you can download a calendar file with the monthly reminders and any dates found in the sources. Please review the plan with a parent, teacher, or counselor first."


class Assistant:
    def __init__(self, llm=None, search=None, db_path=None, knowledge_dir=None, mode=None, today=None):
        mode = mode or config.LLM_MODE
        self.llm = None if mode == "off" else (llm or LLMClient())
        self.search = search or make_search()
        self.profiles = ProfileStore(db_path or config.DB_PATH)
        self._knowledge_dir = knowledge_dir or config.KNOWLEDGE_DIR
        self._knowledge = _UNSET
        self._today = today or date.today

    def _knowledge_store(self):
        """Built on first use, and only if there are documents to index (nothing held in RAM otherwise)."""
        if self._knowledge is _UNSET:
            self._knowledge = KnowledgeStore(self._knowledge_dir) if KnowledgeStore.has_documents(self._knowledge_dir) else None
        return self._knowledge

    @property
    def has_model(self) -> bool:
        return self.llm is not None

    # --- profile helpers used by the UI --------------------------------------------------
    def get_profile(self, user_id):
        return self.profiles.load(user_id)

    def profile_fields(self, user_id):
        return self.profiles.fields(user_id)

    def update_profile(self, user_id, updates):
        return self.profiles.set_fields(user_id, updates, replace=True)

    def delete_profile_field(self, user_id, key):
        self.profiles.delete_field(user_id, key)

    def delete_user_data(self, user_id):
        self.profiles.delete_all(user_id)

    def _remember(self, user_id, updates, trace) -> None:
        if updates and self.profiles.set_fields(user_id, updates):
            trace.add("memory_write", "memory", fields=sorted(updates))

    def greet(self, user_id: str, session: SessionMemory) -> TurnResult:
        """Opening message. No model call, no search."""
        profile = self.profiles.load(user_id)
        session.intake_active = bool(profile.missing_required())
        field, text = next_question(profile, True, session)
        session.awaiting, session.greeted = field, True
        return TurnResult(answer=text, needs_input=True, agents_used=["intake"], trace=Trace())

    # --- one turn ------------------------------------------------------------------------
    def handle(self, user_id: str, text: str, session: SessionMemory | None = None, on_token=None,
               use_llm: bool = True) -> TurnResult:
        session = session or SessionMemory()
        trace = Trace()

        safety = check_input(text)
        trace.add("safety", "safety", allowed=safety.allowed, flags=safety.flags)
        if not safety.allowed:
            return TurnResult(answer=safety.reply, blocked=True, flags=safety.flags, trace=trace)
        question = safety.text
        awaiting = session.awaiting

        # 1. a direct answer to the intake question we just asked, and 2. facts stated in ordinary text
        if awaiting in ("role", "grade", "interests"):
            self._remember(user_id, extract_updates(question, awaiting), trace)
        profile = self.profiles.load(user_id)
        self._remember(user_id, extract_freetext(question, profile), trace)
        profile = self.profiles.load(user_id)

        plan = route(question, profile.audience)
        trace.add("routing", "router", agents=plan.agents, role=profile.audience)
        is_question = bool(plan.agents) and ("?" in question or len(question.split()) >= 8)

        if awaiting == "location":  # optional step: answer it, skip it, or ask something else instead
            session.location_asked = True
            if is_question:
                awaiting = None
            else:
                self._remember(user_id, extract_updates(question, "location"), trace)
                profile = self.profiles.load(user_id)

        if plan.agents == ["quiz"]:
            return self._reply(trace, QUIZ_INTRO, needs_input=True, action="quiz")

        # Intake: who is asking, grade, interests, then (once) where they live.
        if profile.missing_required():
            session.intake_active = True
        if next_field(profile, session):
            if is_question and not session.pending_question:
                session.pending_question = question  # answer it once intake is done
            field, msg = next_question(profile, not session.greeted, session)
            session.awaiting, session.greeted = field, True
            return self._reply(trace, msg, needs_input=True, agents=["intake"])

        session.awaiting = None
        if awaiting is not None:  # intake just finished
            pending, session.pending_question = session.pending_question, None
            pending = pending or (question if is_question else None)
            if not pending:
                return self._reply(trace, next_question(profile, False, session)[1], needs_input=True, agents=["intake"])
            question, plan = pending, route(pending, profile.audience)
            trace.add("resume", "router", question=question, agents=plan.agents)
        else:
            session.pending_question = None

        if not plan.agents:
            return self._reply(trace, plan.clarifying_question, needs_input=True)

        today = self._today()
        evidence = gather_evidence(plan.agents, question, profile, self.search, self._knowledge_store(), trace)
        extra = self._plan_extras(plan.agents, question, profile, evidence, today, trace)
        draft, used_llm = writer.write(self.llm if use_llm else None, profile, question, plan.agents, evidence,
                                       on_token, trace, extra)
        final, cited, issues = verifier.finalize(draft, evidence, trace) if evidence else (draft, [], ["no sources found"])
        final, flags = check_output(final)
        calendar = self._calendar(extra, today)
        if calendar:
            final += CALENDAR_NOTE
        return self._reply(trace, final, sources=cited, issues=issues, flags=flags, agents=plan.agents,
                           used_llm=used_llm, ics=calendar,
                           offer_quiz=plan.offer_quiz or (profile.band == "middle" and "career_explorer" in plan.agents))

    # --- plan, deadlines, calendar -------------------------------------------------------
    @staticmethod
    def _plan_extras(agents, question, profile, evidence, today, trace) -> dict:
        extra: dict = {}
        if "plan" in agents:
            extra["checklist"] = planner.checklist(profile)
            extra["months"] = planner.monthly_plan(profile, today)
        if "plan" in agents or "funding" in agents:
            found = deadlines.extract(evidence, today)
            if found:
                extra["deadlines"] = found
            elif asks_deadlines(question):
                extra["asked_deadlines"] = True
            trace.add("deadlines", "planner", found=len(found))
        return extra

    @staticmethod
    def _calendar(extra: dict, today) -> str:
        events = [{"date": m["date"], "summary": f"Plan: {m['action'][:70]}", "description": m["action"]}
                  for m in extra.get("months", [])]
        for d in extra.get("deadlines", []):
            note = " (the source gave no year; confirm it)" if d["year_guessed"] else ""
            events.append({"date": d["date"], "summary": f"Date from a source: {d['title'][:60]}",
                           "description": f"{d['context']}{note} Source: {d['url']}. Confirm on the official page."})
        return ics.make_ics(events)

    # --- interest quiz -------------------------------------------------------------------
    @staticmethod
    def quiz_questions():
        return quiz.QUESTIONS

    def finish_quiz(self, user_id: str, answers: list, session: SessionMemory | None = None, on_token=None,
                    use_llm: bool = True) -> TurnResult:
        """Score the quiz, remember the top interests, then answer 'what careers are in these clusters?'
        with real sources. Needs no model to score; the write-up follows the usual rules."""
        session = session or SessionMemory()
        top = quiz.score(answers)
        if not top:
            return TurnResult(answer="Pick an answer for at least a few of the questions and I'll show your matches.", needs_input=True)
        self.profiles.set_fields(user_id, {"interests": [c["keywords"].split()[0] for c in top[:2]]})
        names = " and ".join(c["name"] for c in top[:2])
        turn = self.handle(user_id, f"What careers are in {names}?", session, on_token=on_token, use_llm=use_llm)
        turn.answer = quiz.summary(top) + "\n\n" + turn.answer
        turn.offer_quiz = False
        return turn

    @staticmethod
    def _reply(trace, answer, sources=None, issues=None, flags=None, agents=None, needs_input=False,
               used_llm=False, action="", ics="", offer_quiz=False) -> TurnResult:
        trace.add("response", chars=len(answer), used_llm=used_llm)
        return TurnResult(answer=answer, sources=sources or [], agents_used=agents or [], needs_input=needs_input,
                          used_llm=used_llm, action=action, offer_quiz=offer_quiz, ics=ics, flags=flags or [],
                          issues=issues or [], trace=trace)
