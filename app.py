"""
OPS Platform — Combined App
==============================
Runs ALL modules together on a single Flask server.

    python app.py

Individual modules can be run standalone:
    python report/app.py            → port 5002
    python converter/app.py         → port 5004
    python search/app.py            → port 5003
    python bulk/app.py              → port 5005
    python excel_compare/app.py     → port 5006
    python excel_merge/app.py       → port 5007
    python dcn_sequence/app.py      → port 5008
    python dcn_analytics/app.py     → port 5009
    python operations_center/app.py → port 5001
"""

import os
from flask import Flask, render_template, send_from_directory, jsonify

# ── Blueprint imports ─────────────────────────────────────────────
from report.report_routes import report_bp
from converter.converter_routes import converter_bp
from search.search_routes import search_bp
from bulk.bulk_routes import bulk_bp
from excel_compare.excel_compare_routes import excel_compare_bp
from excel_merge.excel_merge_routes import excel_merge_bp
from dcn_sequence.dcn_sequence_routes import dcn_sequence_bp
from dcn_analytics.dcn_analytics_routes import dcn_analytics_bp
from operations_center.operations_center_routes import operations_center_bp

# ── Help Blueprint imports ─────────────────────────────────────────────
from help.dcn_analytics_help import dcn_help_bp

# ── App init ──────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "report_app_secret"

# ── Folders ───────────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# ── Register blueprints ───────────────────────────────────────────
app.register_blueprint(report_bp)
app.register_blueprint(converter_bp)
app.register_blueprint(search_bp)
app.register_blueprint(bulk_bp)
app.register_blueprint(excel_compare_bp, url_prefix="")
app.register_blueprint(excel_merge_bp)
app.register_blueprint(dcn_sequence_bp)
app.register_blueprint(dcn_analytics_bp)
app.register_blueprint(operations_center_bp)

# ── Help blueprints ───────────────────────────────────────────
app.register_blueprint(dcn_help_bp)

# ── Home page ─────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


# ── Compare page ──────────────────────────────────────────────────
@app.route("/compare")
def compare_page():
    return render_template("compare.html")


# ── Serve uploaded files ──────────────────────────────────────────
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)


# ── Run ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
