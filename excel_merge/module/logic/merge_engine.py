import pandas as pd



def merge_dataframes(
    old_df,
    new_df,
    key_column,
    latest_logic,
    date_column
):

    key_column = key_column.lower()

    updated_records = []
    new_records = []

    updated_cells = {}

    merged_df = old_df.copy()

    existing_keys = set(old_df[key_column].tolist())

    for _, new_row in new_df.iterrows():

        key_value = new_row[key_column]

        if key_value in existing_keys:

            old_row = merged_df[
                merged_df[key_column] == key_value
            ].iloc[0]

            changed_columns = []

            for col in merged_df.columns:

                old_val = str(old_row[col]).strip()
                new_val = str(new_row[col]).strip()

                if old_val != new_val:
                    changed_columns.append(col)

            if changed_columns:

                merged_df = merged_df[
                    merged_df[key_column] != key_value
                ]

                merged_df = pd.concat([
                    merged_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)

                updated_records.append(new_row)

                updated_cells[key_value] = changed_columns

        else:

            merged_df = pd.concat([
                merged_df,
                pd.DataFrame([new_row])
            ], ignore_index=True)

            new_records.append(new_row)

    updated_df = pd.DataFrame(updated_records)

    new_records_df = pd.DataFrame(new_records)

    return (
        merged_df,
        updated_df,
        new_records_df,
        updated_cells
    )