import streamlit as st
from common.utils.links import make_ui_link
from common.utils.formatters import safe_text, format_date
from common.utils.text_cleaner import format_description


def render_preview_table(data):

    st.markdown("""
    <table class="preview-table">
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <tr>
        <td><b>INCIDENT</b></td>
        <td>{make_ui_link("incident", data.get("number"))}</td>
        <td><b>CREATED BY</b></td>
        <td>{safe_text(data.get("created_by"))}</td>
    </tr>
    <tr>
        <td><b>AZURE BUG</b></td>
        <td>{make_ui_link("azure", data.get("azure_bug"))}</td>
        <td><b>CREATED DATE</b></td>
        <td>{format_date(data.get("created_date"))}</td>
    </tr>
    <tr>
        <td><b>PTC CASE</b></td>
        <td>{safe_text(data.get("ptc_case"))}</td>
        <td><b>ASSIGNED TO</b></td>
        <td>{safe_text(data.get("assigned_to"))}</td>
    </tr>
    <tr>
        <td><b>PRIORITY</b></td>
        <td>{safe_text(data.get("priority"))}</td>
        <td><b>RESOLVED DATE</b></td>
        <td>{format_date(data.get("resolved_date"))}</td>
    </tr>
    </table>
    """, unsafe_allow_html=True)


def render_description_table(data):

    desc = format_description(data.get("description"))

    st.markdown(f"""
    <table class="preview-table">
    <tr>
        <td><b>SHORT DESCRIPTION</b></td>
        <td><b>DESCRIPTION</b></td>
    </tr>
    <tr>
        <td>{safe_text(data.get("short_description"))}</td>
        <td>{safe_text(desc)}</td>
    </tr>
    </table>
    """, unsafe_allow_html=True)
