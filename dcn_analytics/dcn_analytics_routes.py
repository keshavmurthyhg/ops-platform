from flask import (
    Blueprint,
    render_template,
    jsonify,
    send_file,
    request
)

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from io import BytesIO
import pandas as pd  # <-- THIS WAS MISSING!
from datetime import datetime
from datetime import timedelta
import os


from dcn_analytics.module.services.dashboard_service import (
    load_dashboard_data
)

# Import your data file path variable from your validator module
from dcn_analytics.module.logic.validator import DATA_FILE

dcn_analytics_bp = Blueprint(
    "dcn_analytics",
    __name__
)

# Ensure you import your core logical engines for filters
from dcn_analytics.module.logic.validator import validate_master_dataset
from dcn_analytics.module.logic.analytics_engine import (
    prepare_dataframe,
    build_daily_summary,
    build_monthly_chart_data,
    build_monthly_pivot,
    build_kpi
)

# =========================================================
# PAGE
# =========================================================
@dcn_analytics_bp.route(
    "/dcn-analytics"
)
def dcn_analytics_page():

    return render_template(
        "dcn_analytics.html"
    )


# =========================================================
# DASHBOARD API
# =========================================================
@dcn_analytics_bp.route(
    "/api/dcn-analytics/dashboard"
)
def dashboard_api():

    try:

        result = load_dashboard_data()

        return jsonify(result)

    except Exception as error:

        return jsonify({

            "success": False,

            "message": str(error)

        })

# =========================================================
# DOWNLOAD DOWNLOAD REPORT: MONTHLY PIVOT
# =========================================================
@dcn_analytics_bp.route("/api/dcn-analytics/download/monthly")
def download_monthly_report():
    try:
        data = load_dashboard_data()
        pivot_records = data.get("monthly_pivot", [])
        
        df = pd.DataFrame(pivot_records)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Monthly Pivot Summary")
            
        output.seek(0)
        timestamp = datetime.now().strftime("%d%b%Y_%H%M")
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f"Monthly_Pivot_Summary_{timestamp}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return str(e), 500


# =========================================================
# DOWNLOAD REPORT: DAILY SKIPPED SUMMARY
# =========================================================
@dcn_analytics_bp.route("/api/dcn-analytics/download/daily")
def download_daily_report():
    try:
        data = load_dashboard_data()
        daily_records = data.get("daily_summary", [])
        
        # Build clean export dataframe
        df = pd.DataFrame(daily_records)
        if not df.empty and "Total DCNs" in df.columns:
            df = df.drop(columns=["Total DCNs"])
            
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Daily Skipped Summary")
            
        output.seek(0)
        timestamp = datetime.now().strftime("%d%b%Y_%H%M")
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f"Daily_Skipped_Summary_{timestamp}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return str(e), 500


