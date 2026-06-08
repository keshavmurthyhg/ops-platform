import requests

SERVICENOW_INSTANCE = (
    "https://volvoitsm.service-now.com"
)

USERNAME = "a447927"
PASSWORD = "Xperia@Feb2026"

URL = (
    f"{SERVICENOW_INSTANCE}"
    "/api/now/table/incident"
)

params = {
    "sysparm_limit": 5,
    "sysparm_fields": (
        "number,"
        "short_description,"
        "state,"
        "priority,"
        "sys_updated_on"
    )
}

incidents = []

try:

    session = requests.Session()

    session.auth = (
        USERNAME,
        PASSWORD
    )

    headers = {
        "Accept": "application/json"
    }

    response = session.get(
        URL,
        headers=headers,
        params=params,
        timeout=30
    )

    print("Status:",
          response.status_code)

    print(response.text)

    if response.status_code == 200:

        data = response.json()

        for incident in data.get(
            "result",
            []
        ):

            incidents.append({

                "number":
                    incident.get(
                        "number",
                        ""
                    ),

                "description":
                    incident.get(
                        "short_description",
                        ""
                    ),

                "state":
                    incident.get(
                        "state",
                        ""
                    ),

                "priority":
                    incident.get(
                        "priority",
                        ""
                    ),

                "updated":
                    incident.get(
                        "sys_updated_on",
                        ""
                    )
            })

    else:

        print(
            "ServiceNow Error:"
        )

except Exception as e:

    print(
        "Collector Error:",
        str(e)
    )

