"""
log_analyzer/log_analyzer_routes.py
Endpoints:
  GET  /log-analyzer/              → main page
  POST /log-analyzer/save-summary  → save summary report locally + download
  GET  /api/help/log-analyzer      → help topics (registered via help bp)
"""

import os, datetime, json
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from common.logger import setup_logger

logger = setup_logger("log_analyzer")

log_analyzer_bp = Blueprint(
    "log_analyzer", __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/log_analyzer/static",
    url_prefix="/log-analyzer",
)

def _summary_dir():
    d = os.path.join(current_app.config.get("OUTPUT_FOLDER", "outputs"), "log_analyzer")
    os.makedirs(d, exist_ok=True)
    return d


@log_analyzer_bp.route("/")
def index():
    logger.info("Log Analyzer page loaded")
    return render_template("log_analyzer.html")


@log_analyzer_bp.route("/save-summary", methods=["POST"])
def save_summary():
    """
    Receive summary JSON from browser, write to outputs/log_analyzer/,
    and return the file as a download. All local — no external transmission.
    Body JSON: { metadata, level_counts, top_errors, top_loggers, top_users,
                  error_entries (up to 5000) }
    """
    try:
        body = request.get_json(force=True) or {}
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"log_summary_{ts}.txt"
        out_path = os.path.join(_summary_dir(), fname)

        lines = []
        lines.append("=" * 70)
        lines.append("  LOG ANALYZER — WINDCHILL LOG SUMMARY REPORT")
        lines.append(f"  Generated : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")

        meta = body.get("metadata", {})
        lines.append("FILE INFORMATION")
        lines.append("-" * 40)
        for k, v in meta.items():
            lines.append(f"  {str(k):<24}: {v}")
        lines.append("")

        counts = body.get("level_counts", {})
        if counts:
            lines.append("LOG LEVEL COUNTS")
            lines.append("-" * 40)
            for lv in ("FATAL", "ERROR", "WARN", "INFO", "DEBUG"):
                n = counts.get(lv, 0)
                lines.append(f"  {lv:<10}: {n:,}")
            lines.append("")

        for section_key, section_title in [
            ("top_errors",  "TOP ERROR PATTERNS (normalised)"),
            ("top_loggers", "TOP LOGGERS WITH ERRORS"),
            ("top_users",   "TOP USERS / SESSIONS IN ERRORS"),
        ]:
            items = body.get(section_key, [])
            if items:
                lines.append(section_title)
                lines.append("-" * 40)
                for item in items:
                    lines.append(f"  {item.get('count',''):>8}  {item.get('name','')}")
                lines.append("")

        entries = body.get("error_entries", [])
        if entries:
            lines.append(f"ERROR / FATAL ENTRIES ({len(entries):,} entries)")
            lines.append("-" * 40)
            hdr = f"  {'Timestamp':<24} {'Level':<7} {'Logger':<35} {'User':<12} Message"
            lines.append(hdr)
            lines.append("  " + "-" * 100)
            for e in entries[:5000]:
                ts_val  = str(e.get("ts", ""))[:23]
                lv_val  = str(e.get("level", ""))
                lg_val  = str(e.get("logger", ""))[:34]
                us_val  = str(e.get("user",  ""))[:11]
                ms_val  = str(e.get("message", ""))
                lines.append(f"  {ts_val:<24} {lv_val:<7} {lg_val:<35} {us_val:<12} {ms_val}")
                if e.get("extra"):
                    for xline in str(e["extra"]).splitlines()[:5]:
                        lines.append(f"  {'':>86}  {xline}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("  END OF REPORT  —  Data is confidential. Do not share externally.")
        lines.append("=" * 70)

        content = "\n".join(lines)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        logger.info("Log summary saved: %s (%d KB, %d entries)",
                    fname, len(content) // 1024, len(entries))
        return send_file(out_path, as_attachment=True, download_name=fname,
                         mimetype="text/plain")

    except Exception as exc:
        logger.error("save_summary error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500
