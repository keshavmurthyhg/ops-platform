import pandas as pd


# =========================================================
# CLEAN COLUMN NAMES
# =========================================================
def clean_columns(df):

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    return df


# =========================================================
# REMOVE EMPTY ROWS
# =========================================================
def remove_empty_rows(df):

    df = df.dropna(
        how="all"
    )

    return df


# =========================================================
# PREPARE DATAFRAME
# =========================================================
def prepare_dataframe(df):

    df = clean_columns(df)

    df = remove_empty_rows(df)

    return df