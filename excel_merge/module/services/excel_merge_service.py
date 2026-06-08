import pandas as pd
import os

from datetime import datetime

from excel_merge.module.logic.dataframe_utils import (
    load_excel,
    normalize_dataframe
)

from excel_merge.module.logic.validator import (
    validate_dataframes
)

from excel_merge.module.logic.merge_engine import (
    merge_dataframes
)

from excel_merge.module.logic.deduplicator import (
    remove_duplicates
)


def process_excel_merge(
    old_file,
    new_file,
    key_column,
    latest_logic,
    date_column,
    output_folder
):

    old_df = load_excel(old_file)
    new_df = load_excel(new_file)

    old_df = normalize_dataframe(old_df)
    new_df = normalize_dataframe(new_df)

    validate_dataframes(
        old_df,
        new_df,
        key_column
    )

    (
        merged_df,
        updated_df,
        new_records_df,
        updated_cells
    ) = merge_dataframes(
        old_df=old_df,
        new_df=new_df,
        key_column=key_column,
        latest_logic=latest_logic,
        date_column=date_column
    )

    merged_df, duplicates_removed_df = remove_duplicates(
        merged_df,
        key_column
    )

    preview_columns = merged_df.columns.tolist()

    preview_rows = (
        merged_df
        .head(50)
        .fillna("")
        .to_dict(orient='records')
    )

    timestamp = datetime.now().strftime(
        '%d%b%Y_%H%M%S'
    )

    output_filename = (
        f'Merged_Output_{timestamp}.xlsx'
    )

    output_path = os.path.join(
        output_folder,
        output_filename
    )

    with pd.ExcelWriter(
        output_path,
        engine='openpyxl'
    ) as writer:

        merged_df.to_excel(
            writer,
            sheet_name='Merged_Data',
            index=False
        )

        updated_df.to_excel(
            writer,
            sheet_name='Updated_Records',
            index=False
        )

        new_records_df.to_excel(
            writer,
            sheet_name='New_Records',
            index=False
        )

        duplicates_removed_df.to_excel(
            writer,
            sheet_name='Duplicates_Removed',
            index=False
        )

    new_rows_list = []

    if not new_records_df.empty:

        new_rows_list = (
            new_records_df[key_column.lower()]
            .astype(str)
            .tolist()
        )

    return {

        'success': True,

        'message':
            'Excel merge completed successfully',

        'download_file':
            output_filename,

        'total_rows':
            len(merged_df),

        'updated_rows':
            len(updated_df),

        'new_rows':
            len(new_records_df),

        'duplicates_removed':
            len(duplicates_removed_df),

        'preview_columns':
            preview_columns,

        'preview_rows':
            preview_rows,

        'updated_cells':
            updated_cells,

        'new_rows_list':
            new_rows_list
    }