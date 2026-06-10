from flask import (

    Blueprint,
    render_template,
    request,
    jsonify,
    send_from_directory

)

import os

from dcn_sequence.module.services.dcn_sequence_service import (
    process_dcn_sequence
)


# =========================================================
# BLUEPRINT
# =========================================================
dcn_sequence_bp = Blueprint(
    "dcn_sequence",
    __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/dcn_sequence/static"
)


# =========================================================
# FOLDERS
# =========================================================
UPLOAD_DIR = "uploads"

OUTPUT_DIR = os.path.join(
    "outputs",
    "dcn_sequence"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# =========================================================
# PAGE
# =========================================================
@dcn_sequence_bp.route("/dcn-sequence")
def dcn_sequence_page():

    return render_template(
        "dcn_sequence.html"
    )


# =========================================================
# PROCESS API
# =========================================================
@dcn_sequence_bp.route(
    "/api/dcn-sequence/process",
    methods=["POST"]
)
def process_sequence():

    try:

        if "file" not in request.files:

            return jsonify({

                "success": False,

                "message":
                    "No file uploaded"

            })


        file = request.files["file"]


        if file.filename == "":

            return jsonify({

                "success": False,

                "message":
                    "Empty filename"

            })


        upload_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        file.save(upload_path)


        result = process_dcn_sequence(
            upload_path
        )

        return jsonify(result)

    except Exception as error:

        return jsonify({

            "success": False,

            "message": str(error)

        })


# =========================================================
# DOWNLOAD API
# =========================================================
@dcn_sequence_bp.route(
    "/api/dcn-sequence/download/<filename>"
)
def download_output(filename):

    return send_from_directory(

        OUTPUT_DIR,
        filename,
        as_attachment=True

    )