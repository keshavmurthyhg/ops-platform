# =====================================================
#  AZURE DEVOPS BUG LOADER
# =====================================================
#  Supports two modes, controlled by config.py:
#
#    USE_AZURE_API = False → reads data/Azure.csv
#    USE_AZURE_API = True  → calls Azure DevOps REST API
#
#  To enable live API:
#    1. Set USE_AZURE_API = True in modules/config.py
#    2. Set AZURE_ORG, AZURE_PROJECT, AZURE_PAT
#
#  PAT scope needed: Work Items (Read)
# =====================================================

import base64
import requests
import pandas as pd

from common.config import (
    USE_AZURE_API,
    AZURE_ORG,
    AZURE_PROJECT,
    AZURE_PAT,
    AZURE_CSV_PATH,
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
    "new",
    "active",
    "approved",
    "committed",
    "in progress",
    "on hold",
]

# Fields to fetch from Azure DevOps API
AZURE_FIELDS = [
    "System.Id",
    "System.Title",
    "System.AssignedTo",
    "System.State",
    "System.CreatedBy",
    "System.CreatedDate",
    "Microsoft.VSTS.Common.Priority",
    "System.WorkItemType",
]


# ─────────────────────────────────────────────
#  CSV FALLBACK
# ─────────────────────────────────────────────

def _load_from_csv():

    try:

        df = pd.read_csv(AZURE_CSV_PATH)

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.lower()
        )

        for col in ["created by", "assigned to", "state",
                    "release_windchill", "created date", "id", "title"]:
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].fillna("").astype(str)

        # Filter by created-by user
        df = df[
            df["created by"]
            .str.lower()
            .apply(
                lambda x: any(u in x for u in TRACKER_USERS)
            )
        ]

        # Filter active states
        df = df[
            df["state"]
            .str.strip()
            .str.lower()
            .isin(ACTIVE_STATES)
        ]

        azure_df = pd.DataFrame({
            "Number":      df.get("id", ""),
            "Vendor Ticket": "",
            "Description": df.get("title", ""),
            "Assigned To": df.get("assigned to", "").apply(clean_person_name),
            "Status":      df.get("state", ""),
            "Priority":    df.get("release_windchill", "").fillna(""),
            "Created By":  df.get("created by", "").apply(clean_person_name),
            "Created Date":df.get("created date", "").apply(format_tracker_date),
        })

        azure_df = azure_df.fillna("")

        print(f"[AZURE] CSV → {len(azure_df)} active bugs")
        return azure_df.to_dict(orient="records")

    except Exception as e:

        print(f"[AZURE] CSV load failed: {e}")
        return []


# ─────────────────────────────────────────────
#  LIVE API  (USE_AZURE_API = True)
# ─────────────────────────────────────────────

def _get_auth_header():
    """Build Basic-auth header from PAT."""
    token = base64.b64encode(
        f":{AZURE_PAT}".encode("ascii")
    ).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json",
    }


def _run_wiql_query(headers):
    """
    Run WIQL query to get IDs of active bugs
    created by tracker users.
    """

    # Build user IN clause
    user_list = ", ".join(
        f"'{u}'" for u in TRACKER_USERS
    )

    # WIQL does substring match with Contains
    user_conditions = " OR ".join(
        f"[System.CreatedBy] Contains '{u}'"
        for u in TRACKER_USERS
    )

    state_list = ", ".join(
        f"'{s.title()}'" for s in ACTIVE_STATES
    )

    wiql = {
        "query": f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE
                [System.TeamProject] = '{AZURE_PROJECT}'
                AND [System.WorkItemType] = 'Bug'
                AND [System.State] IN ({state_list})
                AND ({user_conditions})
            ORDER BY [System.CreatedDate] DESC
        """
    }

    url = (
        f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}"
        f"/_apis/wit/wiql?api-version=7.1"
    )

    resp = requests.post(url, json=wiql, headers=headers, timeout=15)
    resp.raise_for_status()

    items = resp.json().get("workItems", [])
    return [str(i["id"]) for i in items]


def _get_work_item_details(ids, headers):
    """
    Batch-fetch full details for a list of work item IDs.
    Azure allows up to 200 per request.
    """

    all_rows = []
    batch_size = 200

    fields_param = ",".join(AZURE_FIELDS)

    for i in range(0, len(ids), batch_size):

        batch = ids[i: i + batch_size]
        ids_param = ",".join(batch)

        url = (
            f"https://dev.azure.com/{AZURE_ORG}/{AZURE_PROJECT}"
            f"/_apis/wit/workitems?ids={ids_param}"
            f"&fields={fields_param}&api-version=7.1"
        )

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        all_rows.extend(resp.json().get("value", []))

    return all_rows


def _load_from_api():
    """
    Calls Azure DevOps WIQL + Work Items API.

    Step 1: WIQL query → get matching IDs
    Step 2: Batch fetch full item details
    Step 3: Normalize to standard row format
    """

    headers = _get_auth_header()

    try:
        ids = _run_wiql_query(headers)
    except Exception as e:
        print(f"[AZURE] WIQL query failed: {e}")
        print("[AZURE] Falling back to CSV")
        return _load_from_csv()

    if not ids:
        print("[AZURE] API → 0 bugs found")
        return []

    try:
        items = _get_work_item_details(ids, headers)
    except Exception as e:
        print(f"[AZURE] Work item detail fetch failed: {e}")
        print("[AZURE] Falling back to CSV")
        return _load_from_csv()

    rows = []

    for item in items:

        f = item.get("fields", {})

        created_by_raw = f.get("System.CreatedBy", {})
        assigned_to_raw = f.get("System.AssignedTo", {})

        created_by = (
            created_by_raw.get("displayName", "")
            if isinstance(created_by_raw, dict)
            else str(created_by_raw)
        )

        assigned_to = (
            assigned_to_raw.get("displayName", "")
            if isinstance(assigned_to_raw, dict)
            else str(assigned_to_raw)
        )

        rows.append({
            "Number":
                str(f.get("System.Id", "")),
            "Vendor Ticket": "",
            "Description":
                str(f.get("System.Title", "")),
            "Assigned To":
                clean_person_name(assigned_to),
            "Status":
                str(f.get("System.State", "")),
            "Priority":
                str(f.get("Microsoft.VSTS.Common.Priority", "")),
            "Created By":
                clean_person_name(created_by),
            "Created Date":
                format_tracker_date(
                    str(f.get("System.CreatedDate", ""))
                ),
        })

    print(f"[AZURE] API → {len(rows)} active bugs")
    return rows


# ─────────────────────────────────────────────
#  PUBLIC ENTRY POINT
# ─────────────────────────────────────────────

def load_azure_tracker():

    if USE_AZURE_API:
        print("[AZURE] Mode: LIVE API")
        return _load_from_api()
    else:
        print("[AZURE] Mode: CSV file (API disabled)")
        return _load_from_csv()
