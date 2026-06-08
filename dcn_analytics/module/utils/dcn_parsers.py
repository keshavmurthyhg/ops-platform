import re
import pandas as pd


def parse_created_date(series):
    """
    Convert Created On column into valid datetime.
    """

    cleaned = (
        series.astype(str)
        .str.replace("CEST", "", regex=False)
        .str.replace("CET", "", regex=False)
        .str.strip()
    )

    return pd.to_datetime(
        cleaned,
        errors="coerce"
    )


def clean_dcn_number(series):
    """
    Keep ONLY valid WC DCNs.

    Example:
        128140WC -> 128140

    Ignore:
        TEMP001
        12345AB
        TESTWCX
    """

    cleaned = (
        series.astype(str)
        .str.upper()
        .str.strip()
    )

    # ONLY VALID WC FORMAT
    cleaned = cleaned.where(
        cleaned.str.match(r"^\d+WC$")
    )

    extracted = cleaned.str.extract(
        r"(\d+)"
    )[0]

    return pd.to_numeric(
        extracted,
        errors="coerce"
    )


def prepare_dcn_dataframe(df):
    """
    Standard cleanup for analytics dataframe.
    """

    df = df.copy()

    # -------------------------
    # Created Date
    # -------------------------
    df["Created Date"] = parse_created_date(
        df["Created On"]
    )

    # -------------------------
    # DCN Number
    # -------------------------
    df["DCN_NUM"] = clean_dcn_number(
        df["Number"]
    )

    # -------------------------
    # Remove invalid rows
    # -------------------------
    df = df.dropna(
        subset=[
            "Created Date",
            "DCN_NUM"
        ]
    )

    # -------------------------
    # Convert numeric type
    # -------------------------
    df["DCN_NUM"] = (
        df["DCN_NUM"]
        .astype(int)
    )

    # -------------------------
    # Sort by created date
    # -------------------------
    df = df.sort_values(
        by="DCN_NUM"
    ).reset_index(drop=True)
    return df


def detect_missing_dcns(
    df,
    max_gap=5
):
    """
    Detect skipped DCNs in chronological order.
    """

    missing_rows = []

    for i in range(len(df) - 1):

        current_num = df.iloc[i]["DCN_NUM"]
        next_num = df.iloc[i + 1]["DCN_NUM"]

        current_date = df.iloc[i]["Created Date"]

        gap = next_num - current_num

        # Ignore duplicates / reverse ordering
        if gap <= 1:
            continue

        # Ignore unrealistic jumps
        if gap > max_gap:
            continue

        missing_numbers = []

        for n in range(
            current_num + 1,
            next_num
        ):
            missing_numbers.append(
                f"{n}WC"
            )

        missing_rows.append({
            "Date": current_date.date(),
            "Month": current_date.strftime("%b"),
            "Year": int(current_date.year),
            "Sequence Skipped": len(missing_numbers),
            "Skipped DCN Numbers": ", ".join(missing_numbers)
        })

    return pd.DataFrame(missing_rows)