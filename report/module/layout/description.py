from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors

def build_pdf_description(data, center_style, styles):

    def wrap(x):
        return Paragraph(str(x or ""), styles["Normal"])

    table = Table([
        [
            Paragraph("<b>SHORT DESCRIPTION</b>", center_style),
            Paragraph("<b>DESCRIPTION</b>", center_style)
        ],
        [
            wrap(data.get("short_description")),
            wrap(data.get("description"))
        ]
    ], colWidths=[260,260])

    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    
        # 🔹 HEADER ROW GREY
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
    
        # 🔹 HEADER BOLD
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    
        # 🔹 TEXT ALIGNMENT
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    return table
