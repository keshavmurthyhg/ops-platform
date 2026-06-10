"""
Excel Compare — Standalone App
================================
Run this file to launch ONLY the Excel Compare module.

    python excel_compare/app.py
"""

import os
import sys

# Allow absolute imports from project root when run as standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, url_for
from excel_compare.excel_compare_routes import excel_compare_bp
from common.common_blueprint import common_bp

_HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = "standalone_secret"

UPLOAD_FOLDER = os.path.join(_HERE, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.register_blueprint(common_bp)
app.register_blueprint(excel_compare_bp, url_prefix="")


@app.route("/")
def home_redirect():
    return redirect(url_for("excel_compare.index"))


if __name__ == "__main__":
    print("Running Excel Compare as a Standalone Web Application...")
    app.run(debug=True, port=5006)
