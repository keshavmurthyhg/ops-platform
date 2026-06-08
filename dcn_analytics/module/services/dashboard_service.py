import pandas as pd

from dcn_analytics.module.logic.validator import (
    validate_master_dataset
)

from dcn_analytics.module.logic.analytics_engine import (

    prepare_dataframe,

    build_daily_summary,

    build_monthly_chart_data,

    build_monthly_pivot,

    build_kpi

)


# =========================================================
# LOAD DASHBOARD
# =========================================================
def load_dashboard_data():

    try:

        # =================================================
        # MASTER FILE
        # =================================================
        file_path = validate_master_dataset()

        # =================================================
        # READ EXCEL
        # =================================================
        df = pd.read_excel(
            file_path
        )

        # =================================================
        # PREPARE
        # =================================================
        df = prepare_dataframe(df)

        # =================================================
        # DAILY SUMMARY
        # =================================================
        daily_summary_df = build_daily_summary(
            df
        )

        # =================================================
        # EMPTY DATA
        # =================================================
        if daily_summary_df.empty:

            return {

                "success": True,

                "kpi": {

                    "total_missing": 0,

                    "latest_dcn": "-",

                    "current_month": 0,

                    "last_updated": "-"

                },

                "daily_summary": [],

                "monthly_pivot": [],

                "chart_data": {

                    "labels": [],

                    "datasets": []

                }

            }

        # =================================================
        # CHART
        # =================================================
        chart_data = build_monthly_chart_data(
            daily_summary_df
        )

        # =================================================
        # PIVOT
        # =================================================
        monthly_pivot = build_monthly_pivot(
            daily_summary_df
        )

        # =================================================
        # KPI
        # =================================================
        kpi = build_kpi(
            daily_summary_df
        )

        # =================================================
        # RESPONSE
        # =================================================
        return {

            "success": True,

            "kpi": kpi,

            "daily_summary":

                daily_summary_df.to_dict(
                    orient="records"
                ),

            "monthly_pivot":

                monthly_pivot,

            "chart_data":

                chart_data

        }

    except Exception as error:

        return {

            "success": False,

            "message": str(error),

            "kpi": {

                "total_missing": 0,

                "latest_dcn": "-",

                "current_month": 0,

                "last_updated": "-"

            },

            "daily_summary": [],

            "monthly_pivot": [],

            "chart_data": {

                "labels": [],

                "datasets": []

            }

        }