import streamlit as st
import pandas as pd
from datetime import date, timedelta


def render_sidebar(df):

    st.sidebar.header("Filters")

    priorities = st.sidebar.multiselect(
        "Priority",
        options=sorted(df["priority"].dropna().unique())
    )

    date_range = st.sidebar.date_input("Created Date Range", value=())

    preset = st.sidebar.selectbox(
        "Quick Filter",
        ["None", "Last 7 Days", "Last 30 Days"]
    )

    # ---------------- PRESET ---------------- #
    if preset == "Last 7 Days":
        date_range = (date.today() - timedelta(days=7), date.today())
    elif preset == "Last 30 Days":
        date_range = (date.today() - timedelta(days=30), date.today())

    # ---------------- FILTER ---------------- #
    filtered = df.copy()

    if priorities:
        filtered = filtered[filtered["priority"].isin(priorities)]

    filtered["created"] = pd.to_datetime(filtered["created"], errors="coerce")

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range

        filtered = filtered[
            (filtered["created"].dt.date >= start) &
            (filtered["created"].dt.date <= end)
        ]

    # ---------------- ACTION ---------------- #
    st.sidebar.markdown("### Actions")

    if st.sidebar.button("Apply to Bulk", key="apply_bulk_btn"):
    
        if filtered is None or filtered.empty:
            st.sidebar.warning("No filtered data available")
        else:
            inc_list = filtered["number"].astype(str).tolist()
    
            # ✅ Used by main_view auto-fill
            st.session_state["bulk_incidents_list"] = inc_list
    
            # ✅ Optional text version
            st.session_state["bulk_incidents"] = ", ".join(inc_list)
    
            st.sidebar.success(f"Applied to {len(inc_list)} incidents")

    # ---------------- DOWNLOAD ---------------- #
    st.sidebar.markdown("### Download")

    if st.session_state.get("pdf_ready") and "data" in st.session_state:
        st.sidebar.download_button(
            "⬇ Download PDF",
            st.session_state["pdf_bytes"],
            file_name=f"{st.session_state['data']['number']}.pdf"
        )

    if st.session_state.get("word_ready") and "data" in st.session_state:
        st.sidebar.download_button(
            "⬇ Download Word",
            st.session_state["word_bytes"],
            file_name=f"{st.session_state['data']['number']}.docx"
        )

    if st.session_state.get("zip_ready") and "data" in st.session_state:
        st.sidebar.download_button(
            "⬇ Download ZIP",
            st.session_state["zip_bytes"],
            file_name="Bulk_Report.zip"
        )

    return filtered
