"""
DCN Sequence — Standalone App
===============================
Run this file to launch ONLY the DCN Sequence module.

    python dcn_sequence/app.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, url_for
from dcn_sequence.dcn_sequence_routes import dcn_sequence_bp
from common.common_blueprint import common_bp

_HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = "dcn_sequence_secret"

UPLOAD_FOLDER = os.path.join(_HERE, "uploads")
OUTPUT_FOLDER = os.path.join(_HERE, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

app.register_blueprint(common_bp)
app.register_blueprint(dcn_sequence_bp)


@app.route("/")
def home_redirect():
    return redirect(url_for("dcn_sequence.dcn_sequence_page"))


if __name__ == "__main__":
    print("Running DCN Sequence as a Standalone Web Application...")
    app.run(debug=True, use_reloader=False, port=5008)
