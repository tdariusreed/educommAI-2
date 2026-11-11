"""'How I got this answer': one text block (many small widgets are slow to rerender)."""

import streamlit as st


def render_trace(turn) -> None:
    if turn is None or turn.trace is None or not turn.trace.events:
        return
    with st.expander("How I got this answer"):
        st.caption("Written by the AI model" if turn.used_llm else "Built directly from the sources (no AI model used)")
        if turn.issues:
            st.warning("Checks: " + "; ".join(turn.issues))
        st.code("\n".join(turn.trace.to_lines()), language="text")
