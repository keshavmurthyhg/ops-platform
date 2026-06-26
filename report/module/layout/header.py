from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors

from common.utils.links import get_url, make_pdf_link, parse_ptc_cases

# PTC support case URL — must match links.py get_url("ptc case", ...)
_PTC_CASE_URL = "https://support.ptc.com/appserver/cs/view/case.jsp?n={}"


def build_pdf_header(data, wrap_link, format_date):

    def wrap(x):
        return Paragraph(str(x or "-"), style=None)

    def safe_link(field, value):
        """Keep links clickable while preventing blank values."""
        if not value:
            return wrap("-")
        value = str(value).strip()
        if value.lower() in ["nan", "none", "nat", "-"]:
            return wrap("-")
        try:
            url = get_url(field, value)
            if url:
                return wrap_link(field, value)
            return wrap(value)
        except Exception as e:
            print(f"{field} link error:", e)
            return wrap(value)

    def build_ptc_cell(raw):
        """
        Build a Paragraph with each PTC case individually hyperlinked.
        Uses parse_ptc_cases from links.py — handles comma-separated lists
        and alpha-prefixed IDs (e.g. C1234567 → strips to 1234567 for URL).
        """
        if not raw:
            return wrap("-")
        raw = str(raw).strip()
        if raw.lower() in ("nan", "none", "nat", "-", ""):
            return wrap("-")

        cases = parse_ptc_cases(raw)   # [(display, num_id), ...]
        if not cases:
            return wrap(raw)

        parts_html = []
        for display, num_id in cases:
            url = _PTC_CASE_URL.format(num_id)
            parts_html.append(
                f'<link href="{url}" color="#000000">{display}</link>'
            )

        return Paragraph(", ".join(parts_html), style=None)

    table = Table(
        [
            [
                "INCIDENT",
                safe_link("incident", data.get("number")),
                "CREATED BY",
                wrap(data.get("created_by"))
            ],
            [
                "AZURE BUG",
                safe_link("azure bug", data.get("azure_bug")),
                "CREATED DATE",
                wrap(format_date(data.get("created_date")))
            ],
            [
                "PTC CASE",
                build_ptc_cell(data.get("ptc_case")),
                "ASSIGNED TO",
                wrap(data.get("assigned_to"))
            ],
            [
                "PRIORITY",
                wrap(data.get("priority")),
                "RESOLVED DATE",
                wrap(format_date(data.get("resolved_date")))
            ]
        ],
        colWidths=[100, 160, 100, 160]
    )

    table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 1, colors.black),

            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),

            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),

            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTNAME", (3, 0), (3, -1), "Helvetica"),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )

    return table
