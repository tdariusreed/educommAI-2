"""Interest quiz form, the quiz offer, and the calendar download. Nothing here runs a model until Submit."""

import streamlit as st

MAX_KEPT = 40


def render_actions(assistant, user_id: str, session) -> None:
    turn = st.session_state.last_turn
    if turn is not None and turn.action == "quiz":
        st.session_state.quiz_open = True
    if st.session_state.get("quiz_open"):
        _quiz_form(assistant, user_id, session)
    elif turn is not None and turn.offer_quiz:
        if st.button("📝 Not sure yet? Take the 8-question interest quiz"):
            st.session_state.quiz_open = True
            st.session_state.last_turn = None  # the offer is used up
            st.rerun()
    if turn is not None and turn.ics:
        # Human review step: the plan is a draft. The calendar file is offered only after the person confirms that a
        # parent, teacher, or counselor has looked at it. (A confirmation, not a verification: see GOVERNANCE.md.)
        reviewed = st.checkbox("A parent, teacher, or counselor has reviewed this plan with me",
                               key=f"reviewed_{len(st.session_state.messages)}")
        if reviewed:
            st.download_button("📅 Download reminders (.ics)", turn.ics, file_name="educommAI-plan.ics",
                               mime="text/calendar", help="Opens in Google Calendar, Apple Calendar, or Outlook.")
        else:
            st.caption("This plan is a draft. Check it with an adult you trust, then tick the box to get the calendar file.")


def _quiz_form(assistant, user_id: str, session) -> None:
    with st.form("quiz_form"):
        st.subheader("Interest quiz")
        st.caption("No wrong answers. Pick what sounds most like you; you can skip any question.")
        picks = []
        for i, (question, options) in enumerate(assistant.quiz_questions()):
            labels = [text for text, _ in options]
            choice = st.radio(f"{i + 1}. {question}", labels, index=None, key=f"quiz_{i}")
            picks.append(labels.index(choice) if choice is not None else None)
        done, cancel = st.columns(2)
        submitted, cancelled = done.form_submit_button("Show my matches"), cancel.form_submit_button("Close")
    if cancelled:
        st.session_state.quiz_open = False
        st.rerun()
    if submitted:
        if not any(p is not None for p in picks):
            st.warning("Pick at least a few answers first.")
            return
        with st.spinner("Matching you to careers..."):
            turn = assistant.finish_quiz(user_id, picks, session, use_llm=st.session_state.get("use_llm", True))
        messages = st.session_state.messages
        messages.append({"role": "assistant", "content": turn.answer})
        del messages[:-MAX_KEPT]
        st.session_state.quiz_open = False
        st.session_state.last_turn = turn
        st.rerun()
