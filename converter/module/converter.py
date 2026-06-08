import os
from converter.module.ppt_to_doc import ppt_to_word
from common.logger import setup_logger

logger = setup_logger("converter")


def convert_ppt(
    ppt_path,
    output_folder,
    incident_data=None
):
    """
    Only converts PPT -> DOCX
    Keep PDF generation separate
    """

    try:
        logger.info(f"Conversion started for file: {ppt_path}")

        base = os.path.splitext(
            os.path.basename(ppt_path)
        )[0]

        docx_path = os.path.join(
            output_folder,
            f"{base}.docx"
        )

        logger.info(f"Output path created: {docx_path}")

        logger.info("Calling ppt_to_word()")
        ppt_to_word(
            ppt_path,
            docx_path,
            incident_data
        )

        logger.info(f"DOCX created successfully: {docx_path}")

        return docx_path

    except Exception as e:
        logger.error(f"Converter failed: {str(e)}")
        raise