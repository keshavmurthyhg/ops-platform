import pandas as pd
import os

# ==========================================
# CONFIG
# ==========================================

FILE_PATH = "data/user_group_mapping.csv"

DEFAULT_GROUP = "UNASSIGNED"


# ==========================================
# LOAD EXISTING GROUP FILE
# ==========================================

def load_group_mapping():

    if os.path.exists(FILE_PATH):

        mapping = pd.read_csv(FILE_PATH)

    else:

        mapping = pd.DataFrame(
            columns=["Name", "Group"]
        )

    if "Group" not in mapping.columns:

        mapping["Group"] = DEFAULT_GROUP

    mapping = mapping[["Name", "Group"]]

    mapping["Name"] = (
        mapping["Name"]
        .astype(str)
        .str.strip()
    )

    mapping["Group"] = (
        mapping["Group"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return mapping


# ==========================================
# SAVE GROUP FILE
# ==========================================

def save_group_mapping(mapping_df):

    existing = pd.DataFrame()

    if os.path.exists(FILE_PATH):

        existing = pd.read_csv(FILE_PATH)

    # preserve extra columns
    for col in existing.columns:

        if col not in mapping_df.columns:

            mapping_df[col] = existing[col]

    mapping_df.to_csv(
        FILE_PATH,
        index=False
    )


# ==========================================
# EXTRACT USERS FROM DATAFRAME
# ==========================================

def extract_users_from_dataframe(df):

    users = pd.concat([
        df["Assigned To"],
        df["Created By"]
    ]).dropna().astype(str).unique()

    return sorted(users)


# ==========================================
# BUILD GROUP MAPPING
# ==========================================

def build_group_mapping(df):

    users = extract_users_from_dataframe(df)

    users_df = pd.DataFrame({
        "Name": users
    })

    mapping_df = load_group_mapping()

    merged = users_df.merge(
        mapping_df,
        on="Name",
        how="left"
    )

    merged["Group"] = merged["Group"].fillna(
        DEFAULT_GROUP
    )

    return merged


# ==========================================
# GET UNIQUE GROUPS
# ==========================================

def get_available_groups(mapping_df):

    return sorted(
        mapping_df["Group"]
        .dropna()
        .unique()
        .tolist()
    )


# ==========================================
# FILTER DATAFRAME BY GROUP
# ==========================================

def filter_dataframe_by_group(
    df,
    mapping_df,
    selected_groups
):

    if not selected_groups:

        return df

    selected_groups = [
        str(g).strip().upper()
        for g in selected_groups
    ]

    allowed_users = mapping_df[
        mapping_df["Group"].isin(
            selected_groups
        )
    ]["Name"].tolist()

    filtered_df = df[
        (
            df["Assigned To"].isin(
                allowed_users
            )
        )
        |
        (
            df["Created By"].isin(
                allowed_users
            )
        )
    ]

    return filtered_df

# ==========================================
# SAVE USER GROUP
# ==========================================

def save_user_group(group_name, users):

    mapping = load_group_mapping()

    group_name = str(group_name).strip().upper()

    for user in users:

        user = str(user).strip()

        existing = mapping["Name"] == user

        if existing.any():

            mapping.loc[
                existing,
                "Group"
            ] = group_name

        else:

            mapping.loc[len(mapping)] = {
                "Name": user,
                "Group": group_name
            }

    save_group_mapping(mapping)