"""
Excel Compare — Standalone App
================================
Run this file to launch ONLY the Excel Compare module.

    python excel_compare/app.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, send_from_directory
from excel_compare.module.layout import excel_compare_bp

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.secret_key = "excel_compare_secret"

UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "excel_compare", "module", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.register_blueprint(excel_compare_bp, url_prefix="")


@app.route("/")
def home():
    return render_template("excel_compare/templates/excel_compare.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5006)
