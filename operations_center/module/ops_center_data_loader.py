import pandas as pd
import os


DATA_FILE = os.path.join(
    "data",
    "operations_tracker.xlsx"
)


def load_support_mails():

    try:

        df = pd.read_excel(
            DATA_FILE,
            sheet_name="Support_Mail"
        )

        return df.fillna("").to_dict(
            orient="records"
        )

    except Exception as e:

        print(
            f"Support Mail Load Error: {e}"
        )

        return []


def load_integration_failures():

    try:

        df = pd.read_excel(
            DATA_FILE,
            sheet_name="Integration_Failure"
        )

        return df.fillna("").to_dict(
            orient="records"
        )

    except Exception as e:

        print(
            f"Integration Failure Load Error: {e}"
        )

        return []


def load_incident_tracker():

    try:

        df = pd.read_excel(
            DATA_FILE,
            sheet_name="Incident_Tracker"
        )

        return (
            df.fillna("")
              .to_dict(orient="records")
        )

    except Exception as e:

        print(
            f"Incident Tracker Load Error: {e}"
        )

        return []