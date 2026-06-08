"""
DCN Analytics — Standalone App
================================
Run this file to launch ONLY the DCN Analytics module.

    python dcn_analytics/app.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, send_from_directory
from dcn_analytics.dcn_analytics_routes import dcn_analytics_bp

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.secret_key = "dcn_analytics_secret"

UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.register_blueprint(dcn_analytics_bp)


@app.route("/")
def home():
    return render_template("dcn_analytics.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5009)
