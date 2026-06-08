from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def get_pdf_styles():
    styles = getSampleStyleSheet()

    center = ParagraphStyle(
        name="center",
        parent=styles["Normal"],
        alignment=1
    )

    bullet = ParagraphStyle(
        name="bullet",
        parent=styles["Normal"],
        leftIndent=10,
        spaceAfter=4
    )

    return styles, center, bullet
