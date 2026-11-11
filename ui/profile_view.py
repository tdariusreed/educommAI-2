"""'What I know about you': everything stored, with delete buttons."""

import streamlit as st

LABELS = {"role": "You are", "grade": "Grade", "interests": "Interests", "academics": "School", "location": "Where you live",
          "constraints": "Things that matter", "goal": "Your goal"}


def render_known(assistant, user_id: str) -> None:
    st.subheader("What I know about you")
    fields = assistant.profile_fields(user_id)
    if not fields:
        st.caption("Nothing yet. Tell me about yourself in the chat, or use the form below.")
    for key, value in fields:
        text_col, btn_col = st.columns([5, 1])
        text_col.markdown(f"**{LABELS.get(key, key)}:** {', '.join(value) if isinstance(value, list) else value}")
        if btn_col.button("✕", key=f"del_{key}", help="Forget this"):
            assistant.delete_profile_field(user_id, key)
            st.rerun()
    if fields and st.button("Delete everything about me"):
        assistant.delete_user_data(user_id)
        st.session_state.messages = []
        st.session_state.session.clear()
        st.session_state.last_turn = None
        st.session_state.quiz_open = False
        st.rerun()
