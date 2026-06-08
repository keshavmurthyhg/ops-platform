import os

from report.module.doc_generator import (
    generate_word_doc_wrapper
)

from common.logger import setup_logger


logger = setup_logger("ppt_to_doc")


# =========================================
# MAIN CONVERTER
# =========================================
def convert_ppt_to_doc(
    ppt_path,
    output_docx,
    incident_data=None
):

    try:

        logger.info(
            f"Starting PPT->DOC conversion: {ppt_path}"
        )

        # =====================================
        # USE EXISTING RCA WORD GENERATOR
        # =====================================

        if incident_data:

            logger.info(
                "Generating RCA + PPT document"
            )

            word_bytes = generate_word_doc_wrapper(
                data=incident_data,
                ppt_data=ppt_path
            )

        else:

            logger.warning(
                "No incident data found. "
                "Generating PPT-only document."
            )

            word_bytes = generate_word_doc_wrapper(
                data={},
                ppt_data=ppt_path
            )

        # =====================================
        # SAVE DOCX
        # =====================================

        with open(output_docx, "wb") as f:

            f.write(word_bytes)

        logger.info(
            f"DOC saved successfully: {output_docx}"
        )

        return output_docx

    except Exception as e:

        logger.error(
            f"PPT conversion failed: {str(e)}"
        )

        raise


# =========================================
# ENTRY FUNCTION
# =========================================
def ppt_to_word(
    ppt_path,
    output_docx,
    incident_data=None
):

    logger.info("ppt_to_word called")

    return convert_ppt_to_doc(
        ppt_path,
        output_docx,
        incident_data
    )