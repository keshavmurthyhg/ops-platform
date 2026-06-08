from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from io import BytesIO

from report.module.layout.header import build_pdf_header
from report.module.layout.description import build_pdf_description
from report.module.layout.body import build_sections
from report.module.layout.styles import get_pdf_styles
from report.module.layout.footer import pdf_footer

from common.utils.links import get_url, make_pdf_link
from common.utils.formatters import format_date, safe_pdf_text, safe_table
from common.utils.image_utils import add_images_pdf


# ================= SAFE HEADER VALUE ================= #
def clean_header_value(val):
    if not val:
        return ""

    val = str(val)

    # Escape problematic characters (CRITICAL)
    val = val.replace("&", "&amp;")
    val = val.replace("<", "&lt;")
    val = val.replace(">", "&gt;")

    # Prevent very long values
    return val[:200]


# ================= MAIN PDF GENERATOR ================= #
def generate_pdf_doc(data, root, l2, res, images):

    styles, center_style, bullet_style = get_pdf_styles()

    buffer = BytesIO()
    elements = []

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=50
    )

    # ================= HEADER ================= #
    elements.append(Paragraph("<b>INCIDENT REPORT</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    try:
        header = build_pdf_header(
            data,
            lambda field, value: make_pdf_link(
                safe_table(
                    "-" if str(value).lower() in ["nan", "none", "nat"] else value
                ),
                get_url(field, value),
                styles
            ),
            format_date
        )
        elements.append(header)

    except Exception as e:
        # 🔴 Fail-safe (never crash PDF)
        elements.append(Paragraph("Header could not be rendered", styles["Normal"]))
        print("Header error:", e)

    elements.append(Spacer(1, 15))

    # ================= DESCRIPTION ================= #
    try:
        desc = build_pdf_description(data, center_style, styles)
        elements.append(desc)
    except Exception as e:
        elements.append(Paragraph("Description error", styles["Normal"]))
        print("Description error:", e)

    elements.append(Spacer(1, 20))

    # ================= SANITIZE BODY ================= #
    root = safe_pdf_text(root)
    l2 = safe_pdf_text(l2)
    res = safe_pdf_text(res)

    # ================= BODY ================= #
    try:
        build_sections(
            elements,
            root,
            l2,
            res,
            styles,
            bullet_style,
            add_images_pdf,
            images
        )
    except Exception as e:
        elements.append(Paragraph("Body content could not be rendered", styles["Normal"]))
        print("Body error:", e)

    # ================= FOOTER ================= #
    footer = pdf_footer(data)
    
    try:
        doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    except Exception as e:
        print("PDF build error:", e)
        raise e  # still raise so you can debug if needed

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
