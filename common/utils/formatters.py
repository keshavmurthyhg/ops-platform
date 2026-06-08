import re
from datetime import datetime
from reportlab.lib import colors


# ---------------- DATE ---------------- #
def format_date(val):
    """
    Handles:
    - None
    - pandas NaT
    - empty strings
    - valid datetime/date strings
    """

    if val is None:
        return "-"

    val_str = str(val).strip()

    if val_str.lower() in ["nat", "nan", "none", ""]:
        return "-"

    try:
        if isinstance(val, str):
            val = datetime.fromisoformat(val)

        return val.strftime("%d-%b-%Y")

    except Exception:
        return "-"

# ---------------- WORD TABLE ---------------- #
def set_cell_bg(cell):
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    shading = parse_xml(
        r'<w:shd {} w:fill="D9D9D9"/>'.format(nsdecls('w'))
    )
    cell._tc.get_or_add_tcPr().append(shading)


# ---------------- SAFE TABLE VALUE ---------------- #
def safe_table(val):
    """
    For header/table display:
    - no 'nan'
    - no long values
    """

    val = safe_text(val, default="")

    return val[:200]  # prevent layout overflow

# ---------------- SAFE PDF TEXT ---------------- #
def safe_pdf_text(val):
    """
    Cleans text for ReportLab:
    - removes nan
    - escapes HTML chars
    - splits long lines (prevents LayoutError)
    """

    val = safe_text(val, default="")

    # Escape problematic characters
    val = val.replace("&", "&amp;")
    val = val.replace("<", "&lt;")
    val = val.replace(">", "&gt;")

    # Prevent long line crash
    MAX_LEN = 800
    safe_lines = []

    for line in val.split("\n"):
        if len(line) > MAX_LEN:
            chunks = [line[i:i+MAX_LEN] for i in range(0, len(line), MAX_LEN)]
            safe_lines.extend(chunks)
        else:
            safe_lines.append(line)

    return "\n".join(safe_lines)


# ---------------- SAFE TEXT ---------------- #
def safe_text(val, default="-"):
    """
    Universal cleaner:
    - Handles None / NaN
    - Removes unsafe values
    - Normalizes output
    """

    if val is None:
        return default

    val = str(val).strip()

    if val.lower() in ["nan", "none", ""]:
        return default

    return val

# ---------------- CLEAN DESCRIPTION ---------------- #
def format_description(text: str) -> str:
    """
    Clean ServiceNow description:
    - remove contact info
    - remove phone numbers
    - remove MS Teams lines
    """

    if not text:
        return ""

    text = str(text)

    # 🔴 Remove entire contact preference block
    text = re.sub(
        r"How does the user want to be contacted in case of queries\?.*?(?:phone number:?.*?|MS Teams.*?|$)",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )
    
    # Remove standalone business phone lines
    text = re.sub(
        r"Business phone number:?.*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # 🔴 Remove MS Teams lines
    text = re.sub(
        r"MS Teams.*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # 🔴 Remove phone numbers
    text = re.sub(
        r"\+?\d[\d\s]{7,}",
        "",
        text
    )

    # 🔴 Normalize spacing
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()