# =========================================================
# UPLOAD EXCEL DATA FILE
# =========================================================
@dcn_analytics_bp.route(
    "/api/dcn-analytics/upload",
    methods=["POST"]
)
def upload_excel_api():
    try:
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "message": "No file part in the request"
            }), 400

        file = request.files["file"]
        
        if file.filename == "":
            return jsonify({
                "success": False,
                "message": "No file selected"
            }), 400

        if file and (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
            # Ensure target directory exists
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            
            # Save and overwrite master file
            file.save(DATA_FILE)
            
            return jsonify({
                "success": True,
                "message": "Master dataset uploaded and refreshed successfully!"
            })
            
        return jsonify({
            "success": False,
            "message": "Invalid file type. Please upload a valid Excel spreadsheet (.xlsx)"
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": f"Upload failed: {str(error)}"
        }), 500

@dcn_analytics_bp.route("/api/dcn-analytics/download/full-dashboard")
def download_full_excel_dashboard():
    try:
        # Fetch live data engine structures
        data = load_dashboard_data()
        pivot_records = data.get("monthly_pivot", [])
        daily_records = data.get("daily_summary", [])

        # Create a new blank openpyxl workbook
        wb = openpyxl.Workbook()
        
        # ---------------------------------------------------------
        # SHEET 1: DASHBOARD (PIVOT + LIVE CHART)
        # ---------------------------------------------------------
        ws_dash = wb.active
        ws_dash.title = "Dashboard"
        ws_dash.views.sheetView[0].showGridLines = True

        # Styles definition
        font_title = Font(name="Segoe UI", size=16, bold=True, color="183153")
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        font_data = Font(name="Segoe UI", size=11)
        font_total = Font(name="Segoe UI", size=11, bold=True)
        
        fill_header = PatternFill(start_color="445B7C", end_color="445B7C", fill_type="solid")
        fill_total = PatternFill(start_color="E9ECEF", end_color="E9ECEF", fill_type="solid")
        
        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        
        border_thin = Side(border_style="thin", color="DCDCDC")
        border_double = Side(border_style="double", color="333333")
        
        cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
        total_border = Border(top=border_thin, bottom=border_double)

        # Title Block
        ws_dash["B2"] = "DCN Analytics - Monthly Operations Dashboard"
        ws_dash["B2"].font = font_title
        ws_dash.row_dimensions[2].height = 25

        # Build Table Headers (Starting at Row 4)
        headers = ["Month", "2023", "2024", "2025", "2026"]
        for col_idx, text in enumerate(headers, start=2): # Col B to F
            cell = ws_dash.cell(row=4, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
        ws_dash.row_dimensions[4].height = 24

        # Inject Pivot Records
        start_row = 5
        for idx, row in enumerate(pivot_records):
            current_row = start_row + idx
            ws_dash.row_dimensions[current_row].height = 20
            
            r_month = ws_dash.cell(row=current_row, column=2, value=row.get("Month", "-"))
            r_2023  = ws_dash.cell(row=current_row, column=3, value=int(row.get("2023", 0)))
            r_2024  = ws_dash.cell(row=current_row, column=4, value=int(row.get("2024", 0)))
            r_2025  = ws_dash.cell(row=current_row, column=5, value=int(row.get("2025", 0)))
            r_2026  = ws_dash.cell(row=current_row, column=6, value=int(row.get("2026", 0)))
            
            for cell in [r_month, r_2023, r_2024, r_2025, r_2026]:
                cell.font = font_data
                cell.alignment = align_center
                cell.border = cell_border

        # Dynamic Total Footer Row
        total_row = start_row + len(pivot_records)
        ws_dash.row_dimensions[total_row].height = 22
        
        t_label = ws_dash.cell(row=total_row, column=2, value="Total")
        t_2023  = ws_dash.cell(row=total_row, column=3, value=f"=SUM(C{start_row}:C{total_row-1})")
        t_2024  = ws_dash.cell(row=total_row, column=4, value=f"=SUM(D{start_row}:D{total_row-1})")
        t_2025  = ws_dash.cell(row=total_row, column=5, value=f"=SUM(E{start_row}:E{total_row-1})")
        t_2026  = ws_dash.cell(row=total_row, column=6, value=f"=SUM(F{start_row}:F{total_row-1})")
        
        for cell in [t_label, t_2023, t_2024, t_2025, t_2026]:
            cell.font = font_total
            cell.fill = fill_total
            cell.alignment = align_center
            cell.border = total_border

        # CREATE EDITABLE NATIVE EXCEL BAR CHART
        chart = BarChart()
        chart.type = "col"
        chart.style = 10
        chart.title = "Monthly DCN Skipped Trend"
        chart.y_axis.title = "Skipped Count"
        chart.x_axis.title = "Months"
        chart.width = 16
        chart.height = 12

        # Data references (Columns C to F, Rows 4 to 16 - Excludes Grand Total Row)
        chart_data = Reference(ws_dash, min_col=3, min_row=4, max_col=6, max_row=total_row-1)
        # Category references (Column B Months, Rows 5 to 16)
        chart_cats = Reference(ws_dash, min_col=2, min_row=5, max_row=total_row-1)
        
        chart.add_data(chart_data, titles_from_data=True)
        chart.set_categories(chart_cats)
        
        # Position Chart right next to the Pivot summary table
        ws_dash.add_chart(chart, "H4")

        # Set specific Column Widths for Dashboard Layout
        ws_dash.column_dimensions["B"].width = 15
        for col in ["C", "D", "E", "F"]:
            ws_dash.column_dimensions[col].width = 12

        # ---------------------------------------------------------
        # SHEET 2: DAILY SKIPPED DATA
        # ---------------------------------------------------------
        ws_daily = wb.create_sheet(title="Daily Skipped Details")
        ws_daily.views.sheetView[0].showGridLines = True
        
        daily_headers = ["SL NO", "Date", "Sequence Skipped", "Skipped DCN Numbers"]
        for col_idx, text in enumerate(daily_headers, start=1):
            cell = ws_daily.cell(row=1, column=col_idx, value=text)
            cell.font = font_header
            cell.fill = PatternFill(start_color="183153", end_color="183153", fill_type="solid")
            cell.alignment = align_left if col_idx == 4 else align_center
        ws_daily.row_dimensions[1].height = 24

        for idx, row in enumerate(daily_records):
            r_idx = idx + 2
            ws_daily.row_dimensions[r_idx].height = 19
            
            c_sl   = ws_daily.cell(row=r_idx, column=1, value=idx + 1)
            c_date = ws_daily.cell(row=r_idx, column=2, value=row.get("Date", "-"))
            c_seq  = ws_daily.cell(row=r_idx, column=3, value=int(row.get("Sequence Skipped", 0)))
            c_nums = ws_daily.cell(row=r_idx, column=4, value=row.get("Skipped DCN Numbers", "-"))
            
            c_sl.alignment = align_center
            c_date.alignment = align_center
            c_seq.alignment = align_center
            c_nums.alignment = align_left
            
            for cell in [c_sl, c_date, c_seq, c_nums]:
                cell.font = font_data
                cell.border = cell_border
                
        # Auto-fit Column Widths for Daily Details Sheet
        for col in ws_daily.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws_daily.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # ---------------------------------------------------------
        # SHIP WORKBOOK TO BROWSER
        # ---------------------------------------------------------
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        timestamp = datetime.now().strftime("%d%b%Y_%H%M")
        return send_file(
            output,
            as_attachment=True,
            download_name=f"DCN_Operations_Dashboard_{timestamp}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as error:
        return jsonify({"success": False, "message": f"Excel generation failed: {str(error)}"}), 500


# =========================================================
# APPLY FILTERS ROUTE
# =========================================================
@dcn_analytics_bp.route("/api/dcn-analytics/apply-filters", methods=["POST"])
def apply_filters_api():
    try:
        payload = request.get_json() or {}
        
        filter_type = payload.get("filter_type", "none")
        start_date_str = payload.get("start_date", "")
        end_date_str = payload.get("end_date", "")
        selected_year = payload.get("year", "")
        quick_option = payload.get("quick_option", "")

        # 1. Load and process the base master dataset
        file_path = validate_master_dataset()
        df = pd.read_excel(file_path)
        df = prepare_dataframe(df)

        # 2. Extract full daily details before date filtering
        daily_summary_df = build_daily_summary(df)

        if daily_summary_df.empty:
            return jsonify({
                "success": True,
                "kpi": {"total_missing": 0, "latest_dcn": "-", "current_month": 0, "last_updated": "-"},
                "daily_summary": [], "monthly_pivot": [],
                "chart_data": {"labels": [], "datasets": []}
            })

        # Convert Date string back to datetime objects for filtering comparisons
        daily_summary_df["FilterDate"] = pd.to_datetime(daily_summary_df["Date"], format="%d-%b-%Y")

        # 3. Apply Filtering Logic based on UI Selection
        # --- DATE RANGE ---
        if filter_type == "range" and start_date_str and end_date_str:
            start_dt = pd.to_datetime(start_date_str)
            end_dt = pd.to_datetime(end_date_str) + timedelta(days=1) - timedelta(seconds=1) # Include full end day
            daily_summary_df = daily_summary_df[
                (daily_summary_df["FilterDate"] >= start_dt) & 
                (daily_summary_df["FilterDate"] <= end_dt)
            ]

        # --- BY YEAR ---
        elif filter_type == "year" and selected_year:
            daily_summary_df = daily_summary_df[daily_summary_df["Year"] == int(selected_year)]

        # --- QUICK SELECT ---
        elif filter_type == "quick" and quick_option:
            days_to_subtract = int(quick_option)
            # Use the most recent record date as reference point instead of hard system clock
            max_date = daily_summary_df["FilterDate"].max()
            boundary_date = max_date - timedelta(days=days_to_subtract)
            daily_summary_df = daily_summary_df[daily_summary_df["FilterDate"] >= boundary_date]

        # Drop temporary indexing filter column
        daily_summary_df = daily_summary_df.drop(columns=["FilterDate"])

        # 4. Re-calculate metrics from our newly filtered dataframe subset
        chart_data = build_monthly_chart_data(daily_summary_df)
        monthly_pivot = build_monthly_pivot(daily_summary_df)
        kpi = build_kpi(daily_summary_df)

        return jsonify({
            "success": True,
            "kpi": kpi,
            "daily_summary": daily_summary_df.to_dict(orient="records"),
            "monthly_pivot": monthly_pivot,
            "chart_data": chart_data
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": f"Filtering failed: {str(error)}"
        }), 500