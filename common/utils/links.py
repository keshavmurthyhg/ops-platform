import re


# ── Shared PTC case parser ────────────────────────────────────────────────────
def parse_ptc_cases(raw):
    """
    Parse a PTC case field into a list of (display, numeric_id) tuples.

    Handles:
      - single:             "17979095"
      - comma-separated:    "17979095, 17993513, 18004286"
      - alpha-prefixed:     "C1234567"  →  display="C1234567", id="1234567"
      - mixed:              "C1234567, 18007960"

    Returns [] when value is empty / nan / "-".
    """
    if not raw:
        return []
    raw = str(raw).strip()
    if raw.lower() in ("nan", "none", "nat", "-", ""):
        return []
    result = []
    for part in [p.strip() for p in raw.split(",") if p.strip()]:
        digits = re.sub(r"[^0-9]", "", part)
        if digits:
            result.append((part, digits))   # (original display, numeric id)
    return result


def extract_azure_id(text):
    if not text:
        return None

    match = re.search(r'/edit/(\d+)', text)
    if match:
        return match.group(1)

    match = re.search(r'\b\d{6,}\b', text)
    return match.group(0) if match else None


def get_url(field, value):
    """
    Return a URL for a known field type and value.

    field values:
        "incident"         → ServiceNow incident URL
        "azure bug"        → Azure DevOps VCEWindchillPLM work item URL
        "ptc case"         → PTC case support URL
        "azure_vpa"        → Azure DevOps VPA user story URL  (NEW)
        "ptc_article"      → PTC article URL                  (NEW)
    """
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

    # ── NEW: VPA Azure user story (from references_service) ──────────────────
    elif field == "azure_vpa":
        return (
            "https://dev.azure.com/VolvoGroup-DVP/VPA/"
            f"_workitems/edit/{value}"
        )

    # ── NEW: PTC article (from references_service) ───────────────────────────
    elif field == "ptc_article":
        return (
            f"https://www.ptc.com/en/support/article/{value}"
        )

    return None


# ---------------- PDF LINKS ---------------- #
def make_pdf_link(value, url, styles):
    """
    Render a clickable PDF link — black text, no underline.
    Matches the document-wide hyperlink style preference.
    """
    from reportlab.platypus import Paragraph

    if not value or not url:
        return Paragraph("-", styles["Normal"])

    return Paragraph(
        f'<link href="{url}" color="#000000">{value}</link>',
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
