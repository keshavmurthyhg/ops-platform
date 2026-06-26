import os
import pandas as pd

from report.module.doc_generator import (
    generate_pdf,
    generate_word_doc_wrapper
)

from common.utils.formatters import (
    format_description
)


from common.logger import setup_logger
logger = setup_logger("rca")


def load_incident_data(incident_number):
    """
    Load incident data from Snow.xlsx
    and normalize for report generator
    """

    snow_file = os.path.join("data", "Snow.xlsx")

    if not os.path.exists(snow_file):
        raise Exception("Snow.xlsx not found in data folder")

    df = pd.read_excel(snow_file)

    # Normalize ALL column headers to lowercase + stripped
    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]

    # Match incident number
    row = df[
        df["number"].astype(str).str.strip() == incident_number.strip()
    ]

    if row.empty:
        raise Exception(f"{incident_number} not found in Snow.xlsx")

    r = row.iloc[0]

    def val(col):
        v = r.get(col, "")
        if v is None:
            return ""
        s = str(v).strip()
        return "" if s.lower() in ("nan", "nat", "none") else s

    return {
        "number":               val("number"),
        "short_description":    val("short description"),
        "description":          format_description(val("description")),
        "priority":             val("priority"),
        "created_by":           val("opened by"),
        "opened_by":            val("opened by"),
        "assigned_to":          val("assigned to"),
        "created_date":         val("created"),
        "resolved_date":        val("resolved"),
        "ptc_case":             val("vendor ticket"),

        # Spaced keys for rca_service.py
        "resolution notes":     val("resolution notes"),
        "work notes":           val("work notes"),
        "additional comments":  val("additional comments"),

        # Underscored aliases
        "resolution_notes":     val("resolution notes"),
        "work_notes":           val("work notes"),
        "additional_comments":  val("additional comments"),
    }


def generate_incident_report(
    incident_number,
    report_type
):
    """
    Main reusable report service
    """

    data = load_incident_data(
        incident_number
    )

    output_folder = "outputs"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if report_type == "pdf":

        pdf_buffer = generate_pdf(data)

        output_path = os.path.join(
            output_folder,
            f"{incident_number}.pdf"
        )

        with open(output_path, "wb") as f:
            f.write(pdf_buffer)

        return output_path

    elif report_type == "word":

        word_buffer = generate_word_doc_wrapper(
            data
        )

        output_path = os.path.join(
            output_folder,
            f"{incident_number}.docx"
        )

        with open(output_path, "wb") as f:
            f.write(word_buffer)

        return output_path

    else:
        raise Exception(
            "Invalid report type"
        )