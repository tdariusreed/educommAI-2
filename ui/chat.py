"""Chat panel. Streams the answer, but repaints at most ~6x/second (each repaint costs CPU)."""

import time

import streamlit as st

MAX_KEPT = 40   # messages kept in memory
MAX_SHOWN = 20  # messages drawn


def render_messages(messages: list[dict]) -> None:
    for m in messages[-MAX_SHOWN:]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])


def handle_input(assistant, user_id: str, session) -> None:
    text = st.chat_input("Ask about careers, school, or paying for college...")
    if not text:
        return
    messages = st.session_state.messages
    messages.append({"role": "user", "content": text})
    with st.chat_message("user"):
        st.markdown(text)
    with st.chat_message("assistant"):
        box, last = st.empty(), [0.0]

        def on_token(partial: str) -> None:
            if time.monotonic() - last[0] > 0.15:
                last[0] = time.monotonic()
                box.markdown(partial + " ▌")

        with st.spinner("Looking that up..."):
            turn = assistant.handle(user_id, text, session, on_token=on_token,
                                    use_llm=st.session_state.get("use_llm", True))
        box.markdown(turn.answer)
    messages.append({"role": "assistant", "content": turn.answer})
    del messages[:-MAX_KEPT]
    st.session_state.last_turn = turn
