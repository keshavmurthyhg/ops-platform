import os
from flask import Blueprint, render_template, request, jsonify

excel_compare_bp = Blueprint(
    "excel_compare",
    __name__,
    template_folder="templates",
    static_folder="static"
)

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "uploads"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@excel_compare_bp.route("/excel-compare")
def excel_compare_home():
    return render_template("excel_compare.html")


@excel_compare_bp.route("/upload-files", methods=["POST"])
def upload_files():
    old_file = request.files.get("old_file")
    new_file = request.files.get("new_file")

    if not old_file or not new_file:
        return jsonify({"status": "error", "message": "Both files required"})

    old_path = os.path.join(UPLOAD_FOLDER, old_file.filename)
    new_path = os.path.join(UPLOAD_FOLDER, new_file.filename)

    old_file.save(old_path)
    new_file.save(new_path)

    return jsonify({
        "status": "success",
        "message": "Files uploaded successfully"
    })


@excel_compare_bp.route("/run-compare", methods=["POST"])
def run_compare():
    return jsonify({
        "status": "success",
        "summary": {
            "rows_changed": 25,
            "columns_changed": 4,
            "new_rows": 12,
            "deleted_rows": 6
        }
    })


@excel_compare_bp.route("/download-report")
def download_report():
    return jsonify({
        "status": "success",
        "message": "Download triggered"
    })