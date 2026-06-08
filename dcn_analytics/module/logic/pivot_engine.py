import pandas as pd


# =========================================================
# BUILD MONTHLY PIVOT
# =========================================================
def build_monthly_pivot(daily_summary_df):

    if daily_summary_df.empty:

        return pd.DataFrame()


    # =====================================================
    # DATE
    # =====================================================
    daily_summary_df["DateObj"] = pd.to_datetime(

        daily_summary_df["Date"],
        format="%d-%b-%Y",
        errors="coerce"

    )


    # =====================================================
    # MONTH / YEAR
    # =====================================================
    daily_summary_df["Month"] = (
        daily_summary_df["DateObj"]
        .dt.strftime("%b")
    )

    daily_summary_df["Year"] = (
        daily_summary_df["DateObj"]
        .dt.year
    )


    # =====================================================
    # PIVOT
    # =====================================================
    pivot_df = pd.pivot_table(

        daily_summary_df,

        index="Month",

        columns="Year",

        values="Sequence Skipped",

        aggfunc="sum",

        fill_value=0

    )


    # =====================================================
    # MONTH ORDER
    # =====================================================
    month_order = [

        "Jan", "Feb", "Mar",
        "Apr", "May", "Jun",
        "Jul", "Aug", "Sep",
        "Oct", "Nov", "Dec"

    ]

    pivot_df = pivot_df.reindex(
        month_order
    )


    pivot_df = pivot_df.fillna(0)

    pivot_df = pivot_df.astype(int)


    return pivot_df