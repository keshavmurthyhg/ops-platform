"""
Search — Standalone App
========================
Run this file to launch ONLY the Search module.

    python search/app.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, url_for
from search.search_routes import search_bp
from common.common_blueprint import common_bp

_HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = "search_app_secret"

UPLOAD_FOLDER = os.path.join(_HERE, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.register_blueprint(common_bp)
app.register_blueprint(search_bp)


@app.route("/")
def home_redirect():
    return redirect(url_for("search.search_page"))


if __name__ == "__main__":
    print("Running Search as a Standalone Web Application...")
    app.run(debug=True, use_reloader=False, port=5003)
