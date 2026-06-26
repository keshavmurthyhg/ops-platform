import os
from flask import Flask, render_template
from common.common_blueprint import common_bp
from windchill_monitoring.windchill_routes import windchill_monitoring_bp

app = Flask(__name__)
app.secret_key = "windchill_standalone_secret"

# Shared folder support
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "outputs"

app.register_blueprint(common_bp)
app.register_blueprint(windchill_monitoring_bp)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5011, use_reloader=False)