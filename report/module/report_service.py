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
    Load incident data from snow.xlsx
    and normalize for report generator
    """

    snow_file = os.path.join("data", "snow.xlsx")

    if not os.path.exists(snow_file):
        raise Exception("snow.xlsx not found in data folder")

    df = pd.read_excel(snow_file)

    row = df[
        df["Number"].astype(str).str.strip()
        == incident_number
    ]

    if row.empty:
        raise Exception(
            f"{incident_number} not found in snow.xlsx"
        )

    r = row.iloc[0]

    # Extract resolution notes properly
    resolution_notes = str(
        r.get("Resolution notes", "")
    ).strip()

    print("RESOLUTION NOTES:")
    print(resolution_notes)

    data = {
        "number": r.get("Number"),

        "assigned_to": r.get("Assigned to"),

        "created_date": r.get("Created"),
        "resolved_date": r.get("Resolved"),

        "priority": r.get("Priority"),

        "short_description": r.get(
            "Short description"
        ),

        "description": format_description(
            r.get("Description")
        ),

        # IMPORTANT → keep exact key expected by doc_generator
        "resolution notes": resolution_notes,

        "work notes": r.get(
            "Work notes"
        ),

        "additional comments": r.get(
            "Additional comments"
        ),

        "created_by": r.get(
            "Opened by"
        ),

        "opened_by": r.get(
            "Opened by"
        ),

        "ptc_case": r.get(
            "Vendor ticket"
        )
    }

    return data


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