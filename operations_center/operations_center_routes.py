import pandas as pd
import os
import subprocess

from io import BytesIO
from datetime import datetime
from pathlib import Path
from flask import (
    Blueprint,
    render_template,
    jsonify,
    send_file,
    request
)

from operations_center.module.ops_center_excel_refresh import (
    refresh_power_query
)

from operations_center.module.ops_ptc_auto_download import (
    download_latest_ptc_csv
)

from operations_center.module.ops_center_service import (
    get_operations_dashboard_data
)

from common.utils.links import (
    get_url
)

#from operations_center.module.ops_servicenow_collector import (
#    incidents
#)


from operations_center.module.ops_azure_collector import (
    azure_cases
)

operations_center_bp = Blueprint(
    "operations_center",
    __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/operations_center/static"
)

DATA_FILE = os.path.join(
    "data",
    "operations_tracker.xlsx"
)

from operations_center.module.ops_support_email_collector import (
    get_support_emails
)

from operations_center.module.ops_integration_failure_collector import (
    get_integration_failures
)

@operations_center_bp.route(
    "/api/operations-center/export",
    methods=["POST"]
)
def export_operations_view():

    try:

        payload = request.get_json()

        rows = payload.get("rows", [])

        tracker = payload.get(
            "tracker",
            "operations"
        )

        df = pd.DataFrame(rows)

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                index=False,
                sheet_name=tracker[:31]
            )

        output.seek(0)

        timestamp = datetime.now().strftime(
            "%d%b%Y_%H%M"
        )

        return send_file(
            output,
            as_attachment=True,
            download_name=
                f"{tracker}_{timestamp}.xlsx",
            mimetype=
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@operations_center_bp.route("/operations-center")
def operations_center():

    dashboard_data = (
        get_operations_dashboard_data()
    )

    
    dashboard_data["azure_data"] = azure_cases


    # -----------------------------------
    # INCIDENT LINKS
    # -----------------------------------
    for row in dashboard_data["incident_data"]:

        row["number_url"] = get_url(
            "incident",
            row.get("Number")
        )

        vendor_ticket = str(
            row.get("Vendor Ticket", "")
        ).strip()

        if vendor_ticket.isdigit():

            row["vendor_ticket_url"] = get_url(
                "ptc case",
                vendor_ticket
            )

        else:
            row["vendor_ticket_url"] = ""

    # -----------------------------------
    # AZURE LINKS
    # -----------------------------------
    for row in dashboard_data["azure_data"]:

        row["number_url"] = get_url(
            "azure bug",
            row.get("Number")
        )

    # -----------------------------------
    # PTC LINKS
    # -----------------------------------
    for row in dashboard_data["ptc_data"]:

        row["number_url"] = get_url(
            "ptc case",
            row.get("Number")
        ) 


    return render_template(
        "operations_center.html",

        support_data=
            dashboard_data["support_data"],

        failure_data=
            dashboard_data["failure_data"],

        incident_data=
            dashboard_data["incident_data"],

        azure_data=
            dashboard_data["azure_data"],

        ptc_data=
            dashboard_data["ptc_data"],

        summary=
            dashboard_data["summary"]
    )

@operations_center_bp.route(
    "/api/operations-center/refresh"
)
def refresh_operations_data():

    dashboard_data = (
        get_operations_dashboard_data()
    )

    status_file = Path(
        "data/refresh_status.txt"
    )

    refresh_time = "Never"

    if status_file.exists():

        refresh_time = (
            status_file.read_text(
                encoding="utf-8"
            ).strip()
        )

    return jsonify({

        "success": True,

        "refresh_time":
            refresh_time,

        "support_data":
            dashboard_data["support_data"],

        "failure_data":
            dashboard_data["failure_data"],

        "incident_data":
            dashboard_data["incident_data"],

        "azure_data":
            dashboard_data["azure_data"],

        "ptc_data":
            dashboard_data["ptc_data"],

        "summary":
            dashboard_data["summary"]
    })

@operations_center_bp.route(
    "/api/operations-center/refresh-power-query"
)
def refresh_power_query_route():

    result = refresh_power_query()

    return jsonify(result)


@operations_center_bp.route(
    "/api/operations-center/launch-edge-debug",
    methods=["POST"]
)
def launch_edge_debug_route():
    """Launch start_edge_debug.bat to open Edge in debug mode."""
    import subprocess
    from pathlib import Path
    bat_path = Path(__file__).resolve().parent.parent / "start_edge_debug.bat"
    try:
        if not bat_path.exists():
            return jsonify({"success": False, "message": f"Bat file not found: {bat_path}"})
        # Run the bat in its own console window so Edge starts independently
        # of the Flask process — use shell=True so the bat runs cleanly
        subprocess.Popen(
            f'start "" cmd /c "{bat_path}"',
            shell=True,
        )
        return jsonify({
            "success": True,
            "message": f"Launched: {bat_path}\nEdge will open in debug mode. Log in to PTC if prompted, then click Refresh PTC Cases."
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@operations_center_bp.route(
    "/api/operations-center/refresh-ptc",
    methods=["POST"]
)
def refresh_ptc_csv_route():
    """
    Executes the direct Python script to hook onto the open Edge session,
    download the file, and save it to data/Ptc.csv.
    """
    try:
        # Launch automation process
        result = download_latest_ptc_csv()
        
        # Return status output structure safely to let client handle coloration and display logic
        return jsonify({
            "success": result.get("success", False),
            "message": result.get("message", "Data processing terminated"),
            "detail": result.get("detail", "")
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to execute PTC data refresh",
            "detail": str(e)
        })


@operations_center_bp.route(
    "/api/refresh-status"
)
def get_refresh_status():

    status_file = Path(
        "data/refresh_status.txt"
    )

    if status_file.exists():

        return jsonify({
            "last_refresh":
                status_file.read_text(
                    encoding="utf-8"
                ).strip()
        })

    return jsonify({
        "last_refresh":
            "Never"
    })

@operations_center_bp.route(
    "/api/operations-center/support-emails"
)
def support_emails_api():

    try:

        data = get_support_emails(500)

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


@operations_center_bp.route(
    "/api/operations-center/integration-failures"
)
def integration_failures_api():

    try:

        data = get_integration_failures(500)

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        })


#@operations_center_bp.route(
#    "/api/incidents"
#)
#def get_incidents():

#    return jsonify({
 #       "success": True,
#        "data": incidents
#    })


@operations_center_bp.route(
    "/api/azure-cases"
)
def get_azure_cases():

    return jsonify({
        "success": True,
        "data": azure_cases
    })



