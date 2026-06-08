import pandas as pd

def apply_search(df, keyword):
    if not keyword:
        return df

    keyword = keyword.lower()

    return df[
        df.astype(str)
        .apply(lambda row: row.str.lower().str.contains(keyword))
        .any(axis=1)
    ]
