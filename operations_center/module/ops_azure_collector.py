import requests
import base64
from dotenv import load_dotenv
import os
from datetime import datetime
from common.utils.parsers import clean_person_name, format_tracker_date
from common.config import USE_AZURE_API, AZURE_ORG, AZURE_PROJECT, AZURE_PAT, AZURE_CSV_PATH, TRACKER_USERS
from windchill_monitoring.module.data_logger import append_to_historical_log

ORGANIZATION = AZURE_ORG
PROJECT = AZURE_PROJECT

token = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
headers = {"Content-Type": "application/json", "Authorization": f"Basic {token}"}

azure_cases = []

try:
    query = {
        "query": """
        SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo],
               [Microsoft.VSTS.Common.Priority], [System.CreatedBy], [System.CreatedDate]
        FROM WorkItems
        WHERE [System.TeamProject] = 'VCEWindchillPLM'
          AND [System.WorkItemType] = 'Bug'
          AND [System.State] <> 'Closed'
        ORDER BY [System.CreatedDate] DESC
        """
    }

    wiql_url = f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/wit/wiql?api-version=7.1"
    response = requests.post(wiql_url, headers=headers, json=query)

    if response.status_code == 200:
        data = response.json()
        work_items = data.get("workItems", [])
        ids = [str(item["id"]) for item in work_items][:500]

        BATCH_SIZE = 200
        for i in range(0, len(ids), BATCH_SIZE):
            batch_ids = ids[i:i + BATCH_SIZE]
            details_url = f"https://dev.azure.com/{ORGANIZATION}/_apis/wit/workitems?ids=" + ",".join(batch_ids) + "&api-version=7.1"
            details_response = requests.get(details_url, headers=headers)

            if details_response.status_code != 200:
                continue

            details_data = details_response.json()
            for item in details_data.get("value", []):
                fields = item.get("fields", {})
                assigned_to = fields.get("System.AssignedTo", {})
                created_by = fields.get("System.CreatedBy", {})
                raw_created_date = fields.get("System.CreatedDate", "").split("T")[0]
                formatted_created_date = datetime.strptime(raw_created_date, "%Y-%m-%d").strftime("%d-%b-%Y")

                created_by_name = clean_person_name(
                    created_by.get("displayName", "") if isinstance(created_by, dict) else str(created_by)
                )
                # Filter: only include work items created by tracked users
                if TRACKER_USERS and not any(
                    u.lower() in created_by_name.lower() for u in TRACKER_USERS
                ):
                    continue

                azure_cases.append({
                    "Number": item.get("id", ""),
                    "Description": fields.get("System.Title", ""),
                    "Assigned To": clean_person_name(assigned_to.get("displayName", "") if isinstance(assigned_to, dict) else str(assigned_to)),
                    "Status": fields.get("System.State", ""),
                    "Priority": fields.get("Microsoft.VSTS.Common.Priority", ""),
                    "Created By": created_by_name,
                    "Created Date": formatted_created_date,
                    "raw_created_date": raw_created_date,
                    "item_type": "Bug",
                    "number_url": f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_workitems/edit/{item.get('id')}"
                })

    # Record historical tracking files for reporting
    if azure_cases:
        append_to_historical_log("azure_cases", azure_cases)

except Exception as e:
    print("Azure Collector Error:", str(e))