def apply_filters(df, status="ALL", priority="ALL", keyword=""):

    filtered = df.copy()

    # --- Status filter ---
    if status != "ALL":
        filtered = filtered[filtered["Status"] == status]

    # --- Priority filter ---
    if priority != "ALL":
        filtered = filtered[filtered["Priority"] == priority]

    # --- Keyword search ---
    if keyword:
        keyword = keyword.lower()
        filtered = filtered[
            filtered.astype(str).apply(
                lambda row: row.str.lower().str.contains(keyword).any(),
                axis=1
            )
        ]

    return filtered
