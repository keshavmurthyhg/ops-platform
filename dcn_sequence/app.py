"""
DCN Sequence — Standalone App
===============================
Run this file to launch ONLY the DCN Sequence module.

    python dcn_sequence/app.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, send_from_directory
from dcn_sequence.dcn_sequence_routes import dcn_sequence_bp

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.secret_key = "dcn_sequence_secret"

UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, "outputs", "dcn_sequence")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.register_blueprint(dcn_sequence_bp)


@app.route("/")
def home():
    return render_template("dcn_sequence.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5008)
