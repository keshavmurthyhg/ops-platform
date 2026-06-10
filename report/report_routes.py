from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    send_file,
    session
)

import os
import uuid
import zipfile
from io import BytesIO

from report.module.services.preview_service import get_preview_data
from common.ui.preview_ui import render_preview_html

from report.module.doc_generator import (
    generate_pdf,
    generate_word_doc_wrapper
)

report_bp = Blueprint(
    "report",
    __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/report/static"
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -----------------------------
# REPORT PAGE
# -----------------------------
@report_bp.route("/report")
def report_page():
    return render_template("report.html")


# -----------------------------
# LOAD PREVIEW
# -----------------------------
@report_bp.route("/get-rca-data", methods=["POST"])
def get_rca_data():
    try:
        data = request.get_json()

        incident_number = data.get("incident_number")
        priority = data.get("priority")
        vendor = data.get("vendor")

        if not incident_number:
            return jsonify({
                "error": "Incident number required"
            })

        incident_data = get_preview_data(
            incident_number
        )

        if not incident_data:
            return jsonify({
                "error": "Incident not found"
            })

        if priority and priority != "All":
            if incident_data.get("priority") != priority:
                return jsonify({
                    "error": "Priority filter mismatch"
                })

        if vendor and vendor != "All":
            if incident_data.get("vendor") != vendor:
                return jsonify({
                    "error": "Vendor filter mismatch"
                })

        preview_html = render_preview_html(
            incident_data
        )

        return jsonify({
            "preview_html": preview_html,
            "problem_statement":
                incident_data.get("problem", ""),
            "root_cause":
                incident_data.get("analysis", ""),
            "resolution":
                incident_data.get("resolution", "")
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        })

# -----------------------------
# UPDATE PREVIEW
# -----------------------------
@report_bp.route("/update-preview", methods=["POST"])
def update_preview():
    try:
        incident_number = request.form.get(
            "incident_number"
        )

        data = get_preview_data(
            incident_number
        )

        final_problem = request.form.get("problem")
        final_analysis = request.form.get("analysis")
        final_resolution = request.form.get("resolution")

        data["problem"] = final_problem
        data["analysis"] = final_analysis
        data["resolution"] = final_resolution

        saved_problem_images = []
        saved_root_images = []
        saved_resolution_images = []

        for field_name, target_list in [
            ("problem_images", saved_problem_images),
            ("root_images", saved_root_images),
            ("resolution_images", saved_resolution_images)
        ]:
            for file in request.files.getlist(field_name):
                if file.filename:
                    filename = f"{uuid.uuid4()}_{file.filename}"
                    path = os.path.join(
                        UPLOAD_FOLDER,
                        filename
                    )
                    file.save(path)
                    target_list.append(path)

        session["edited_data"] = {
            "incident_number": incident_number,
            "problem": final_problem,
            "analysis": final_analysis,
            "resolution": final_resolution,
            "problem_images": saved_problem_images,
            "root_images": saved_root_images,
            "resolution_images": saved_resolution_images
        }

        preview_html = render_preview_html(
            data,
            root=final_problem,
            l2=final_analysis,
            resolution=final_resolution,
            problem_images=saved_problem_images,
            root_images=saved_root_images,
            resolution_images=saved_resolution_images
        )

        return preview_html

    except Exception as e:
        return str(e)

# -----------------------------
# DOWNLOAD FILES
# -----------------------------
@report_bp.route("/download/word", methods=["POST"])
def download_word():
    return generate_download("word")


@report_bp.route("/download/pdf", methods=["POST"])
def download_pdf():
    return generate_download("pdf")


@report_bp.route("/download/zip", methods=["POST"])
def download_zip():
    return generate_download("zip")


def generate_download(file_type):
    incident_number = request.form.get(
        "incident_number"
    )

    problem = request.form.get(
        "problem_statement"
    )

    root = request.form.get(
        "root_cause"
    )

    resolution = request.form.get(
        "resolution"
    )

    edited_data = session.get(
        "edited_data",
        {}
    )

    incident_data = get_preview_data(
        incident_number
    )

    images = {
        "problem": edited_data.get(
            "problem_images", []
        ),
        "root": edited_data.get(
            "root_images", []
        ),
        "resolution": edited_data.get(
            "resolution_images", []
        )
    }

    if file_type == "word":
        file_bytes = generate_word_doc_wrapper(
            data=incident_data,
            root=problem,
            l2=root,
            res=resolution,
            images=images
        )

        return send_file(
            BytesIO(file_bytes),
            as_attachment=True,
            download_name=f"{incident_number}.docx"
        )

    elif file_type == "pdf":
        file_bytes = generate_pdf(
            data=incident_data,
            root=problem,
            l2=root,
            res=resolution,
            images=images
        )

        return send_file(
            BytesIO(file_bytes),
            as_attachment=True,
            download_name=f"{incident_number}.pdf"
        )

    elif file_type == "zip":
        pdf_bytes = generate_pdf(
            data=incident_data,
            root=problem,
            l2=root,
            res=resolution,
            images=images
        )

        word_bytes = generate_word_doc_wrapper(
            data=incident_data,
            root=problem,
            l2=root,
            res=resolution,
            images=images
        )

        zip_buffer = BytesIO()

        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as z:
            z.writestr(
                f"{incident_number}.pdf",
                pdf_bytes
            )

            z.writestr(
                f"{incident_number}.docx",
                word_bytes
            )

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=f"{incident_number}.zip"
        )


    