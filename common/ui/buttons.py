import streamlit as st

def render_action_buttons():

    cols = st.columns(5)

    actions = {}

    with cols[0]:
        actions["pdf"] = st.button("Generate PDF", use_container_width=True, key="btn_pdf")

    with cols[1]:
        actions["word"] = st.button("Generate Word", use_container_width=True, key="btn_word")

    with cols[2]:
        actions["bulk"] = st.button("Bulk Generate", use_container_width=True, key="btn_bulk")

    with cols[3]:
        actions["preview"] = st.button("Preview", use_container_width=True, key="btn_preview")

    with cols[4]:
        actions["clear"] = st.button("Clear", use_container_width=True, key="btn_clear")

    return actions
