from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    send_file
)

import pandas as pd
from io import BytesIO

from bulk.module.bulk_service import (
    filter_incidents,
    generate_bulk_zip_file
)

from common.logger import setup_logger

logger = setup_logger("bulk")

bulk_bp = Blueprint(
    "bulk",
    __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/bulk/static"
)


# -----------------------------
# BULK PAGE
# -----------------------------
@bulk_bp.route("/bulk")
def bulk_page():
    logger.info("Bulk page loaded")
    return render_template("bulk.html")


# -----------------------------
# FILTER INCIDENTS
# -----------------------------
@bulk_bp.route("/bulk/filter-incidents", methods=["POST"])
def bulk_filter_route():
    try:
        data = request.json
        logger.info("Filter incidents: priority=%s year=%s",
                    data.get("priority"), data.get("year"))

        incidents = filter_incidents(
            priority=data.get("priority"),
            year=data.get("year"),
            from_date=data.get("from_date"),
            to_date=data.get("to_date")
        )

        logger.info("Filter returned %d incidents", len(incidents))
        return jsonify({"success": True, "incidents": incidents})

    except Exception as e:
        logger.error("Filter failed: %s", str(e))
        return jsonify({"success": False, "message": str(e)})


# -----------------------------
# DOWNLOAD ZIP
# -----------------------------
@bulk_bp.route("/bulk/download-zip", methods=["POST"])
def bulk_download_zip_route():
    try:
        data            = request.json
        incident_text   = data.get("incidents", "")
        output_type     = data.get("output_type", "both")

        incident_numbers = [
            x.strip()
            for x in incident_text.split(",")
            if x.strip()
        ]

        logger.info("Bulk ZIP requested: %d incidents, format=%s",
                    len(incident_numbers), output_type)

        zip_buffer = generate_bulk_zip_file(incident_numbers, output_type)

        logger.info("Bulk ZIP generated successfully")
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name="bulk_reports.zip",
            mimetype="application/zip"
        )

    except Exception as e:
        logger.error("Bulk ZIP failed: %s", str(e))
        return str(e)


# -----------------------------
# FAILED REPORT DOWNLOAD
# -----------------------------
@bulk_bp.route("/bulk/download-failed-report", methods=["POST"])
def bulk_failed_report():
    try:
        data              = request.json
        failed_incidents  = data.get("failed_incidents", [])

        if not failed_incidents:
            return jsonify({"success": False, "message": "No failed incidents found"})

        logger.info("Failed report download: %d incidents", len(failed_incidents))

        df = pd.DataFrame({"Incident Number": failed_incidents})
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        return send_file(
            csv_buffer,
            as_attachment=True,
            download_name="failed_incidents.csv",
            mimetype="text/csv"
        )

    except Exception as e:
        logger.error("Failed report download error: %s", str(e))
        return str(e)
