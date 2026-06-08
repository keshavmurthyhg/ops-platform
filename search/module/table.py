import streamlit as st
import pandas as pd
import re


def clean_name(val):
    if pd.isna(val):
        return val
    val = str(val)
    val = re.sub(r"\s*<.*?>", "", val)
    val = re.sub(r"\s*\(.*?\)", "", val)
    return val.strip()


def build_link(row):
    num = str(row.get("Number", ""))
    src = row.get("Source", "")

    if src == "SNOW":
        return f"https://volvoitsm.service-now.com/nav_to.do?uri=incident.do?sysparm_query=number={num}"
    elif src == "PTC":
        return f"https://support.ptc.com/appserver/cs/view/case.jsp?n={num}"
    elif src == "AZURE":
        return f"https://dev.azure.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/{num}"
    return ""


def show_table(df, page, page_size):

    if df.empty:
        st.warning("No data")
        return

    df = df.copy().reset_index(drop=True)

    # SL NO
    df.insert(0, "SL No", df.index + 1)

    # CLEAN NAMES
    for col in ["Created By", "Assigned To"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_name)

    # DATE FORMAT
    for col in ["Created Date", "Resolved Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%d-%b-%y")

    # REMOVE .0
    if "Assigned To" in df.columns:
        df["Assigned To"] = df["Assigned To"].astype(str).str.replace(".0", "", regex=False)

    # LINK
    df["Open"] = df.apply(
        lambda row: f'<a href="{build_link(row)}" target="_blank">Open</a>' if build_link(row) else "",
        axis=1
    )

    # PAGINATION
    start = (page - 1) * page_size
    end = start + page_size
    df_page = df.iloc[start:end]

    cols = [
        "SL No", "Number", "Description", "Priority", "Status",
        "Created By", "Created Date", "Assigned To",
        "Resolved Date", "Source", "Open"
    ]

    df_page = df_page[[c for c in cols if c in df_page.columns]]

    st.dataframe(
        df_page,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Open": st.column_config.LinkColumn("🔗"),
            "Description": st.column_config.TextColumn(width="large"),
        }
    )
