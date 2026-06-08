import os
import re

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    send_file
)

# converter modules
from converter.module.converted_preview import (
    generate_slide_preview
)
from converter.module.converter import convert_ppt
from converter.module.ppt_metadata import (
    extract_slide1_metadata
)

# FIXED import
from report.module.services.preview_service import (
    get_preview_data
)
from common.ui.preview_ui import (
    render_preview_html
)

converter_bp = Blueprint(
    "converter",
    __name__
)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)

# temporary preview image store
preview_image_store = {}


# -----------------------------------
# fallback incident extraction
# -----------------------------------
def extract_full_incident_from_filename(
    filename
):
    """
    Example:
    INC108152642_report.pptx
    -> INC108152642
    """

    match = re.search(
        r"(INC\d{6,})",
        filename.upper()
    )

    if match:
        return match.group(1)

    return None


# -----------------------------------
# converter page
# -----------------------------------
@converter_bp.route("/converter")
def converter_page():
    return render_template(
        "converter.html"
    )


# -----------------------------------
# preview uploaded ppt
# -----------------------------------
@converter_bp.route(
    "/converter/preview",
    methods=["POST"]
)
def preview_converter():
    try:
        file = request.files.get(
            "ppt_file"
        )

        if not file:
            return jsonify({
                "error":
                "No PPT uploaded"
            }), 400

        ppt_path = os.path.join(
            UPLOAD_FOLDER,
            file.filename
        )

        file.save(ppt_path)

        print(
            f"PPT saved at: {ppt_path}"
        )

        # -----------------------------
        # extract incident
        # -----------------------------
        metadata = extract_slide1_metadata(
            ppt_path
        )

        incident_number = metadata.get(
            "incident"
        )

        print(
            f"Extracted incident: "
            f"{incident_number}"
        )

        # fallback from filename
        if (
            not incident_number
            or len(incident_number) < 8
        ):
            incident_number = (
                extract_full_incident_from_filename(
                    file.filename
                )
            )

            print(
                f"Fallback incident: "
                f"{incident_number}"
            )

        if not incident_number:
            return jsonify({
                "error":
                "Valid incident not found"
            }), 400

        # -----------------------------
        # fetch incident details
        # -----------------------------
        try:
            incident_data = (
                get_preview_data(
                    incident_number
                )
            )

        except Exception as e:
            print(
                f"Incident fetch failed: {e}"
            )

            incident_data = {
                "priority": "N/A",
                "description":
                "Unable to fetch incident"
            }

        # -----------------------------
        # preview html
        # -----------------------------
        preview_html = render_preview_html(
            incident_data
        )

        # -----------------------------
        # slide preview generation
        # -----------------------------
        slide_preview_result = (
            generate_slide_preview(
                ppt_path
            )
        )

        slide_images = []

        if slide_preview_result[
            "success"
        ]:
            for img in slide_preview_result[
                "images"
            ]:
                filename = img[
                    "filename"
                ]

                preview_image_store[
                    filename
                ] = img[
                    "filepath"
                ]

                slide_images.append({
                    "filename":
                    filename
                })

        else:
            print(
                "Slide preview failed:",
                slide_preview_result.get(
                    "error"
                )
            )

        return jsonify({
            "preview_html":
            preview_html,
            "slide_images":
            slide_images
        })

    except Exception as e:
        print(
            f"Preview error: {e}"
        )

        return jsonify({
            "error": str(e)
        }), 500


# -----------------------------------
# serve preview images
# -----------------------------------
@converter_bp.route(
    "/converter/slide-preview/<filename>"
)
def serve_slide_preview(
    filename
):
    file_path = (
        preview_image_store.get(
            filename
        )
    )

    if (
        file_path and
        os.path.exists(file_path)
    ):
        return send_file(
            file_path
        )

    return jsonify({
        "error":
        "Image not found"
    }), 404


# -----------------------------------
# convert preview slides
# -----------------------------------
@converter_bp.route(
    "/converter/convert",
    methods=["POST"]
)
def convert_ppt_route():
    try:
        ppt_file = request.files.get(
            "ppt_file"
        )

        if not ppt_file:
            return jsonify({
                "error":
                "No file uploaded"
            }), 400

        upload_path = os.path.join(
            UPLOAD_FOLDER,
            ppt_file.filename
        )

        ppt_file.save(
            upload_path
        )

        slide_preview_result = (
            generate_slide_preview(
                upload_path
            )
        )

        slide_images = []

        if slide_preview_result[
            "success"
        ]:
            for img in slide_preview_result[
                "images"
            ]:
                filename = img[
                    "filename"
                ]

                preview_image_store[
                    filename
                ] = img[
                    "filepath"
                ]

                slide_images.append({
                    "filename":
                    filename
                })

        return jsonify({
            "success": True,
            "slide_images":
            slide_images
        })

    except Exception as e:
        print(
            f"Convert error: {e}"
        )

        return jsonify({
            "error": str(e)
        }), 500


# -----------------------------------
# generate final doc
# -----------------------------------
@converter_bp.route(
    "/converter/generate",
    methods=["POST"]
)
def generate_converter():
    try:
        file = request.files.get(
            "ppt_file"
        )

        if not file:
            return jsonify({
                "error":
                "No PPT uploaded"
            }), 400

        filename = file.filename

        ppt_path = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        if not os.path.exists(
            ppt_path
        ):
            file.save(
                ppt_path
            )


        metadata = extract_slide1_metadata(
            ppt_path
        )

        incident_number = metadata.get(
            "incident"
        )

        if not incident_number:
            incident_number = (
                extract_full_incident_from_filename(
                    file.filename
                )
            )

        incident_data = get_preview_data(
            incident_number
        )

        output_file = convert_ppt(
            ppt_path,
            OUTPUT_FOLDER,
            incident_data
        )

        return jsonify({
            "filename":
            os.path.basename(
                output_file
            )
        })

    except Exception as e:
        print(
            f"Generate error: {e}"
        )

        return jsonify({
            "error": str(e)
        }), 500


# -----------------------------------
# download generated file
# -----------------------------------
@converter_bp.route(
    "/converter/download/<filename>"
)
def download_converter(
    filename
):
    try:
        path = os.path.join(
            OUTPUT_FOLDER,
            filename
        )

        if not os.path.exists(
            path
        ):
            return jsonify({
                "error":
                "File not found"
            }), 404

        return send_file(
            path,
            as_attachment=True
        )

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500