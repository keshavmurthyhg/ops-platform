import pandas as pd
import os


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

    
    # Use loader's TRACKER_USERS filtered data + merge user stories
    try:
        from operations_center.module.ops_user_stories_collector import user_stories
        merged = list(dashboard_data["azure_data"]) + list(user_stories)
        merged.sort(key=lambda r: r.get("raw_created_date",""), reverse=True)
        dashboard_data["azure_data"] = merged
    except Exception:
        pass  # user_stories module optional


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
            dashboard_data["summary"],

        data_ages=
            dashboard_data.get("data_ages", {})
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
            dashboard_data["summary"],

        "data_ages":
            dashboard_data.get("data_ages", {})
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
    "/api/operations-center/upload-data",
    methods=["POST"]
)
def upload_data_file():
    """
    Accept a CSV/XLSX file upload and save it to the data/ folder
    with the canonical name supplied as 'dest' (Snow.xlsx / Azure.csv / Ptc.csv).
    """
    ALLOWED_DESTS = {"Snow.xlsx", "Azure.csv", "Ptc.csv"}

    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file in request"}), 400

        f    = request.files["file"]
        dest = request.form.get("dest", "").strip()

        if not dest or dest not in ALLOWED_DESTS:
            return jsonify({
                "success": False,
                "message": f"Invalid destination '{dest}'. Must be one of: {', '.join(ALLOWED_DESTS)}"
            }), 400

        if not f.filename:
            return jsonify({"success": False, "message": "No filename"}), 400

        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)

        save_path = data_dir / dest
        f.save(str(save_path))

        size_kb = save_path.stat().st_size // 1024

        return jsonify({
            "success": True,
            "message": f"Saved {dest} ({size_kb:,} KB)",
            "file":    str(save_path)
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



def refresh_ptc_csv_route():
    """
    Trigger a fresh PTC Case Tracker CSV download via Selenium.
    Requires Edge to be running in debug mode on port 9222.
    """
    result = download_latest_ptc_csv()

    return jsonify({
        "success": result["success"],
        "message": result["message"],
        "file":    result.get("file"),
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



# =============================================================================
#  USER GROUP ROUTES — for group-based filtering in Azure tracker
# =============================================================================

@operations_center_bp.route("/api/operations-center/user-groups", methods=["GET"])
def get_user_groups():
    """Return group → [users] mapping from data/user_group_mapping.csv."""
    import csv as _csv
    from pathlib import Path
    mapping_file = Path("data") / "user_group_mapping.csv"
    groups = {}  # { display_name: group_name }
    try:
        if mapping_file.exists():
            with open(mapping_file, encoding="utf-8") as f:
                for row in _csv.DictReader(f):
                    name  = (row.get("Name","") or "").strip()
                    group = (row.get("Group","") or "").strip().upper()
                    if name and group:
                        groups[name] = group
    except Exception as e:
        log.error(f"user_group_mapping load error: {e}")
    return jsonify({"success": True, "groups": groups})


@operations_center_bp.route("/api/operations-center/user-groups", methods=["POST"])
def save_user_groups():
    """Save or update user→group mappings."""
    import csv as _csv
    from pathlib import Path
    payload = request.get_json() or {}
    updates = payload.get("groups", {})  # { "Pradnya Shinde": "WINDCHILL_TEAM" }
    mapping_file = Path("data") / "user_group_mapping.csv"
    mapping_file.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if mapping_file.exists():
        with open(mapping_file, encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                name  = (row.get("Name","") or "").strip()
                group = (row.get("Group","") or "").strip()
                if name:
                    existing[name] = group

    existing.update(updates)
    with open(mapping_file, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=["Name","Group"])
        w.writeheader()
        for name, group in sorted(existing.items()):
            w.writerow({"Name": name, "Group": group.upper()})

    return jsonify({"success": True, "saved": len(existing)})


# =============================================================================
#  REPORT ROUTES — Daily / Weekly / Summary / Range / Excel / PDF / Digest
#  Appended to operations_center_routes.py
# =============================================================================

def _load_module(name):
    try:
        import importlib
        for p in (f"common.utils.{name}", f"operations_center.module.{name}"):
            try: return importlib.import_module(p)
            except ImportError: pass
    except Exception: pass
    return None

_re  = _load_module("report_engine")
_dg  = _load_module("email_digest")


def _ops_data():
    d = get_operations_dashboard_data()
    return dict(
        support_data  = d.get("support_data",  []),
        failure_data  = d.get("failure_data",  []),
        incident_data = d.get("incident_data", []),
        azure_data    = azure_cases,
        ptc_data      = d.get("ptc_data",      []),
    )

def _wm_data():
    import os, csv
    transactions = worker_stats = []
    wvs_queue = []
    try:
        from windchill_monitoring.module.windchill_scraper import scrape_windchill_data
        snap = scrape_windchill_data(status_mode="FAILED")
        transactions = snap.get("transactions", [])
        worker_stats = snap.get("worker_stats", [])
    except Exception:
        pass
    try:
        p = os.path.join("data","history","wvs_queue_history.csv")
        if os.path.exists(p):
            latest = ""
            with open(p, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    ts = r.get("captured_at","") or ""
                    if ts > latest: latest = ts
            if latest:
                with open(p, encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        if (r.get("captured_at","") or "") == latest:
                            wvs_queue.append(dict(r))
    except Exception:
        pass
    return dict(transactions=transactions, wvs_queue=wvs_queue, worker_stats=worker_stats)

def _parse_date_arg(s):
    if not s: return None
    from datetime import date as _d
    try: return _d.fromisoformat(s)
    except Exception: return None


# ── Main report generator ─────────────────────────────────────────────────────
@operations_center_bp.route("/api/operations-center/generate-report", methods=["POST"])
def generate_report():
    if not _re:
        return jsonify({"success":False,"message":"report_engine.py not found"}), 500
    try:
        from flask import Response
        payload      = request.get_json() or {}
        report_type  = payload.get("report_type",  "daily_report")
        from_date    = _parse_date_arg(payload.get("from_date",""))
        to_date      = _parse_date_arg(payload.get("to_date",""))
        date_label   = payload.get("date_label", str(from_date or ""))
        trackers     = payload.get("trackers",   ["failure","support","incident","azure","ptc","wm_tx","wvs","workers"])
        fmt          = payload.get("format",     "html")
        settings     = payload.get("settings",   {})
        now          = datetime.now().strftime("%d %b %Y %H:%M")

        ops = _ops_data()
        wm  = _wm_data()

        kwargs = dict(
            report_type   = report_type,
            date_label    = date_label,
            now           = now,
            support_data  = ops["support_data"],
            failure_data  = ops["failure_data"],
            incident_data = ops["incident_data"],
            azure_data    = ops["azure_data"],
            ptc_data      = ops["ptc_data"],
            transactions  = wm["transactions"],
            wvs_queue     = wm["wvs_queue"],
            worker_stats  = wm["worker_stats"],
            trackers      = trackers,
            settings      = settings,
            from_date     = from_date,
            to_date       = to_date,
        )

        if fmt == "excel":
            data     = _re.build_excel_report(**kwargs)
            ts       = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"ops_{report_type}_{ts}.xlsx"
            return Response(
                data,
                mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers  = {"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        # HTML (also used for PDF — browser prints it)
        html = _re.build_html_report(**kwargs)
        if fmt == "pdf":
            # Return HTML with print-on-load for PDF save
            html = html.replace(
                "<script>",
                "<script>window.addEventListener('load',function(){setTimeout(function(){window.print();},800);});"
            )
        return Response(html, mimetype="text/html")

    except Exception as e:
        log.error(f"Report generation failed: {e}", exc_info=True)
        if request.get_json({}).get("format","") == "html":
            return Response(f"<h2>Report Error: {e}</h2>", mimetype="text/html")
        return jsonify({"success":False,"message":str(e)}), 500


# ── Digest routes (unchanged) ─────────────────────────────────────────────────
@operations_center_bp.route("/api/operations-center/prepare-digest/<digest_type>", methods=["POST"])
def prepare_digest(digest_type):
    if not _dg:
        return jsonify({"success":False,"message":"email_digest.py not found"}), 500
    if digest_type not in _dg.DIGEST_TYPES:
        return jsonify({"success":False,"message":f"Unknown type. Valid: {_dg.DIGEST_TYPES}"}), 400
    try:
        wm_types = ("wm_transactions","wvs_queue","worker_stats","weekly_summary")
        kwargs   = {**_ops_data(), **(_wm_data() if digest_type in wm_types else {})}
        return jsonify(_dg.prepare_daily_digest(digest_type, **kwargs))
    except Exception as e:
        return jsonify({"success":False,"message":str(e)}), 500


@operations_center_bp.route("/api/operations-center/prepare-all-digests", methods=["POST"])
def prepare_all_digests():
    if not _dg:
        return jsonify({"success":False,"message":"email_digest.py not found"}), 500
    try:
        kwargs  = {**_ops_data(), **_wm_data()}
        results = _dg.prepare_all_digests(**kwargs)
        alerts  = [r for r in results if r.get("is_alert")]
        return jsonify({
            "success"    : True,
            "total"      : len(results),
            "alerts"     : len(alerts),
            "alert_types": [r["digest_type"] for r in alerts],
            "results"    : results,
            "folder"     : str(_dg.DIGEST_BASE / datetime.now().strftime("%Y-%m-%d")),
        })
    except Exception as e:
        return jsonify({"success":False,"message":str(e)}), 500


@operations_center_bp.route("/api/operations-center/list-digests", methods=["GET"])
def list_digests():
    if not _dg: return jsonify({"success":False,"digests":[]})
    try:
        days = int(request.args.get("days",7))
        return jsonify({"success":True,"digests":_dg.list_saved_digests(days)})
    except Exception as e:
        return jsonify({"success":False,"message":str(e),"digests":[]})


@operations_center_bp.route("/api/operations-center/view-digest", methods=["GET"])
def view_digest():
    from flask import Response, abort
    from pathlib import Path
    html_file = request.args.get("file","")
    if not html_file: abort(400,"Missing file parameter")
    try:
        p = Path(html_file)
        if "email_digests" not in str(p): abort(403,"Access denied")
        return Response(p.read_text(encoding="utf-8"), mimetype="text/html")
    except FileNotFoundError:
        abort(404,"Digest file not found — regenerate the digest")
    except Exception as e:
        return f"<h2>Error: {e}</h2>", 500
