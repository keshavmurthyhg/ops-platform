import os
import zipfile
import tempfile

from datetime import datetime, timezone, timedelta
from modules.word_compare.comparator import compare_documents


def generate_output_file(
    old_file,
    new_file,
    progress_callback=None
):
    old_file.seek(0)
    new_file.seek(0)

    if progress_callback:
        progress_callback(
            10,
            "Preparing output files..."
        )

    old_base = os.path.splitext(
        old_file.name
    )[0]

    new_base = os.path.splitext(
        new_file.name
    )[0]

    ist_timezone = timezone(
        timedelta(hours=5, minutes=30)
    )

    current_date = datetime.now(
        ist_timezone
    ).strftime("%d%b%Y")

    old_output_name = (
        f"{old_base}"
        f"_Diff-Highlighted_"
        f"{current_date}.docx"
    )

    new_output_name = (
        f"{new_base}"
        f"_Diff-Highlighted_"
        f"{current_date}.docx"
    )

    zip_name = (
        f"Word-Doc_Compared_"
        f"{current_date}.zip"
    )

    if progress_callback:
        progress_callback(
            30,
            "Creating temporary files..."
        )

    with tempfile.TemporaryDirectory() as temp_dir:

        old_output_path = os.path.join(
            temp_dir,
            old_output_name
        )

        new_output_path = os.path.join(
            temp_dir,
            new_output_name
        )

        if progress_callback:
            progress_callback(
                50,
                "Comparing documents..."
            )

        compare_documents(
            old_file,
            new_file,
            old_output_path,
            new_output_path
        )

        zip_path = os.path.join(
            temp_dir,
            zip_name
        )

        if progress_callback:
            progress_callback(
                80,
                "Creating ZIP package..."
            )

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zipf:

            zipf.write(
                old_output_path,
                old_output_name
            )

            zipf.write(
                new_output_path,
                new_output_name
            )

        with open(
            zip_path,
            "rb"
        ) as f:
            file_bytes = f.read()

    if progress_callback:
        progress_callback(
            100,
            "Completed successfully."
        )

    return {
        "file_bytes": file_bytes,
        "file_name": zip_name
    }
