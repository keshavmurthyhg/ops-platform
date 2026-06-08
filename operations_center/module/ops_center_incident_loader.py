# =====================================================
#  SERVICENOW INCIDENT LOADER
# =====================================================
#  Supports two modes, controlled by config.py:
#
#    USE_SNOW_API = False  → reads data/Snow.xlsx
#    USE_SNOW_API = True   → calls SNOW REST API
#
#  To enable live API:
#    1. Set USE_SNOW_API = True in modules/config.py
#    2. Fill in SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD
# =====================================================

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

from common.config import (
    USE_SNOW_API,
    SNOW_INSTANCE,
    SNOW_USERNAME,
    SNOW_PASSWORD,
    SNOW_EXCEL_PATH,
    TRACKER_USERS,
)

from common.utils.parsers import (
    clean_person_name,
    format_tracker_date,
)

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

ACTIVE_STATES = [
    "on hold",
    "in progress",
    "open",
    "new",
]

# SNOW numeric state values (API uses numbers)
# 1=New, 2=In Progress, 3=On Hold, 6=Resolved, 7=Closed
SNOW_ACTIVE_STATES = "1,2,3"


# ─────────────────────────────────────────────
#  EXCEL FALLBACK
# ─────────────────────────────────────────────

def _load_from_excel():

    try:

        snow = pd.read_excel(
            SNOW_EXCEL_PATH,
            engine="openpyxl"
        )

    except Exception as e:

        print(f"[SNOW] Excel load failed: {e}")
        return []

    snow.columns = (
        snow.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    def get_col(df, *names):
        for n in names:
            if n in df.columns:
                return df[n]
        return pd.Series([""] * len(df))

    incident_df = pd.DataFrame({

        "Number":
            get_col(snow, "number"),

        "Vendor Ticket":
            get_col(
                snow,
                "vendor ticket",
                "vendor incident",
                "vendor reference",
                "external ticket",
            ),

        "Description":
            get_col(
                snow,
                "short description",
                "description",
            ),

        "Assigned To":
            get_col(snow, "assigned to")
            .apply(clean_person_name),

        "Status":
            get_col(snow, "incident state"),

        "Priority":
            get_col(snow, "priority"),

        "Created By": "",

        "Created Date":
            get_col(
                snow,
                "created",
                "opened",
                "opened at",
                "created date",
                "date",
            ).apply(format_tracker_date),
    })

    incident_df = incident_df.fillna("")

    # Filter active states
    incident_df = incident_df[
        incident_df["Status"]
        .astype(str)
        .str.lower()
        .str.strip()
        .isin(ACTIVE_STATES)
    ]

    # Filter tracker users
    incident_df = incident_df[
        incident_df["Assigned To"]
        .astype(str)
        .str.lower()
        .apply(
            lambda x: any(
                u in x for u in TRACKER_USERS
            )
        )
    ]

    # Sort newest first
    try:
        incident_df["_sort"] = pd.to_datetime(
            incident_df["Created Date"],
            errors="coerce"
        )
        incident_df = incident_df.sort_values(
            "_sort", ascending=False
        )
        incident_df.drop(columns=["_sort"], inplace=True)
    except Exception:
        pass

    print(f"[SNOW] Excel → {len(incident_df)} active incidents")
    return incident_df.to_dict(orient="records")


# ─────────────────────────────────────────────
#  LIVE API  (USE_SNOW_API = True)
# ─────────────────────────────────────────────

def _load_from_api():
    """
    Calls ServiceNow Table API.

    Fetches incidents assigned to tracker users
    that are Open / In Progress / On Hold.

    Requires:
      SNOW_INSTANCE  e.g. "volvoitsm"
      SNOW_USERNAME  your SNOW login
      SNOW_PASSWORD  your SNOW password
    """

    base = f"https://{SNOW_INSTANCE}.service-now.com"

    # Build user filter  e.g. assigned_to.nameLIKEkeshava^ORassigned_to.nameLIKEramesh
    user_filter = "^OR".join(
        f"assigned_to.nameLIKE{u}"
        for u in TRACKER_USERS
    )

    params = {
        "sysparm_query":
            f"state={SNOW_ACTIVE_STATES.replace(',', '^ORstate=')}^{user_filter}",
        "sysparm_fields":
            "number,short_description,assigned_to,state,"
            "priority,vendor_ticket,opened_at",
        "sysparm_limit": 500,
        "sysparm_display_value": "true",
    }

    # Rewrite state filter cleanly
    state_q = "^OR".join(
        f"state={s}" for s in SNOW_ACTIVE_STATES.split(",")
    )
    params["sysparm_query"] = f"({state_q})^({user_filter})"

    try:

        resp = requests.get(
            f"{base}/api/now/table/incident",
            params=params,
            auth=HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD),
            timeout=15,
        )

        resp.raise_for_status()
        records = resp.json().get("result", [])

    except Exception as e:

        print(f"[SNOW] API call failed: {e}")
        print("[SNOW] Falling back to Excel file")
        return _load_from_excel()

    rows = []

    for r in records:

        rows.append({
            "Number":
                str(r.get("number", "")),
            "Vendor Ticket":
                str(r.get("vendor_ticket", "")),
            "Description":
                str(r.get("short_description", "")),
            "Assigned To":
                clean_person_name(
                    r.get("assigned_to", {}).get("display_value", "")
                    if isinstance(r.get("assigned_to"), dict)
                    else str(r.get("assigned_to", ""))
                ),
            "Status":
                str(r.get("state", "")),
            "Priority":
                str(r.get("priority", "")),
            "Created By": "",
            "Created Date":
                format_tracker_date(
                    r.get("opened_at", "")
                ),
        })

    print(f"[SNOW] API → {len(rows)} active incidents")
    return rows


# ─────────────────────────────────────────────
#  PUBLIC ENTRY POINT
# ─────────────────────────────────────────────

def load_incident_tracker():

    if USE_SNOW_API:
        print("[SNOW] Mode: LIVE API")
        return _load_from_api()
    else:
        print("[SNOW] Mode: Excel file (API disabled)")
        return _load_from_excel()
