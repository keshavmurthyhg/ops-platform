# =========================================================
# BUILD CHART DATA
# =========================================================
def build_chart_data(pivot_df):

    if pivot_df.empty:

        return {

            "labels": [],

            "datasets": []

        }


    labels = list(
        pivot_df.index
    )

    datasets = []


    for year in pivot_df.columns:

        datasets.append({

            "label": str(year),

            "data": pivot_df[year].tolist()

        })


    return {

        "labels": labels,

        "datasets": datasets

    }