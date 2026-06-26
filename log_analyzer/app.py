"""
log_analyzer/app.py  —  standalone entry-point
Run:  python log_analyzer/app.py   →  http://localhost:5013
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flask import Flask, redirect
from common.common_blueprint import common_bp
from log_analyzer.log_analyzer_routes import log_analyzer_bp

app = Flask(__name__)
app.secret_key = "log_analyzer_standalone"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

app.register_blueprint(common_bp)
app.register_blueprint(log_analyzer_bp)

@app.route("/")
def home():
    return redirect("/log-analyzer/")

if __name__ == "__main__":
    app.run(debug=True, port=5013, use_reloader=False)
