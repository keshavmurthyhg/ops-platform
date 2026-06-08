from report.module.report_service import load_incident_data
from report.module.doc_generator import prepare_data
from common.logger import setup_logger

logger = setup_logger("preview_service")


def get_preview_data(incident_number):
    """
    Returns fully prepared data including RCA
    for UI preview/edit
    """

    try:
        logger.info(
            f"Preview requested for incident: {incident_number}"
        )

        raw_data = load_incident_data(
            incident_number
        )

        logger.info(
            "Incident data loaded successfully"
        )

        prepared = prepare_data(
            raw_data
        )

        logger.info(
            "Preview data prepared successfully"
        )

        return prepared

    except Exception as e:
        logger.error(
            f"Preview failed for {incident_number}: {str(e)}"
        )
        raise