import streamlit as st
import pandas as pd
import re
import io

from search.module.data_loader import load_data
from search.module.search import apply_search
from search.module.kpi import calculate_kpi


def render_search_page():

    st.title("Ops Insight Dashboard")

    df, last_refresh = load_data()

    # ---------- PRIORITY CLEAN ----------
    def clean_priority(row):
        if row["Source"] == "PTC":
            m = re.search(r"Severity\s*([1-3])", str(row["Priority"]))
            return f"Severity {m.group(1)}" if m else ""
        return row["Priority"]

    df["Priority"] = df.apply(clean_priority, axis=1)

    # ---------- SIDEBAR ----------
    with st.sidebar.expander("📂 Source", True):
        cols = st.columns(2)

        all_src = cols[0].checkbox("ALL", True)
        azure = cols[1].checkbox("AZURE", all_src)
        snow = cols[0].checkbox("SNOW", all_src)
        ptc = cols[1].checkbox("PTC", all_src)

        sources = ["AZURE", "SNOW", "PTC"] if all_src else []
        if not all_src:
            if azure:
                sources.append("AZURE")
            if snow:
                sources.append("SNOW")
            if ptc:
                sources.append("PTC")

        if not sources:
            st.stop()

    filtered = df[df["Source"].isin(sources)].copy()

    # ---------- FILTER ----------
    with st.sidebar.expander("🎯 Filters", True):
        status = st.multiselect("Status", sorted(filtered["Status"].dropna().unique()))
        priority = st.multiselect("Priority", sorted(filtered["Priority"].dropna().unique()))

    if status:
        filtered = filtered[filtered["Status"].isin(status)]
    if priority:
        filtered = filtered[filtered["Priority"].isin(priority)]

    # ---------- DATE FILTER (ADVANCED) ----------
    with st.sidebar.expander("📅 Date Filter", True):

        date_column = st.selectbox(
            "Select Date Field",
            ["Created Date", "Resolved Date"]
        )

        mode = st.radio(
            "Filter Type",
            ["No Filter", "Date Range", "By Year", "Quick Select"]
        )

        temp_dates = df[date_column]

        min_date = temp_dates.min()
        max_date = temp_dates.max()

        selected_year = None
        date_range = None
        quick_option = None

        if mode == "Date Range":
            date_range = st.date_input(
                "Select Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

        elif mode == "By Year":
            years = sorted(temp_dates.dt.year.dropna().unique())
            selected_year = st.selectbox("Select Year", years)

        elif mode == "Quick Select":
            quick_option = st.selectbox(
                "Quick Options",
                ["Last 7 Days", "Last 30 Days", "This Month"]
            )

    # ---------- APPLY DATE FILTER ----------
    if mode != "No Filter":

        filtered[date_column] = filtered[date_column]

        if mode == "Date Range" and date_range and len(date_range) == 2:
            start_date, end_date = date_range

            filtered = filtered[
                (filtered[date_column] >= pd.to_datetime(start_date)) &
                (filtered[date_column] <= pd.to_datetime(end_date))
            ]

        elif mode == "By Year" and selected_year:
            filtered = filtered[
                filtered[date_column].dt.year == selected_year
            ]

        elif mode == "Quick Select" and quick_option:
            today = pd.Timestamp.today()

            if quick_option == "Last 7 Days":
                start_date = today - pd.Timedelta(days=7)

            elif quick_option == "Last 30 Days":
                start_date = today - pd.Timedelta(days=30)

            elif quick_option == "This Month":
                start_date = today.replace(day=1)

            filtered = filtered[
                filtered[date_column] >= start_date
            ]

    # ---------- CLEAR FUNCTION ----------
    def clear_all():
        st.session_state["search_box"] = ""
        st.session_state["page"] = 1
        st.session_state["rows"] = 10

    # ---------- TOOLBAR ----------
    col1, col2, col3, col4, col5, col6 = st.columns([5, 1, 2, 1.5, 1.5, 2])

    with col1:
        search_value = st.text_input("🔎 Search", key="search_box")

    with col2:
        st.markdown("<div style='margin-top:30px'></div>", unsafe_allow_html=True)
        st.button("❌", on_click=clear_all)

    filtered = apply_search(filtered, search_value)

    df_display = filtered.reset_index(drop=True)
    df_display.insert(0, "SL No", range(1, len(df_display) + 1))

    total_rows = len(df_display)

    # ---------- RESULT COUNT ----------
    vc = filtered["Source"].value_counts()

    with col3:
        st.markdown(f"<b>{total_rows}</b> Results", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px;'>"
            f"AZURE: {vc.get('AZURE',0)} | "
            f"SNOW: {vc.get('SNOW',0)} | "
            f"PTC: {vc.get('PTC',0)}"
            f"</div>",
            unsafe_allow_html=True
        )

    with col4:
        page_size = st.selectbox("Rows", [10, 20, 50, 100], key="rows")

    total_pages = max(1, (total_rows // page_size) + (1 if total_rows % page_size else 0))

    with col5:
        page = st.selectbox("Page", list(range(1, total_pages + 1)), key="page")

    with col6:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)

        def to_excel(df):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return buffer.getvalue()

        st.download_button("📥 Download", to_excel(filtered), "ops_data.xlsx")

    # ---------- PAGINATION ----------
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df_display.iloc[start:end]

    # ---------- DATE FORMAT ----------
    for col in ["Created Date", "Resolved Date"]:
        if col in page_df:
            page_df[col] = page_df[col].dt.strftime("%d-%b-%y")

    page_df = page_df.fillna("")

    # ---------- LINK ----------
    def make_link(row):
        num = str(row.get("Number", ""))
        src = row.get("Source", "")

        if src == "SNOW":
            url = f"https://volvoitsm.service-now.com/nav_to.do?uri=incident.do?sysparm_query=number={num}"
        elif src == "PTC":
            url = f"https://support.ptc.com/appserver/cs/view/case.jsp?n={num}"
        elif src == "AZURE":
            url = f"https://dev.azure.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/{num}"
        else:
            url = ""

        if url:
            return f'<a href="{url}" target="_blank">Open</a>'
        return ""

    page_df["Open"] = page_df.apply(make_link, axis=1)

    # ---------- TABLE ----------
    st.write(page_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # ---------- KPI ----------
    with st.sidebar.expander("📈 KPI", True):
        kpi = calculate_kpi(filtered)

        c1, c2 = st.columns(2)
        c1.metric("Total", kpi["total"])
        c2.metric("Open", kpi["open"])

        c3, c4 = st.columns(2)
        c3.metric("Closed", kpi["closed"])
        c4.metric("Cancelled", kpi["cancelled"])

    st.caption(f"Last refreshed: {last_refresh}")
