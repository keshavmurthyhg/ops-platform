import pandas as pd
import os

from common.utils.parsers import (
    prepare_search_dataframe
)

def load_snow_data():

    file_path = os.path.join("data", "Snow.xlsx")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    df = pd.read_excel(file_path)

    # normalize column names
    df = prepare_search_dataframe(df)

    return df
