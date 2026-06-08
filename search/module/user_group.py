import pandas as pd
import os

FILE_PATH = "data/user_group_mapping.csv"
DEFAULT_GROUP = "UNASSIGNED"


def load_or_create_mapping(df):

    # ---------- Extract unique users ----------
    users = pd.concat([
        df["Assigned To"],
        df["Created By"]
    ]).dropna().astype(str).unique()

    users_df = pd.DataFrame({"Name": sorted(users)})

    # ---------- Load existing mapping ----------
    if os.path.exists(FILE_PATH):
        mapping = pd.read_csv(FILE_PATH)
    else:
        mapping = pd.DataFrame(columns=["Name", "Group"])

    # ---------- Ensure correct structure ----------
    if "Group" not in mapping.columns:
        mapping["Group"] = DEFAULT_GROUP

    mapping = mapping[["Name", "Group"]]

    # ---------- Normalize ----------
    mapping["Group"] = mapping["Group"].astype(str).str.strip().str.upper()

    # ---------- Merge (SAFE) ----------
    merged = users_df.merge(mapping, on="Name", how="left")

    # ---------- Fill missing ----------
    merged["Group"] = merged["Group"].fillna(DEFAULT_GROUP)

    return merged


def save_mapping(df):
    df.to_csv(FILE_PATH, index=False)
