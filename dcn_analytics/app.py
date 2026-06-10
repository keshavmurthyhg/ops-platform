"""
DCN Analytics — Standalone App
================================
Run this file to launch ONLY the DCN Analytics module.

    python dcn_analytics/app.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, url_for
from dcn_analytics.dcn_analytics_routes import dcn_analytics_bp
from common.common_blueprint import common_bp

_HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = "dcn_analytics_secret"

UPLOAD_FOLDER = os.path.join(_HERE, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.register_blueprint(common_bp)
app.register_blueprint(dcn_analytics_bp)


@app.route("/")
def home_redirect():
    return redirect(url_for("dcn_analytics.dcn_analytics_page"))


if __name__ == "__main__":
    print("Running DCN Analytics as a Standalone Web Application...")
    app.run(debug=True, use_reloader=False, port=5009)
