"""
ops_user_stories_collector.py
===============================
Fetches Azure DevOps User Stories. Tries:
  1. Live Azure DevOps API (saved query 4614b947-0182-40f7-8681-2ace961e42e5)
  2. Inline WIQL if saved query fails
  3. CSV fallback: data/AOM_user_stories.csv   ← works when PAT expires Dec-2026

Only includes stories created by TRACKER_USERS.
"""

import os
import csv
import base64
import requests
from datetime import datetime
from pathlib import Path

from common.config import (
    USE_AZURE_API, AZURE_PAT, TRACKER_USERS
)
from common.utils.parsers import clean_person_name, format_tracker_date

US_ORG      = "VolvoGroup-DVP"
US_PROJECT  = "VPA"
US_QUERY_ID = "4614b947-0182-40f7-8681-2ace961e42e5"
US_CSV_PATH = Path("data") / "AOM_user_stories.csv"

user_stories = []


def _load_from_csv():
    """Load user stories from data/AOM_user_stories.csv (PAT-expired fallback)."""
    rows = []
    if not US_CSV_PATH.exists():
        print(f"[UserStories] CSV not found: {US_CSV_PATH}")
        return rows
    try:
        with open(US_CSV_PATH, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                # Normalise column names (lowercase, strip)
                r_norm = {k.strip().lower(): (v or "").strip() for k, v in r.items()}
                cb_name = clean_person_name(
                    r_norm.get("created by", "") or r_norm.get("createdby", "")
                )
                # Apply user filter
                if TRACKER_USERS and not any(
                    u.lower() in cb_name.lower() for u in TRACKER_USERS
                ):
                    continue
                item_id = r_norm.get("id", "") or r_norm.get("number", "")
                rows.append({
                    "Number"      : item_id,
                    "Description" : r_norm.get("title", "") or r_norm.get("description",""),
                    "Assigned To" : clean_person_name(r_norm.get("assigned to","") or r_norm.get("assignedto","")),
                    "Status"      : r_norm.get("state","") or r_norm.get("status",""),
                    "Priority"    : r_norm.get("priority",""),
                    "Created By"  : cb_name,
                    "Created Date": format_tracker_date(r_norm.get("created date","") or r_norm.get("createddate","")),
                    "raw_created_date": r_norm.get("created date","") or r_norm.get("createddate",""),
                    "item_type"   : "User Story",
                    "number_url"  : (
                        f"https://dev.azure.com/{US_ORG}/{US_PROJECT}/_workitems/edit/{item_id}"
                        if item_id else ""
                    ),
                })
        print(f"[UserStories] CSV → {len(rows)} user stories")
    except Exception as e:
        print(f"[UserStories] CSV load failed: {e}")
    return rows


def _load_from_api():
    """Load user stories from Azure DevOps API."""
    if not AZURE_PAT:
        raise Exception("AZURE_PAT not set")

    token   = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
    headers = {"Content-Type": "application/json", "Authorization": f"Basic {token}"}

    # Try saved query first
    ids = []
    query_url = f"https://dev.azure.com/{US_ORG}/{US_PROJECT}/_apis/wit/wiql/{US_QUERY_ID}?api-version=7.1"
    resp = requests.get(query_url, headers=headers, timeout=20)
    if resp.status_code == 200:
        ids = [str(i["id"]) for i in resp.json().get("workItems", [])][:500]
    else:
        # Inline WIQL fallback
        wiql_url  = f"https://dev.azure.com/{US_ORG}/{US_PROJECT}/_apis/wit/wiql?api-version=7.1"
        wiql_body = {"query": """
            SELECT [System.Id],[System.Title],[System.State],[System.AssignedTo],
                   [Microsoft.VSTS.Common.Priority],[System.CreatedBy],[System.CreatedDate]
            FROM WorkItems
            WHERE [System.TeamProject]='VPA'
              AND [System.WorkItemType]='User Story'
              AND [System.State] NOT IN ('Closed','Removed')
            ORDER BY [System.CreatedDate] DESC"""}
        r2 = requests.post(wiql_url, headers=headers, json=wiql_body, timeout=20)
        if r2.status_code != 200:
            raise Exception(f"WIQL query failed: {r2.status_code}")
        ids = [str(i["id"]) for i in r2.json().get("workItems", [])][:500]

    rows = []
    for i in range(0, len(ids), 200):
        batch = ids[i:i+200]
        url   = f"https://dev.azure.com/{US_ORG}/_apis/wit/workitems?ids={','.join(batch)}&api-version=7.1"
        det   = requests.get(url, headers=headers, timeout=20)
        if det.status_code != 200:
            continue
        for item in det.json().get("value", []):
            f        = item.get("fields", {})
            cb_raw   = f.get("System.CreatedBy",  {})
            at_raw   = f.get("System.AssignedTo", {})
            cb_name  = clean_person_name(cb_raw.get("displayName","") if isinstance(cb_raw,dict) else str(cb_raw))
            at_name  = clean_person_name(at_raw.get("displayName","") if isinstance(at_raw,dict) else str(at_raw))
            if TRACKER_USERS and not any(u.lower() in cb_name.lower() for u in TRACKER_USERS):
                continue
            raw_date = f.get("System.CreatedDate","").split("T")[0]
            try:
                fmt_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d-%b-%Y")
            except Exception:
                fmt_date = raw_date
            item_id = item.get("id","")
            rows.append({
                "Number"          : item_id,
                "Description"     : f.get("System.Title",""),
                "Assigned To"     : at_name,
                "Status"          : f.get("System.State",""),
                "Priority"        : f.get("Microsoft.VSTS.Common.Priority",""),
                "Created By"      : cb_name,
                "Created Date"    : fmt_date,
                "raw_created_date": raw_date,
                "item_type"       : "User Story",
                "number_url"      : f"https://dev.azure.com/{US_ORG}/{US_PROJECT}/_workitems/edit/{item_id}",
            })
    return rows


# ── Main load ─────────────────────────────────────────────────────────────────
try:
    if USE_AZURE_API and AZURE_PAT:
        try:
            user_stories = _load_from_api()
            print(f"[UserStories] API → {len(user_stories)} user stories")
        except Exception as api_err:
            print(f"[UserStories] API failed ({api_err}), falling back to CSV")
            user_stories = _load_from_csv()
    else:
        user_stories = _load_from_csv()

except Exception as e:
    print(f"[UserStories] Collector error: {e}")
    user_stories = []
