"""
Word Compare — Standalone runner
  python word_compare/app.py   → http://localhost:5010
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, render_template
from common.common_blueprint import common_bp
from word_compare.word_compare_routes import word_compare_bp

app = Flask(__name__)
app.secret_key = "wc_secret"

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

app.register_blueprint(common_bp)
app.register_blueprint(word_compare_bp)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5010, use_reloader=False)
