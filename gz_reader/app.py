"""
gz_reader/app.py
=================
Standalone entry-point for the GZ Reader module.
Run this file to launch GZ Reader on its own:

    python gz_reader/app.py        → http://localhost:5012

For the full OPS Platform (all modules together) use the root app.py instead.
"""

import os
import sys

# Allow running from within the gz_reader/ folder OR from the repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flask import Flask, redirect
from common.common_blueprint import common_bp
from gz_reader.gz_reader_routes import gz_reader_bp

app = Flask(__name__)
app.secret_key = "gz_reader_standalone"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

UPLOAD_FOLDER = os.path.join(_HERE, "uploads")
OUTPUT_FOLDER = os.path.join(_HERE, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# register blueprints
app.register_blueprint(common_bp)
app.register_blueprint(gz_reader_bp)


@app.route("/")
def home():
    return redirect("/gz-reader/")


if __name__ == "__main__":
    app.run(debug=True, port=5012, use_reloader=False)
