import streamlit as st
from common.data.snow_loader import load_snow_data

from report.module.ui.state import init_state
from report.module.ui.sidebar import render_sidebar
from report.module.ui.main_view import render_main


def render_doc_generator():
    init_state()

    # ---------------- LOAD DATA ---------------- #
    df = load_snow_data()

    # ✅ HARD CHECK (CRITICAL FIX)
    if df is None:
        st.error("❌ Failed to load data")
        return

    if not hasattr(df, "columns"):
        st.error("❌ Invalid data format")
        st.write("DEBUG TYPE:", type(df))
        return

    if df.empty:
        st.warning("⚠️ No data available")
        return

    # ---------------- SIDEBAR FILTER ---------------- #
    filtered = render_sidebar(df)

    # ✅ SECOND SAFETY CHECK
    if filtered is None or not hasattr(filtered, "columns"):
        st.error("❌ Filter returned invalid data")
        st.write("DEBUG FILTER TYPE:", type(filtered))
        return

    # ---------------- STORE ---------------- #
    st.session_state.filtered_df = filtered

    # ---------------- MAIN VIEW ---------------- #
    render_main(filtered)


if __name__ == "__main__":
    render_doc_generator()
