def validate_dataframes(old_df, new_df, key_column):

    if old_df.empty:
        raise Exception('Old file is empty')

    if new_df.empty:
        raise Exception('New file is empty')

    if key_column.lower() not in old_df.columns:
        raise Exception(f'Key column not found in old file: {key_column}')

    if key_column.lower() not in new_df.columns:
        raise Exception(f'Key column not found in new file: {key_column}')
