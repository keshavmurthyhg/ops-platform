import requests

def fetch_incident(incident_number):
    try:
        url = f"https://volvoitsm.service-now.com/api/now/table/incident?sysparm_query=number={incident_number}"

        headers = {"Accept": "application/json"}

        response = requests.get(url, auth=("username", "password"), headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()["result"]
            if result:
                return result[0]
    except Exception:
        pass

    # Fallback (important for Streamlit Cloud)
    return {
        "number": incident_number,
        "short_description": "Fetched from dashboard / manual input",
        "description": "Details not available from API",
        "priority": "",
        "state": ""
    }


#def fetch_incident(incident_number):
 #   return {
  #      "number": incident_number,
   #     "short_description": "Manual Input",
    #    "description": "No API used",
     #   "priority": "",
      #  "state": ""
    #}
