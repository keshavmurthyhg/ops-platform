import pandas as pd


def apply_search(df, keyword, search_in=None):
    """
    search_in: list of field keys to search in.
               Possible values: 'short_description', 'description', 'resolution_notes'
               Maps to DataFrame column 'Description' (short_description),
               'Full Description' (description), 'Resolution Notes' (resolution_notes).
               If None or empty, defaults to searching only 'Description' (short_description).
    """
    if not keyword:
        return df

    keyword = keyword.lower()

    # Column mapping from search_in keys to actual DataFrame columns
    FIELD_MAP = {
        "short_description": "Description",
        "description": "Full Description",
        "resolution_notes": "Resolution Notes",
    }

    # Default: short description only
    if not search_in:
        search_in = ["short_description"]

    # Collect columns that exist in the dataframe
    columns_to_search = []
    for field in search_in:
        col = FIELD_MAP.get(field)
        if col and col in df.columns:
            columns_to_search.append(col)

    # Fallback: if no mapped columns exist, search Description
    if not columns_to_search:
        if "Description" in df.columns:
            columns_to_search = ["Description"]
        else:
            return df

    # Build mask across selected columns
    mask = pd.Series([False] * len(df), index=df.index)
    for col in columns_to_search:
        mask = mask | df[col].astype(str).str.lower().str.contains(keyword, na=False)

    return df[mask]
