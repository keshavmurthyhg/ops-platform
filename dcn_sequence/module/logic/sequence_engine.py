import re
import pandas as pd


# =========================================================
# EXTRACT NUMERIC DCN VALUES
# =========================================================
def extract_dcn_numbers(df):

    """
    Extract numeric values from Number column.

    Example:
    104121WC -> 104121
    """

    if "Number" not in df.columns:

        raise ValueError(
            "'Number' column not found in Excel"
        )

    series = (
        df["Number"]
        .astype(str)
        .str.strip()
    )

    numeric_values = []

    for value in series:

        match = re.search(
            r"(\d+)",
            value
        )

        if match:

            numeric_values.append(
                int(match.group(1))
            )

    numeric_values = sorted(
        list(set(numeric_values))
    )

    return numeric_values


# =========================================================
# FIND MISSING NUMBERS
# =========================================================
def find_missing_sequences(numbers):

    """
    Find missing sequence values.

    Example:
    [1,2,5] -> [3,4]
    """

    missing = []

    if not numbers:
        return missing

    for current, next_num in zip(
        numbers,
        numbers[1:]
    ):

        if next_num - current > 1:

            for value in range(
                current + 1,
                next_num
            ):

                missing.append(value)

    return missing


# =========================================================
# BUILD OUTPUT DATAFRAME
# =========================================================
def build_missing_dataframe(missing_numbers):

    """
    Create output dataframe.
    """

    rows = []

    for index, number in enumerate(
        missing_numbers,
        start=1
    ):

        rows.append({

            "SL NO": index,

            "Missing DCN Number":
                f"{number}WC",

            "Numeric Value":
                number

        })

    return pd.DataFrame(rows)