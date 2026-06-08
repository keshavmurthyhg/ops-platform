# =====================================================
#  PTC CASE TRACKER LOADER
# =====================================================
#  Supports two modes, controlled by config.py:
#
#    USE_PTC_API = False → reads data/PTC.csv
#    USE_PTC_API = True  → calls PTC REST API
#
#  To enable live API (when corporate access is granted):
#    1. Set USE_PTC_API = True in modules/config.py
#    2. Fill in PTC_BASE_URL, PTC_USERNAME, PTC_PASSWORD
#
#  NOTE: PTC Support portal REST API may require
#  a service account — check with your PTC admin.
# =====================================================

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

from common.config import (
    USE_PTC_API,
    PTC_BASE_URL,
    PTC_USERNAME,
    PTC_PASSWORD,
    PTC_CSV_PATH,
    TRACKER_USERS,
)

from common.utils.parsers import (
    clean_person_name,
    format_tracker_date,
    normalize_priority,
)

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

ACTIVE_STATES = [
    "new",
    "active",
    "approved",
    "committed",
    "in progress",
    "on hold",
    "information received",
    "spr filed",
]


# ─────────────────────────────────────────────
#  CSV FALLBACK  (current working mode)
# ─────────────────────────────────────────────

def _load_from_csv():

    try:

        df = pd.read_csv(
            PTC_CSV_PATH,
            encoding="utf-8-sig",
            index_col=False,
            low_memory=False,
        )

        # Normalize columns
        df.columns = (
            df.columns
            .astype(str)
            .str.replace("\ufeff", "", regex=False)
            .str.replace("ï»¿",  "", regex=False)
            .str.strip()
            .str.lower()
        )

        required_columns = [
            "case number",
            "subject",
            "case assignee",
            "case contact",
            "status",
            "severity",
            "created date",
        ]

        for col in required_columns:
            if col not in df.columns:
                df[col] = ""
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        # Filter tracker users
        df = df[
            df["case contact"]
            .str.lower()
            .apply(
                lambda x: any(u in x for u in TRACKER_USERS)
            )
        ]

        # Filter active states
        df = df[
            df["status"]
            .str.lower()
            .str.strip()
            .isin(ACTIVE_STATES)
        ]

        ptc_df = pd.DataFrame({
            "Number":        df["case number"],
            "Vendor Ticket": "",
            "Description":   df["subject"],
            "Assigned To":   df["case assignee"].apply(clean_person_name),
            "Status":        df["status"],
            "Priority":      df["severity"].apply(normalize_priority),
            "Created By":    df["case contact"].apply(clean_person_name),
            "Created Date":  df["created date"].apply(format_tracker_date),
        })

        ptc_df = ptc_df.fillna("")

        print(f"[PTC] CSV → {len(ptc_df)} active cases")
        return ptc_df.to_dict(orient="records")

    except Exception as e:

        print(f"[PTC] CSV load failed: {e}")
        return []


# ─────────────────────────────────────────────
#  LIVE API  (USE_PTC_API = True)
# ─────────────────────────────────────────────

def _load_from_api():
    """
    Calls PTC Support REST API.

    PTC uses a case management REST endpoint.
    The exact path depends on your PTC portal version.

    Common endpoints:
      - Windchill RV&S:  /api/v1/cases
      - PTC Support:     /appserver/cs/api/cases

    Adjust the URL below to match your environment.
    Your PTC admin can confirm the correct endpoint.
    """

    # ── Attempt PTC REST API ──────────────────
    # Build user filter for case_contact field
    user_filter = " OR ".join(
        f'case_contact contains "{u}"'
        for u in TRACKER_USERS
    )

    state_filter = " OR ".join(
        f'status="{s}"' for s in ACTIVE_STATES
    )

    params = {
        "filter": f"({state_filter}) AND ({user_filter})",
        "limit":  500,
        "fields": "case_number,subject,case_assignee,"
                  "case_contact,status,severity,created_date",
    }

    url = f"{PTC_BASE_URL}/appserver/cs/api/cases"

    try:

        resp = requests.get(
            url,
            params=params,
            auth=HTTPBasicAuth(PTC_USERNAME, PTC_PASSWORD),
            timeout=15,
        )

        resp.raise_for_status()
        records = resp.json().get("cases", [])

    except Exception as e:

        print(f"[PTC] API call failed: {e}")
        print("[PTC] Falling back to CSV file")
        return _load_from_csv()

    rows = []

    for r in records:

        rows.append({
            "Number":
                str(r.get("case_number", "")),
            "Vendor Ticket": "",
            "Description":
                str(r.get("subject", "")),
            "Assigned To":
                clean_person_name(
                    str(r.get("case_assignee", ""))
                ),
            "Status":
                str(r.get("status", "")),
            "Priority":
                normalize_priority(
                    str(r.get("severity", ""))
                ),
            "Created By":
                clean_person_name(
                    str(r.get("case_contact", ""))
                ),
            "Created Date":
                format_tracker_date(
                    str(r.get("created_date", ""))
                ),
        })

    print(f"[PTC] API → {len(rows)} active cases")
    return rows


# ─────────────────────────────────────────────
#  PUBLIC ENTRY POINT
# ─────────────────────────────────────────────

def load_ptc_tracker():

    if USE_PTC_API:
        print("[PTC] Mode: LIVE API")
        return _load_from_api()
    else:
        print("[PTC] Mode: CSV file (API disabled)")
        return _load_from_csv()
