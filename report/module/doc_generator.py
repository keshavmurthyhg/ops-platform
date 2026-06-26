from datetime import datetime

from report.module.renderers.pdf_renderer import generate_pdf_doc
from report.module.renderers.word_renderer import generate_word_doc
from common.utils.text_cleaner import format_description
from common.utils.parsers import extract_azure_id

from report.module.services.rca_service import build_rca
from report.module.services.references_service import extract_references, format_references_text
from common.logger import setup_logger

logger = setup_logger("doc_generator")

def enrich_data(data):
    safe_data = data.copy()

    azure_value = extract_azure_id(
        str(
            safe_data.get(
                "resolution notes",
                ""
            )
        )
    )

    safe_data["azure_bug"] = (
        azure_value if azure_value else "-"
    )

    ptc_value = (
        safe_data.get("ptc_case")
        or safe_data.get("vendor ticket")
        or safe_data.get("ptc case")
    )

    safe_data["ptc_case"] = ptc_value if ptc_value else "-"

    return safe_data


def prepare_data(data):
    logger.info("Preparing report data")
    safe_data = enrich_data(data)

    safe_data["description"] = format_description(
        safe_data.get("description")
    )

    logger.info("Building RCA")
    rca = build_rca(safe_data)

    safe_data["problem"] = rca.get(
        "problem_statement",
        ""
    )

    safe_data["analysis"] = rca.get(
        "root_cause",
        ""
    )

    safe_data["resolution"] = rca.get(
        "resolution",
        ""
    )

    # Extract references — preserve user-edited list (with environment overrides)
    # if it was already set on the incoming data (e.g. from references_json payload).
    logger.info("Extracting references")
    incoming_refs = safe_data.get("references")
    if incoming_refs:
        # Already set (user may have edited environments) — keep as-is
        refs = incoming_refs
        logger.info("References preserved from incoming data: %d", len(refs))
    else:
        refs = extract_references(safe_data)
        safe_data["references"] = refs
        logger.info("References found: %d", len(refs))
    safe_data["references_text"] = format_references_text(refs)

    return safe_data


def get_download_filename(data, extension):
    incident_number = str(
        data.get("number", "incident_report")
    ).strip()

    current_date = datetime.now().strftime("%d%b%Y")

    return f"{incident_number}_{current_date}.{extension}"


# -----------------------------------
# PDF
# -----------------------------------
def generate_pdf(
    data,
    root=None,
    l2=None,
    res=None,
    images=None
):
    try:
        logger.info("PDF generation started")

        prepared = prepare_data(data)

        final_root = root if root else prepared.get("problem")
        final_l2 = l2 if l2 else prepared.get("analysis")
        final_res = res if res else prepared.get("resolution")

        pdf_buffer = generate_pdf_doc(
            data=prepared,
            root=final_root,
            l2=final_l2,
            res=final_res,
            images=images or {}
        )

        logger.info("PDF generation completed")

        return pdf_buffer

    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}")
        raise


# -----------------------------------
# WORD
# -----------------------------------
def generate_word_doc_wrapper(
    data,
    root=None,
    l2=None,
    res=None,
    images=None,
    ppt_data=None
):
    try:
        logger.info("Word generation started")

        prepared = prepare_data(data)

        final_root = root if root else prepared.get("problem")
        final_l2 = l2 if l2 else prepared.get("analysis")
        final_res = res if res else prepared.get("resolution")

        word_buffer = generate_word_doc(
            data=prepared,
            root=final_root,
            l2=final_l2,
            res=final_res,
            images=images or {},
            ppt_data=ppt_data
        )

        logger.info("Word generation completed")

        return word_buffer

    except Exception as e:
        logger.error(
            f"Word generation failed: {str(e)}"
        )
        raise