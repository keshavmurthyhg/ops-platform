import pandas as pd



def load_excel(file_path):
    return pd.read_excel(file_path)



def normalize_dataframe(df):

    df.columns = [str(col).strip().lower() for col in df.columns]

    df = df.fillna('')

    for column in df.columns:
        df[column] = df[column].astype(str).str.strip()

    return df
