def fetch_snow_data_from_incident(incident):

    from common.data.snow_loader import load_snow_data

    df = load_snow_data()  # returns DataFrame

    # ✅ FIX: Proper empty check for DataFrame
    if df is None:
        return None

    if hasattr(df, "empty") and df.empty:
        return None

    # ✅ Convert DataFrame → list of dicts
    all_data = df.to_dict(orient="records")

    # 🔍 Find matching incident
    incident_clean = incident.replace("INC", "").strip()

    data = None
    
    for row in all_data:
        number = str(row.get("number", "")).upper().strip()
    
        # Normalize both sides
        number_clean = number.replace("INC", "").strip()
    
        if number_clean == incident_clean:
            data = row
            break

    # 🔄 Normalize structure
    if not data:
        return None   # ✅ VERY IMPORTANT
    
    return {
        "number": data.get("number") or data.get("Number"),
    
        "short_description": data.get("short_description") or data.get("Short description"),
    
        "description": data.get("description") or data.get("Description"),
    
        "created_by": data.get("created_by") or data.get("Created By"),
    
        "created_date": data.get("created_date") or data.get("Created"),
    
        "assigned_to": data.get("assigned_to") or data.get("Assigned To"),
    
        "priority": data.get("priority") or data.get("Priority"),
    
        "resolved_date": data.get("resolved_date") or data.get("Resolved"),
    
        "azure_bug": data.get("azure_bug") or data.get("Azure Bug"),
    
        "ptc_case": data.get("ptc_case") or data.get("PTC Case"),
    
        # ✅ ADD THESE (YOU WERE MISSING)
        "work_notes": data.get("work_notes") or data.get("Work Notes"),
        "comments": data.get("comments") or data.get("Comments"),
        "close_notes": data.get("close_notes") or data.get("Close Notes"),
    }
