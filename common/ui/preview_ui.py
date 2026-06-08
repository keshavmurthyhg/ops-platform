from common.ui.styles import get_table_style
from common.utils.formatters import (
    format_description,
    format_date,
    safe_text
)

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


def _link(value, type_):
    value = safe_text(value)

    if value == "-":
        return "-"

    if type_ == "incident":
        url = (
            "https://volvoitsm.service-now.com/"
            f"nav_to.do?uri=incident.do?sysparm_query=number={value}"
        )

    elif type_ == "azure":
        url = (
            "https://dev.azure.com/VolvoGroup-DVP/"
            f"VCEWindchillPLM/_workitems/edit/{value}"
        )

    elif type_ == "ptc":
        url = (
            "https://support.ptc.com/appserver/"
            f"cs/view/solution.jsp?n={value}"
        )

    else:
        return value

    return f'<a href="{url}" target="_blank">{value}</a>'


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
    resolution_images=None
):
    """
    Main preview renderer
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

    html = f"""
    <div class="preview-wrapper">
        <div class="preview-table-container">
            {style}

            {incident_table}
            <br>

            {description_table}
            <br>

            {rca_table}
        </div>
    </div>
    """

    return html