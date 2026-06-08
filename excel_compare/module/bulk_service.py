import os
import zipfile
import shutil

from report.module.report_service import generate_incident_report


def generate_bulk_reports(
    incident_numbers,
    report_type
):
    """
    Generate multiple reports
    and return zip file path
    """

    output_folder = "outputs"
    bulk_folder = os.path.join(
        output_folder,
        "bulk_reports"
    )

    zip_path = os.path.join(
        output_folder,
        "bulk_reports.zip"
    )

    # Clean previous folder
    if os.path.exists(bulk_folder):
        shutil.rmtree(bulk_folder)

    os.makedirs(bulk_folder)

    generated_files = []

    for incident in incident_numbers:

        incident = incident.strip()

        if not incident:
            continue

        try:
            file_path = generate_incident_report(
                incident,
                report_type
            )

            filename = os.path.basename(
                file_path
            )

            new_path = os.path.join(
                bulk_folder,
                filename
            )

            shutil.copy(
                file_path,
                new_path
            )

            generated_files.append(
                new_path
            )

        except Exception as e:
            print(
                f"Failed for {incident}: {e}"
            )

    if not generated_files:
        raise Exception(
            "No reports generated"
        )

    # Create zip
    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zipf:

        for file in generated_files:
            zipf.write(
                file,
                os.path.basename(file)
            )

    return zip_path