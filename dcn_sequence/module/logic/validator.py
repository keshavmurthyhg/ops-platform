import os


# =========================================================
# VALIDATE FILE
# =========================================================
def validate_excel_file(file_path):

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            "Uploaded file not found"
        )

    extension = os.path.splitext(
        file_path
    )[1].lower()

    allowed_extensions = [
        ".xlsx",
        ".xls"
    ]

    if extension not in allowed_extensions:

        raise ValueError(
            "Invalid Excel file format"
        )

    return True


# =========================================================
# VALIDATE REQUIRED COLUMNS
# =========================================================
def validate_required_columns(df):

    required_columns = [
        "Number"
    ]

    missing_columns = []

    for column in required_columns:

        if column not in df.columns:

            missing_columns.append(column)

    if missing_columns:

        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    return True