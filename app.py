"""Streamlit app.   Run:  streamlit run app.py"""

import uuid

import streamlit as st

import config
from core.assistant import Assistant
from memory.session_memory import SessionMemory
from ui.chat import handle_input, render_messages
from ui.quiz_view import render_actions
from ui.sidebar import render_sidebar
from ui.trace_view import render_trace

st.set_page_config(page_title="Career Planning Assistant", page_icon="🎓", layout="wide")


@st.cache_resource
def get_assistant() -> Assistant:
    return Assistant()


def init_state(assistant: Assistant) -> None:
    if "session" in st.session_state:
        return
    # Private random id for this browser session. With EDUCOMM_URL_ID=1 it also lives in the URL (bookmarkable, but
    # anyone with the link can see that profile), so that is off by default for public deployments.
    user_id = (config.URL_ID and st.query_params.get("u")) or f"s{uuid.uuid4().hex[:10]}"
    if config.URL_ID:
        st.query_params["u"] = user_id
    st.session_state.user_id = user_id
    st.session_state.session = SessionMemory()
    turn = assistant.greet(user_id, st.session_state.session)  # no model call
    st.session_state.messages = [{"role": "assistant", "content": turn.answer}]
    st.session_state.last_turn = None


assistant = get_assistant()
init_state(assistant)
st.title("🎓 Career Planning Assistant")
st.caption("Explore careers, what school or training they need, and ways to pay for it.")

# Order matters: the chat runs BEFORE the quiz, trace and sidebar are drawn, so they already show the
# updated state and the page never needs a second full rerun after each answer.
render_messages(st.session_state.messages)
handle_input(assistant, st.session_state.user_id, st.session_state.session)
render_actions(assistant, st.session_state.user_id, st.session_state.session)
render_trace(st.session_state.last_turn)
render_sidebar(assistant, st.session_state.user_id)
