from bulk.module.bulk_generator import build_bulk_reports, generate_bulk_zip

def run_bulk(filtered_df, images):

    if filtered_df is None or filtered_df.empty:
        return None

    inc_list = filtered_df["number"].astype(str).tolist()

    reports = build_bulk_reports(filtered_df, inc_list, images)

    if not reports:
        return None

    return generate_bulk_zip(reports)
