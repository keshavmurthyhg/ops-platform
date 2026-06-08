import streamlit as st

def init_state():
    defaults = {
        "filtered_df": None,
        "selected_incident": None,
        "images": {},
        "bulk_reports": None,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
