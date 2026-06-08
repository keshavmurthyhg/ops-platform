from datetime import datetime
import re
from io import BytesIO

# ---------------- COMMON ---------------- #

def clean_text(text):
    """
    Cleans text for safe Word/PDF rendering.
    - Removes invalid XML characters (critical for python-docx)
    - Removes unwanted privacy lines
    """
    if not text:
        return ""

    text = str(text)

    # ✅ Remove invalid XML characters
    text = "".join(
        ch for ch in text
        if ord(ch) in (9, 10, 13) or 32 <= ord(ch) <= 126 or ord(ch) > 127
    )

    # ✅ Remove privacy line (your logic)
    text = re.sub(
        r"How does the user want to be contacted.*?\?",
        "",
        text,
        flags=re.I
    )

    return text.strip()


def clean_nan(val):
    if val is None:
        return ""
    if str(val).lower() == "nan":
        return ""
    return str(val)


def format_date(date_str):
    if not date_str:
        return ""
    try:
        return datetime.strptime(str(date_str).split()[0], "%Y-%m-%d").strftime("%d-%b-%Y")
    except:
        return str(date_str)


def format_description(text):
    if not text:
        return ""

    text = str(text)

    # Remove everything after privacy question
    text = re.split(
        r"How does the user want to be contacted.*?\?",
        text,
        flags=re.I
    )[0]

    return clean_text(text)


def make_link(url, text):
    if not text:
        return ""
    return f'<link href="{url}">{text}</link>'


#============ AZURE NUMBER EXTRACTOR ============== #

def extract_azure_id(text):
    if not text:
        return None

    text = str(text)

    # Match Azure DevOps URL
    match = re.search(r'_workitems/edit/(\d+)', text)
    if match:
        return match.group(1)

    # Backup match (numbers)
    match = re.search(r'/(\d{5,})', text)
    if match:
        return match.group(1)

    return None


# ---------------- PDF ---------------- #

from reportlab.platypus import Image, Spacer

def add_images_pdf(elements, image_list):
    if not image_list:
        return

    for img in image_list:
        try:
            if hasattr(img, "read"):
                img_bytes = BytesIO(img.read())
                img.seek(0)
            else:
                img_bytes = img

            elements.append(Image(img_bytes, width=350, height=200))
            elements.append(Spacer(1, 10))
        except:
            pass


# ---------------- WORD ---------------- #

from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from docx.shared import Inches
from io import BytesIO

def add_images_word(doc, image_list):
    if not image_list:
        return

    for img in image_list:
        try:
            doc.add_paragraph("")  # ✅ spacing BEFORE

            if hasattr(img, "read"):
                img_bytes = BytesIO(img.read())
                img.seek(0)
            else:
                img_bytes = img

            doc.add_picture(img_bytes, width=Inches(5.5))

            doc.add_paragraph("")  # ✅ spacing AFTER

        except Exception:
            pass

def add_hyperlink(paragraph, url, text):
    if not text:
        paragraph.text = ""
        return

    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    run = OxmlElement("w:r")
    text_elem = OxmlElement("w:t")
    text_elem.text = clean_text(text)

    run.append(text_elem)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def set_cell_bg(cell):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "D9D9D9")
    tcPr.append(shd)
