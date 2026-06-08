def calculate_kpi(df):

    if df.empty:
        return {"total":0,"open":0,"closed":0,"cancelled":0}

    status = df["Status"].astype(str).str.lower()

    open_count = status.str.contains("open|new|progress|hold", na=False).sum()
    closed_count = status.str.contains("closed", na=False).sum()
    cancelled_count = status.str.contains("cancel", na=False).sum()

    return {
        "total": len(df),
        "open": int(open_count),
        "closed": int(closed_count),
        "cancelled": int(cancelled_count)
    }
