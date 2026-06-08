import os


# =========================================================
# MASTER DATA FILE
# =========================================================
DATA_FILE = os.path.join(
    "data",
    "DCN-analytics.xlsx"
)


# =========================================================
# VALIDATE MASTER FILE
# =========================================================
def validate_master_dataset():

    if not os.path.exists(DATA_FILE):

        raise FileNotFoundError(

            "Master dataset not found:\n"
            "data/DCN-analytics.xlsx"

        )

    return DATA_FILE