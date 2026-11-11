"""Sidebar: what the assistant knows, plus a quick edit form."""

import streamlit as st

from ui.profile_view import render_known

GRADES = [None, 6, 7, 8, 9, 10, 11, 12]
ROLES = ["", "student", "parent"]
ROLE_LABELS = {"": "Choose...", "student": "A student", "parent": "A parent, guardian, teacher, or counselor"}


def render_sidebar(assistant, user_id: str) -> None:
    with st.sidebar:
        st.header("About you")
        st.caption("Please don't share your full name, address, phone number, or school.")
        render_known(assistant, user_id)
        if assistant.has_model:
            st.toggle("Use the AI model to write answers", value=True, key="use_llm",
                      help="Off = faster and uses less memory. Answers are built straight from the sources.")
        if st.button("📝 Interest quiz", help="8 quick questions that match you to career clusters"):
            st.session_state.quiz_open = True
            st.rerun()
        p = assistant.get_profile(user_id)
        with st.expander("Edit my info"):
            with st.form("profile_form"):
                role = st.selectbox("I am", ROLES, index=ROLES.index(p.role) if p.role in ROLES else 0,
                                    format_func=ROLE_LABELS.get)
                grade = st.selectbox("Grade", GRADES, index=GRADES.index(p.grade),
                                     format_func=lambda g: "Choose..." if g is None else str(g))
                interests = st.text_input("Interests (comma separated)", ", ".join(p.interests))
                academics = st.text_input("Classes / how school is going", p.academics)
                location = st.text_input("City or state", p.location)
                constraints = st.text_input("Anything that matters (cost, family, etc.)", p.constraints)
                goal = st.text_input("What do you want to figure out?", p.goal)
                if st.form_submit_button("Save"):
                    assistant.update_profile(user_id, {"role": role, "grade": grade, "interests": interests, "academics": academics,
                                                       "location": location, "constraints": constraints, "goal": goal})
                    st.rerun()
