from common.ui.styles import get_table_style
from common.utils.formatters import (
    format_description,
    format_date,
    safe_text
)
from common.utils.links import parse_ptc_cases

import os


def _val(x):
    return safe_text(x)


def _format_multiline(text):
    """
    Preserve line breaks from editable RCA sections
    """
    if not text:
        return "-"

    return safe_text(text).replace("\n", "<br>")


# ServiceNow incident URL
_SNOW_URL  = "https://volvoitsm.service-now.com/nav_to.do?uri=incident.do?sysparm_query=number={}"
# Azure DevOps bug URL (VCEWindchillPLM project — Azure Bug field)
_AZURE_URL = "https://dev.azure.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/{}"
# PTC support case URL
_PTC_URL   = "https://support.ptc.com/appserver/cs/view/case.jsp?n={}"


def _link(value, type_):
    """
    Build a clickable anchor for a single value.
    For type_ == "ptc", supports comma-separated and alpha-prefixed case numbers
    (e.g. "17979095, C1234567") — each rendered as an individual link.
    """
    value = safe_text(value)

    if value == "-":
        return "-"

    if type_ == "incident":
        url = _SNOW_URL.format(value)
        return f'<a href="{url}" target="_blank">{value}</a>'

    elif type_ == "azure":
        url = _AZURE_URL.format(value)
        return f'<a href="{url}" target="_blank">{value}</a>'

    elif type_ == "ptc":
        cases = parse_ptc_cases(value)
        if not cases:
            return value
        parts = []
        for display, num_id in cases:
            url = _PTC_URL.format(num_id)
            parts.append(f'<a href="{url}" target="_blank">{display}</a>')
        return ", ".join(parts)

    else:
        return value


def render_images(image_list):
    """
    Render uploaded images inside preview
    """

    if not image_list:
        return ""

    html = "<div style='margin-top:10px;'>"

    for img in image_list:
        filename = os.path.basename(img)

        html += f"""
        <div style="margin-bottom:15px;">
            <img
                src="/uploads/{filename}"
                style="
                    max-width:300px;
                    max-height:300px;
                    border:1px solid #ddd;
                    padding:5px;
                    border-radius:6px;
                "
            />
        </div>
        """

    html += "</div>"

    return html


def render_preview_html(
    data,
    root=None,
    l2=None,
    resolution=None,
    problem_images=None,
    root_images=None,
    resolution_images=None,
    references=None,          # list of reference dicts from references_service
):
    """
    Main preview renderer — renders incident header, description,
    RCA sections (with images), and a References table when references are found.
    """

    if not data:
        return "<h3>No data available for preview</h3>"

    problem_images = problem_images or []
    root_images = root_images or []
    resolution_images = resolution_images or []

    final_problem = root or data.get("problem") or "-"
    final_root = l2 or data.get("analysis") or "-"
    final_resolution = resolution or data.get("resolution") or "-"

    style = get_table_style()

    # -----------------------------------
    # INCIDENT DETAILS TABLE
    # -----------------------------------
    incident_table = f"""
    <table class="tbl preview-table">
        <tr>
            <td class="hdr">INCIDENT</td>
            <td>{_link(data.get("number"), "incident")}</td>

            <td class="hdr">CREATED BY</td>
            <td>{_val(data.get("created_by"))}</td>
        </tr>

        <tr>
            <td class="hdr">AZURE BUG</td>
            <td>{_link(data.get("azure_bug"), "azure")}</td>

            <td class="hdr">CREATED DATE</td>
            <td>{_val(format_date(data.get("created_date")))}</td>
        </tr>

        <tr>
            <td class="hdr">PTC CASE</td>
            <td>{_link(data.get("ptc_case"), "ptc")}</td>

            <td class="hdr">ASSIGNED TO</td>
            <td>{_val(data.get("assigned_to"))}</td>
        </tr>

        <tr>
            <td class="hdr">PRIORITY</td>
            <td>{_val(data.get("priority"))}</td>

            <td class="hdr">RESOLVED DATE</td>
            <td>{_val(format_date(data.get("resolved_date")))}</td>
        </tr>
    </table>
    """

    # -----------------------------------
    # DESCRIPTION TABLE
    # -----------------------------------
    description_table = f"""
    <table class="tbl preview-table">
        <tr>
            <td class="hdr">SHORT DESCRIPTION</td>
            <td class="hdr">DESCRIPTION</td>
        </tr>

        <tr>
            <td>{_val(data.get("short_description"))}</td>
            <td>{_val(format_description(data.get("description")))}</td>
        </tr>
    </table>
    """

    # -----------------------------------
    # RCA TABLE
    # -----------------------------------
    rca_table = f"""
    <table class="tbl preview-table">
        <tr>
            <td class="hdr">PROBLEM STATEMENT</td>
            <td>
                {_format_multiline(final_problem)}
                {render_images(problem_images)}
            </td>
        </tr>

        <tr>
            <td class="hdr">ROOT CAUSE</td>
            <td>
                {_format_multiline(final_root)}
                {render_images(root_images)}
            </td>
        </tr>

        <tr>
            <td class="hdr">RESOLUTION</td>
            <td>
                {_format_multiline(final_resolution)}
                {render_images(resolution_images)}
            </td>
        </tr>
    </table>
    """

    # -----------------------------------
    # REFERENCES TABLE (Azure VPA + PTC articles)
    # -----------------------------------
    # Use references passed in, or fall back to what prepare_data stored
    refs_list = references if references is not None else (data.get("references") or [])

    if refs_list:
        try:
            from report.module.services.references_service import render_references_html
            refs_html = render_references_html(refs_list)
        except ImportError:
            refs_html = ""
    else:
        refs_html = ""

    references_section = f"""
    <table class="tbl preview-table">
        <tr>
            <td class="hdr" style="width:180px;">REFERENCES</td>
            <td>
                {refs_html if refs_html else "<span style='color:#94a3b8;font-size:12px;'>No Azure user stories or PTC articles found in notes.</span>"}
            </td>
        </tr>
    </table>
    """ if refs_list else ""

    html = f"""
    <div class="preview-wrapper">
        <div class="preview-table-container">
            {style}

            {incident_table}
            <br>

            {description_table}
            <br>

            {rca_table}

            {"<br>" + references_section if references_section else ""}
        </div>
    </div>
    """

    return html