"""
Operations Center — Standalone App
====================================
Run this file to launch ONLY the Operations Center module.

    python operations_center/app.py

Or from the project root:

    python -m operations_center.app
"""

import sys
import os

# ── make project root importable ──────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, send_from_directory
from operations_center.operations_center_routes import operations_center_bp

# ── App init ──────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.secret_key = "ops_center_secret"

# ── Folders ───────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# ── Blueprint ─────────────────────────────────────────────────────
app.register_blueprint(operations_center_bp)


# ── Home ──────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("operations_center.html")


# ── Serve uploads ─────────────────────────────────────────────────
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ── Run ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5001)
