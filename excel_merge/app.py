"""
Excel Merge — Standalone App
==============================
Run this file to launch ONLY the Excel Merge module.

    python excel_merge/app.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, send_from_directory
from excel_merge.excel_merge_routes import excel_merge_bp

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.secret_key = "excel_merge_secret"

UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads", "excel_merge")
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, "outputs", "excel_merge")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.register_blueprint(excel_merge_bp)


@app.route("/")
def home():
    return render_template("excel_merge.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(
        os.path.join(PROJECT_ROOT, "uploads"), filename
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5007)
