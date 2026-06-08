def remove_duplicates(df, key_column):

    before_count = len(df)

    deduplicated_df = df.drop_duplicates(
        subset=[key_column.lower()],
        keep='last'
    )

    duplicate_rows = before_count - len(deduplicated_df)

    duplicates_removed_df = df[df.duplicated(
        subset=[key_column.lower()],
        keep='last'
    )]

    return deduplicated_df, duplicates_removed_df
