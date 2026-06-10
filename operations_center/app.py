"""
Operations Center — Standalone App
====================================
Run this file to launch ONLY the Operations Center module.

    python operations_center/app.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, url_for
from operations_center.operations_center_routes import operations_center_bp
from common.common_blueprint import common_bp

_HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = "ops_center_secret"

UPLOAD_FOLDER = os.path.join(_HERE, "uploads")
OUTPUT_FOLDER = os.path.join(_HERE, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

app.register_blueprint(common_bp)
app.register_blueprint(operations_center_bp)


@app.route("/")
def home_redirect():
    return redirect(url_for("operations_center.operations_center"))


if __name__ == "__main__":
    print("Running Operations Center as a Standalone Web Application...")
    app.run(debug=True, use_reloader=False, port=5001)
