import re


def extract_azure_id(text):
    """
    Extract Azure work item ID ONLY from valid Azure DevOps URLs.

    Example:
    https://dev.azure.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/123456
    """

    if not text:
        return ""

    text = str(text)

    match = re.search(
        r"dev\.azure\.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/(\d{6})",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return ""


import pandas as pd


# =========================================
# FORMAT DATE COLUMNS
# =========================================

def format_date_columns(df, columns):

    """
    Convert columns into proper datetime.
    Auto detect formats safely.
    """

    for col in columns:

        if col not in df.columns:
            continue

        df[col] = pd.to_datetime(
            df[col],
            errors="coerce"
        )

    return df


# =========================================
# CLEAN EMPTY VALUES
# =========================================

def clean_empty_values(df):

    """
    Replace NaN / NaT safely.
    """

    return df.fillna("")


# =========================================
# NORMALIZE COLUMN NAMES
# =========================================

def normalize_columns(df):

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    return df


# =========================================
# COMMON SEARCH DATA PREP
# =========================================

def prepare_search_dataframe(df):

    """
    Common dataframe cleanup
    for Search module.
    """

    df = normalize_columns(df)

    df = format_date_columns(

        df,

        [
            "created_date",
            "resolved_date",
            "created",
            "resolved"
        ]
    )

    df = clean_empty_values(df)

    return df

# =========================================
# FORMAT FOR UI DISPLAY
# =========================================

def format_display_date(val):

    """
    UI-safe formatter
    """

    if pd.isna(val):
        return ""

    try:
        return val.strftime("%d-%b-%Y")
    except:
        return ""


# =========================================
# NORMALIZE PRIORITY
# =========================================

def normalize_priority(val):

    """
    Convert:
    Severity 2 - Business Moderately Impacted

    TO:
    Severity 2
    """

    if pd.isna(val):
        return ""

    val = str(val).strip()

    if val.lower().startswith("severity"):

        return val.split("-")[0].strip()

    return val

# =========================================
# SOURCE SAFE DATE PARSER
# =========================================

def parse_mixed_date(val):

    """
    Parse Azure / Snow / PTC dates safely.
    """

    if pd.isna(val):
        return pd.NaT

    val = str(val).strip()

    try:

        # ---------------------------------
        # AZURE
        # 5/12/2026 5:55:44 PM
        # ---------------------------------
        if "/" in val and (
            "AM" in val.upper()
            or
            "PM" in val.upper()
        ):

            return pd.to_datetime(
                val,
                format="%m/%d/%Y %I:%M:%S %p",
                errors="coerce"
            )

        # ---------------------------------
        # SNOW
        # 2026-05-14 14:14:17
        # ---------------------------------
        elif "-" in val and ":" in val:

            return pd.to_datetime(
                val,
                format="%Y-%m-%d %H:%M:%S",
                errors="coerce"
            )

        # ---------------------------------
        # PTC
        # 08-May-26
        # ---------------------------------
        elif "-" in val and len(val.split("-")[-1]) == 2:

            return pd.to_datetime(
                val,
                format="%d-%b-%y",
                errors="coerce"
            )

        # ---------------------------------
        # FALLBACK
        # ---------------------------------
        return pd.to_datetime(
            val,
            errors="coerce"
        )

    except:
        return pd.NaT


# =========================================
# REMOVE EMAIL ADDRESS
# =========================================

def clean_person_name(val):

    if pd.isna(val):
        return ""

    val = str(val).strip()

    if "<" in val:
        val = val.split("<")[0]

    if "(" in val:
        val = val.split("(")[0]

    return val.strip()


# =========================================
# FORMAT TRACKER DATE
# =========================================

def format_tracker_date(val):

    dt = parse_mixed_date(val)

    if pd.isna(dt):
        return ""

    return dt.strftime("%d-%b-%Y")

