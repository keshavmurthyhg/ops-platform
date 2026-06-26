import re


# -----------------------------------------------
# EXTRACT AZURE TICKET IDs FROM RESOLUTION NOTES
# -----------------------------------------------
def extract_azure_ids(text):
    """
    Parse Azure bug/work item IDs from a resolution notes string.
    Looks for patterns like: AB#1234, #1234, Bug 1234, WI-1234, or bare integers.
    Returns a list of unique ID strings found.
    """
    if not text or str(text).strip() in ("", "nan"):
        return []

    s = str(text)

    patterns = [
        r'AB#\s*(\d+)',          # AB#12345
        r'Bug\s*[#:]?\s*(\d+)',  # Bug 12345 / Bug #12345
        r'WI[#\-]?\s*(\d+)',     # WI-12345
        r'#(\d{4,})',            # #12345 (4+ digits to avoid short refs)
    ]

    found = []
    for pat in patterns:
        for m in re.finditer(pat, s, re.IGNORECASE):
            found.append(m.group(1))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for x in found:
        if x not in seen:
            seen.add(x)
            unique.append(x)

    return unique


# -----------------------------------------------
# CALCULATE KPI
# -----------------------------------------------
def calculate_kpi(df):

    if df.empty:
        return {
            "total": 0,
            "open": 0,
            "closed": 0,
            "cancelled": 0
        }

    status = df["Status"].astype(str).str.lower()

    open_count      = status.str.contains("open|new|progress|hold", na=False).sum()
    closed_count    = status.str.contains("closed", na=False).sum()
    cancelled_count = status.str.contains("cancel", na=False).sum()

    return {
        "total":     len(df),
        "open":      int(open_count),
        "closed":    int(closed_count),
        "cancelled": int(cancelled_count)
    }


# -----------------------------------------------
# CALCULATE REPORT BREAKDOWN
# -----------------------------------------------
def calculate_report(df):
    """
    Returns a dict with per-source counts and, for SNOW rows,
    a list of Azure ticket IDs parsed from Resolution Notes.
    """
    if df.empty:
        return {
            "incident": {"total": 0, "open": 0, "closed": 0},
            "azure":    {"total": 0, "open": 0, "closed": 0},
            "ptc":      {"total": 0, "open": 0, "closed": 0},
            "azure_from_snow": []
        }

    def source_stats(src):
        sub    = df[df["Source"] == src]
        status = sub["Status"].astype(str).str.lower()
        return {
            "total":  len(sub),
            "open":   int(status.str.contains("open|new|progress|hold", na=False).sum()),
            "closed": int(status.str.contains("closed|resolved|complete", na=False).sum()),
        }

    # Parse Azure ticket IDs embedded in SNOW Resolution Notes
    snow_df   = df[df["Source"] == "SNOW"].copy()
    azure_ids = []

    if "Resolution Notes" in snow_df.columns:
        for notes in snow_df["Resolution Notes"].dropna():
            azure_ids.extend(extract_azure_ids(notes))

    # Deduplicate
    seen       = set()
    unique_ids = []
    for aid in azure_ids:
        if aid not in seen:
            seen.add(aid)
            unique_ids.append(aid)

    return {
        "incident":        source_stats("SNOW"),
        "azure":           source_stats("AZURE"),
        "ptc":             source_stats("PTC"),
        "azure_from_snow": unique_ids
    }
