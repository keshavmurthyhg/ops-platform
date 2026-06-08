import re


def extract_azure_id(text):
    if not text:
        return None

    match = re.search(r'/edit/(\d+)', text)
    if match:
        return match.group(1)

    match = re.search(r'\b\d{6,}\b', text)
    return match.group(0) if match else None


def get_url(field, value):
    if not value or value == "-":
        return None

    value = str(value).strip()
    field = field.lower()

    if field == "incident":
        return (
            "https://volvoitsm.service-now.com/"
            f"nav_to.do?uri=incident.do?sysparm_query=number={value}"
        )

    elif field == "azure bug":
        return (
            "https://dev.azure.com/VolvoGroup-DVP/"
            f"VCEWindchillPLM/_workitems/edit/{value}"
        )

    elif field == "ptc case":
        return (
            "https://support.ptc.com/"
            f"appserver/cs/view/case.jsp?n={value}"
        )

    return None


# ---------------- PDF LINKS ---------------- #
def make_pdf_link(value, url, styles):
    from reportlab.platypus import Paragraph

    if not value or not url:
        return Paragraph("-", styles["Normal"])

    return Paragraph(
        f'<link href="{url}">{value}</link>',
        styles["Normal"]
    )


# ---------------- WORD LINKS ---------------- #
def apply_word_link(paragraph, key, value):
    """
    Creates clickable hyperlinks in Word
    WITHOUT blue color
    WITHOUT underline
    """

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    value = str(value or "-").strip()

    if value in ["-", "", "nan", "None", "NaT"]:
        paragraph.add_run("-")
        return

    url = get_url(key.lower(), value)

    # No valid URL → plain text
    if not url:
        paragraph.add_run(value)
        return

    part = paragraph.part

    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True
    )

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    # -----------------------------
    # BLACK FONT
    # -----------------------------
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "000000")
    rPr.append(color)

    # -----------------------------
    # REMOVE UNDERLINE
    # -----------------------------
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "none")
    rPr.append(underline)

    new_run.append(rPr)

    text_elem = OxmlElement("w:t")
    text_elem.text = value
    new_run.append(text_elem)

    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


# ---------------- UI LINKS ---------------- #
def make_ui_link(type_, value):
    url = get_url(type_, value)

    if not value:
        return "-"

    if not url:
        return str(value)

    return f'<a href="{url}" target="_blank">{value}</a>'
