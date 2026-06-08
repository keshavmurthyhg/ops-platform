import logging
import pandas as pd

from common.logger import setup_logger

logger = setup_logger("bulk")

# IMPORTANT:
# use existing working generator
from bulk.module.bulk_generator import (
    build_bulk_reports,
    generate_bulk_zip
)

# --- logger = logging.getLogger(__name__)


# ------------------------------
# LOAD SNOW DATA
# ------------------------------
def load_snow_data():
    try:
        df = pd.read_excel("data/snow.xlsx")

        df.columns = [
            str(col).strip().lower()
            for col in df.columns
        ]

        logger.info(f"Loaded {len(df)} records")
        logger.info(f"Columns: {df.columns.tolist()}")

        return df

    except Exception as e:
        logger.exception("snow.xlsx load failed")
        raise e


# ------------------------------
# FILTER INCIDENTS
# ------------------------------
def filter_incidents(
    priority=None,
    year=None,
    from_date=None,
    to_date=None
):
    try:
        logger.info("Bulk filter started")
        logger.info(
            f"Inputs → priority={priority}, "
            f"year={year}, "
            f"from={from_date}, "
            f"to={to_date}"
        )

        df = load_snow_data()

        # Priority filter
        if priority and priority != "All Priorities":
            df = df[df["priority"] == priority]
            logger.info(
                f"After priority filter: {len(df)} records"
            )

        # Year filter
        if year and year != "Select":
            df = df[
                pd.to_datetime(df["created"]).dt.year
                == int(year)
            ]
            logger.info(
                f"After year filter: {len(df)} records"
            )

        # From date filter
        if from_date:
            df = df[
                pd.to_datetime(df["created"])
                >= pd.to_datetime(from_date)
            ]
            logger.info(
                f"After from_date filter: {len(df)} records"
            )

        # To date filter
        if to_date:
            df = df[
                pd.to_datetime(df["created"])
                <= pd.to_datetime(to_date)
            ]
            logger.info(
                f"After to_date filter: {len(df)} records"
            )

        incidents = (
            df["number"]
            .dropna()
            .astype(str)
            .tolist()
        )

        logger.info(
            f"Final incidents fetched: {len(incidents)}"
        )

        return incidents

    except Exception as e:
        logger.exception("Incident filtering failed")
        raise e


# ------------------------------
# GENERATE BULK ZIP
# ------------------------------
def generate_bulk_zip_file(
    incident_numbers,
    output_type="both"
):
    try:
        logger.info(
            f"Bulk generation started for: "
            f"{incident_numbers}"
        )

        df = load_snow_data()

        reports = build_bulk_reports(
            df=df,
            incident_list=incident_numbers
        )

        logger.info(
            f"Reports generated: {len(reports)}"
        )

        zip_buffer = generate_bulk_zip(
            reports,
            output_type
        )

        logger.info(
            "ZIP generated successfully"
        )

        return zip_buffer

    except Exception as e:
        logger.exception(
            "Bulk zip generation failed"
        )
        raise e