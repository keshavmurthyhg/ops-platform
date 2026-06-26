"""
OPS Platform — Combined App
==============================
Runs ALL modules together on a single Flask server.

    python app.py

Individual modules can also be run standalone:
    python bulk/app.py                  → port 5005
    python converter/app.py             → port 5004
    python dcn_analytics/app.py         → port 5009
    python dcn_sequence/app.py          → port 5008
    python excel_compare/app.py         → port 5006
    python excel_merge/app.py           → port 5007
    python operations_center/app.py     → port 5001
    python report/app.py                → port 5002
    python search/app.py                → port 5003
    python word_compare/app.py          → port 5010
    python windchill_monitoring/app.py  → port 5011
    python gz_reader/app.py             → port 5012
    python log_analyzer/app.py          → port 5013
"""

import os
from flask import Flask, render_template

# ── Common blueprint (shared layout + static assets) ──────────────
from common.common_blueprint import common_bp

# ── Module blueprints ─────────────────────────────────────────────
from bulk.bulk_routes import bulk_bp
from converter.converter_routes import converter_bp
from dcn_analytics.dcn_analytics_routes import dcn_analytics_bp
from dcn_sequence.dcn_sequence_routes import dcn_sequence_bp
from excel_compare.excel_compare_routes import excel_compare_bp
from excel_merge.excel_merge_routes import excel_merge_bp
from operations_center.operations_center_routes import operations_center_bp
from report.report_routes import report_bp
from search.search_routes import search_bp
from word_compare.word_compare_routes import word_compare_bp
from windchill_monitoring.windchill_routes import windchill_monitoring_bp
from gz_reader.gz_reader_routes import gz_reader_bp
from log_analyzer.log_analyzer_routes import log_analyzer_bp

# ── Help blueprints ───────────────────────────────────────────────
from help.dcn_analytics_help import dcn_help_bp
from help.ops_help import ops_help_bp
from help.wm_help import wm_help_bp
#from help.search_help import search_help_bp
from help.report_help import report_help_bp
from help.bulk_help import bulk_help_bp
from help.converter_help import converter_help_bp
from help.excel_merge_help import excel_merge_help_bp
from help.gz_reader_help    import gz_reader_help_bp
from help.log_analyzer_help import log_analyzer_help_bp

# ── App init ──────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "ops_platform_secret"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # disable static file cache — ensures JS/CSS changes load immediately

# ── Shared folders ────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# ── Register common blueprint first (provides layout + shared statics) ──
app.register_blueprint(common_bp)

# ── Register module blueprints ────────────────────────────────────
app.register_blueprint(bulk_bp)
app.register_blueprint(converter_bp)
app.register_blueprint(dcn_analytics_bp)
app.register_blueprint(dcn_sequence_bp)
app.register_blueprint(excel_compare_bp, url_prefix="")
app.register_blueprint(excel_merge_bp)
app.register_blueprint(operations_center_bp)
app.register_blueprint(report_bp)
app.register_blueprint(search_bp)
app.register_blueprint(word_compare_bp)
app.register_blueprint(windchill_monitoring_bp)
app.register_blueprint(gz_reader_bp)
app.register_blueprint(log_analyzer_bp)

# ── Help blueprints ───────────────────────────────────────────────
app.register_blueprint(dcn_help_bp)
app.register_blueprint(ops_help_bp)
app.register_blueprint(wm_help_bp)
#app.register_blueprint(search_help_bp)
app.register_blueprint(report_help_bp)
app.register_blueprint(bulk_help_bp)
app.register_blueprint(converter_help_bp)
app.register_blueprint(excel_merge_help_bp)
app.register_blueprint(gz_reader_help_bp)
app.register_blueprint(log_analyzer_help_bp)

# ── Home page ─────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


# ── Run ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
