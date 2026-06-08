import os
import traceback
import pandas as pd

from datetime import datetime

from dcn_sequence.module.logic.validator import (
    validate_excel_file,
    validate_required_columns
)

from dcn_sequence.module.logic.dataframe_utils import (
    prepare_dataframe
)

from dcn_sequence.module.logic.sequence_engine import (

    extract_dcn_numbers,

    find_missing_sequences,

    build_missing_dataframe
)


# =========================================================
# OUTPUT FOLDER
# =========================================================
OUTPUT_DIR = os.path.join(
    "outputs",
    "dcn_sequence"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# =========================================================
# PROCESS DCN SEQUENCE
# =========================================================
def process_dcn_sequence(file_path):

    try:

        # =================================================
        # VALIDATE FILE
        # =================================================
        validate_excel_file(file_path)


        # =================================================
        # READ EXCEL
        # =================================================
        df = pd.read_excel(
            file_path
        )


        # =================================================
        # CLEAN DATAFRAME
        # =================================================
        df = prepare_dataframe(df)


        # =================================================
        # VALIDATE COLUMNS
        # =================================================
        validate_required_columns(df)


        # =================================================
        # EXTRACT DCN NUMBERS
        # =================================================
        numbers = extract_dcn_numbers(df)


        # =================================================
        # FIND MISSING
        # =================================================
        missing_numbers = find_missing_sequences(
            numbers
        )


        # =================================================
        # BUILD OUTPUT
        # =================================================
        result_df = build_missing_dataframe(
            missing_numbers
        )


        # =================================================
        # OUTPUT FILE NAME
        # =================================================
        timestamp = datetime.now().strftime(
            "%d%b%Y_%H%M%S"
        )

        output_filename = (

            f"DCN_Missing_Sequence_"
            f"{timestamp}.xlsx"

        )

        output_path = os.path.join(
            OUTPUT_DIR,
            output_filename
        )


        # =================================================
        # SAVE OUTPUT
        # =================================================
        result_df.to_excel(
            output_path,
            index=False
        )


        # =================================================
        # RESPONSE
        # =================================================
        return {

            "success": True,

            "message":
                "Missing sequence detection completed",

            "total_missing":
                len(result_df),

            "preview":
                result_df.head(100).to_dict(
                    orient="records"
                ),

            "output_file":
                output_filename
        }

    except Exception as error:

        traceback.print_exc()

        return {

            "success": False,

            "message": str(error)
        }