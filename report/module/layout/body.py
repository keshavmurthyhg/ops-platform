from reportlab.platypus import Paragraph, Spacer, PageBreak
from common.utils.formatters import safe_pdf_text


def add_section(elements, title, content, section_images,
                styles, bullet_style, add_images_pdf):
    """
    Generic section renderer for:
    - Problem Statement
    - Root Cause
    - Resolution

    Ensures:
    ✔ text renders first
    ✔ all images render after text
    ✔ images don't overwrite next section
    ✔ multiple images supported
    """

    elements.append(
        Paragraph(f"<b>{title}</b>", styles["Heading2"])
    )
    elements.append(Spacer(1, 8))

    # ---------------- TEXT ---------------- #
    content = safe_pdf_text(content)

    if content:
        for line in str(content).split("\n"):
            line = line.strip()

            if not line:
                continue

            elements.append(
                Paragraph(
                    f"• {line}",
                    bullet_style
                )
            )
    else:
        elements.append(
            Paragraph("• N/A", bullet_style)
        )

    elements.append(Spacer(1, 10))

    # ---------------- IMAGES ---------------- #
    if section_images:
        try:
            add_images_pdf(
                elements,
                section_images
            )
        except Exception as e:
            print(f"{title} image render error:", e)

    elements.append(Spacer(1, 20))


def build_sections(
    elements,
    problem_text,
    root_text,
    resolution_text,
    styles,
    bullet_style,
    add_images_pdf,
    images
):
    """
    Build all 3 RCA sections with correct image mapping
    """

    # support both UI keys + legacy keys
    problem_images = (
        images.get("problem", [])
        or images.get("problem_statement", [])
    )

    root_images = (
        images.get("root", [])
        or images.get("root_cause", [])
    )

    resolution_images = images.get(
        "resolution",
        []
    )


    # ---------------- PROBLEM ---------------- #
    add_section(
        elements=elements,
        title="PROBLEM STATEMENT",
        content=problem_text,
        section_images=problem_images,
        styles=styles,
        bullet_style=bullet_style,
        add_images_pdf=add_images_pdf
    )

    # ---------------- ROOT CAUSE ---------------- #
    add_section(
        elements=elements,
        title="ROOT CAUSE",
        content=root_text,
        section_images=root_images,
        styles=styles,
        bullet_style=bullet_style,
        add_images_pdf=add_images_pdf
    )

    # ---------------- RESOLUTION ---------------- #
    add_section(
        elements=elements,
        title="RESOLUTION & RECOMMENDATION",
        content=resolution_text,
        section_images=resolution_images,
        styles=styles,
        bullet_style=bullet_style,
        add_images_pdf=add_images_pdf
    )