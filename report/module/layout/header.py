from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors

from common.utils.links import get_url, make_pdf_link


def build_pdf_header(data, wrap_link, format_date):

    def wrap(x):
        return Paragraph(str(x or "-"), style=None)

    def safe_link(field, value):
            """
            Keep links clickable while preventing blank values.
            """
        
            if not value:
                return wrap("-")
        
            value = str(value).strip()
        
            if value.lower() in ["nan", "none", "nat", "-"]:
                return wrap("-")
        
            try:
                url = get_url(field, value)
        
                # If valid URL exists → clickable link
                if url:
                    return wrap_link(field, value)
        
                # fallback → plain text
                return wrap(value)
        
            except Exception as e:
                print(f"{field} link error:", e)
                return wrap(value)
                
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
                safe_link("ptc case", data.get("ptc_case")),
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
