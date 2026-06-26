from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    send_file,
    send_from_directory,
    session
)

import os
import uuid
import zipfile
import logging

from io import BytesIO
from logging.handlers import RotatingFileHandler

from report.module.services.preview_service import get_preview_data
from common.ui.preview_ui import render_preview_html

from report.module.doc_generator import (
    generate_pdf,
    generate_word_doc_wrapper
)


# ─────────────────────────────────────────────────────────────────────────────
# LOGGER SETUP
# ─────────────────────────────────────────────────────────────────────────────

def _setup_logger():
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "report.log")

    logger = logging.getLogger("report")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=5
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(handler)

    return logger

logger = _setup_logger()


# ─────────────────────────────────────────────────────────────────────────────
# BLUEPRINT
# ─────────────────────────────────────────────────────────────────────────────

report_bp = Blueprint(
    "report",
    __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/report/static"
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/report")
def report_page():
    logger.info("Report page loaded")
    return render_template("report.html")


@report_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(os.path.abspath(UPLOAD_FOLDER), filename)


@report_bp.route("/get-rca-data", methods=["POST"])
def get_rca_data():
    try:
        data            = request.get_json()
        incident_number = data.get("incident_number")
        priority        = data.get("priority")
        vendor          = data.get("vendor")

        if not incident_number:
            return jsonify({"error": "Incident number required"})

        logger.info("=" * 60)
        logger.info("PREVIEW REQUESTED: %s", incident_number)

        incident_data = get_preview_data(incident_number)

        if not incident_data:
            logger.warning("Incident not found: %s", incident_number)
            return jsonify({"error": "Incident not found"})

        if priority and priority != "All":
            if incident_data.get("priority") != priority:
                logger.warning("Priority filter mismatch: %s", incident_number)
                return jsonify({"error": "Priority filter mismatch"})

        if vendor and vendor != "All":
            if incident_data.get("vendor") != vendor:
                logger.warning("Vendor filter mismatch: %s", incident_number)
                return jsonify({"error": "Vendor filter mismatch"})

        # Log which RCA fields were found (mirrors converter prefill logging)
        has_problem  = bool(incident_data.get("problem", "").strip())
        has_analysis = bool(incident_data.get("analysis", "").strip())
        has_res      = bool(incident_data.get("resolution", "").strip())
        logger.info("  RCA fields: problem=%s  analysis=%s  resolution=%s",
                    has_problem, has_analysis, has_res)
        logger.info("  Priority: %s  Assigned to: %s",
                    incident_data.get("priority", "-"),
                    incident_data.get("assigned_to", "-"))

        preview_html = render_preview_html(
            incident_data,
            references=incident_data.get("references", []),
        )

        logger.info("PREVIEW GENERATED: %s", incident_number)
        logger.info("=" * 60)

        return jsonify({
            "preview_html":      preview_html,
            "problem_statement": incident_data.get("problem",          ""),
            "root_cause":        incident_data.get("analysis",         ""),
            "resolution":        incident_data.get("resolution",       ""),
            "references_text":   incident_data.get("references_text",  ""),
            "references_list":   incident_data.get("references",       []),
        })

    except Exception as e:
        logger.error("Preview failed: %s", str(e))
        return jsonify({"error": str(e)})


@report_bp.route("/update-preview", methods=["POST"])
def update_preview():
    try:
        from report.module.services.references_service import extract_references

        incident_number  = request.form.get("incident_number")
        data             = get_preview_data(incident_number)
        final_problem    = request.form.get("problem",    "")
        final_analysis   = request.form.get("analysis",  "")
        final_resolution = request.form.get("resolution","")

        data["problem"]    = final_problem
        data["analysis"]   = final_analysis
        data["resolution"] = final_resolution

        saved_problem_images    = []
        saved_root_images       = []
        saved_resolution_images = []

        for field_name, target_list in [
            ("problem_images",    saved_problem_images),
            ("root_images",       saved_root_images),
            ("resolution_images", saved_resolution_images),
        ]:
            for file in request.files.getlist(field_name):
                if file.filename:
                    filename = f"{uuid.uuid4()}_{file.filename}"
                    path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(path)
                    target_list.append(path)

        session["edited_data"] = {
            "incident_number":  incident_number,
            "problem":          final_problem,
            "analysis":         final_analysis,
            "resolution":       final_resolution,
            "problem_images":   saved_problem_images,
            "root_images":      saved_root_images,
            "resolution_images":saved_resolution_images,
        }

        # Use user-edited references if sent and non-empty (preserves environment badge
        # changes). If empty or missing, use refs already in prepared data so the
        # references table never disappears after Update Preview.
        import json as _json
        refs = None
        refs_json_raw = request.form.get("references_json", "")
        if refs_json_raw:
            try:
                parsed = _json.loads(refs_json_raw)
                if parsed:           # only use client list when it actually has items
                    refs = parsed
                    logger.info("  references_json received: %d refs, envs=%s",
                                len(refs),
                                [r.get("environment") for r in refs])
            except Exception as e:
                logger.warning("  references_json parse error: %s", e)
        if refs is None:
            refs = data.get("references") or extract_references(data)
            logger.info("  references fallback: %d refs", len(refs))

        preview_html = render_preview_html(
            data,
            root=final_problem,
            l2=final_analysis,
            resolution=final_resolution,
            problem_images=saved_problem_images,
            root_images=saved_root_images,
            resolution_images=saved_resolution_images,
            references=refs,
        )

        logger.info("UPDATE PREVIEW: %s", incident_number)
        logger.info("  problem text     : %d chars", len(final_problem))
        logger.info("  analysis text    : %d chars", len(final_analysis))
        logger.info("  resolution text  : %d chars", len(final_resolution))
        logger.info("  images p=%d r=%d res=%d",
                    len(saved_problem_images), len(saved_root_images),
                    len(saved_resolution_images))
        return preview_html

    except Exception as e:
        logger.error("UPDATE PREVIEW FAILED: %s", str(e))
        return str(e)


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
    import json
    incident_number = request.form.get("incident_number")
    problem         = request.form.get("problem_statement")
    root            = request.form.get("root_cause")
    resolution      = request.form.get("resolution")
    images_mode     = request.form.get("images_in_doc", "all")
    edited_data     = session.get("edited_data", {})
    incident_data   = get_preview_data(incident_number)

    # Merge client-side references (with user-edited environments) if provided
    try:
        client_refs_raw = request.form.get("references_json", "")
        if client_refs_raw:
            client_refs = json.loads(client_refs_raw)
            if client_refs:
                incident_data["references"] = client_refs
    except Exception:
        pass

    images = {
        "problem":    edited_data.get("problem_images",    []),
        "root":       edited_data.get("root_images",       []),
        "resolution": edited_data.get("resolution_images", []),
    } if images_mode != "none" else {"problem":[], "root":[], "resolution":[]}

    logger.info("-" * 60)
    logger.info("DOWNLOAD REQUESTED: %s  format=%s  images_mode=%s",
                incident_number, file_type.upper(), images_mode)
    total_imgs = sum(len(v) for v in images.values())
    logger.info("  Images: problem=%d  root=%d  resolution=%d  (total=%d, mode=%s)",
                len(images["problem"]), len(images["root"]),
                len(images["resolution"]), total_imgs, images_mode)

    if file_type == "word":
        file_bytes = generate_word_doc_wrapper(
            data=incident_data, root=problem, l2=root, res=resolution, images=images
        )
        size_kb = len(file_bytes) // 1024
        logger.info("WORD READY: %s.docx  (%d KB)", incident_number, size_kb)
        return send_file(BytesIO(file_bytes), as_attachment=True,
                         download_name=f"{incident_number}.docx")

    elif file_type == "pdf":
        file_bytes = generate_pdf(
            data=incident_data, root=problem, l2=root, res=resolution, images=images
        )
        size_kb = len(file_bytes) // 1024
        logger.info("PDF READY: %s.pdf  (%d KB)", incident_number, size_kb)
        return send_file(BytesIO(file_bytes), as_attachment=True,
                         download_name=f"{incident_number}.pdf")

    elif file_type == "zip":
        pdf_bytes  = generate_pdf(data=incident_data, root=problem, l2=root, res=resolution, images=images)
        word_bytes = generate_word_doc_wrapper(data=incident_data, root=problem, l2=root, res=resolution, images=images)
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{incident_number}.pdf",  pdf_bytes)
            z.writestr(f"{incident_number}.docx", word_bytes)
        zip_buffer.seek(0)
        total_kb = (len(pdf_bytes) + len(word_bytes)) // 1024
        logger.info("ZIP READY: %s.zip  (%d KB)", incident_number, total_kb)
        return send_file(zip_buffer, as_attachment=True, download_name=f"{incident_number}.zip")


# ─────────────────────────────────────────────────────────────────────────────
# PPT EXPORT — builds RCA PowerPoint from form data
# ─────────────────────────────────────────────────────────────────────────────

@report_bp.route("/download/ppt", methods=["POST"])
def download_ppt():
    try:
        import json
        from datetime import datetime
        from report.module.ppt_creator import create_rca_pptx

        incident_number = request.form.get("incident_number", "INC000000")
        incident_raw    = request.form.get("incident_data", "{}")
        problem_text    = request.form.get("problem",    "")
        root_text       = request.form.get("root_cause", "")
        res_text        = request.form.get("resolution", "")
        # Always fetch fresh incident data from server — the client-side
        # currentIncidentData dict may be partial (only has _refs key)
        try:
            incident_data = get_preview_data(incident_number)
        except Exception:
            incident_data = {}

        # Merge client-side references (which may have user-edited environments)
        # into the server data, so documents reflect the user's changes
        try:
            client_data = json.loads(incident_raw)
            client_refs = client_data.get("_refs") or []
            if client_refs:
                incident_data["references"] = client_refs
        except Exception:
            pass

        # Also accept direct references_json field (preferred — always up to date)
        try:
            refs_json_raw = request.form.get("references_json", "")
            if refs_json_raw:
                direct_refs = json.loads(refs_json_raw)
                if direct_refs:
                    incident_data["references"] = direct_refs
        except Exception:
            pass

        logger.info("=" * 60)
        logger.info("PPT EXPORT: %s", incident_number)
        logger.info("  problem    : %d chars", len(problem_text))
        logger.info("  root_cause : %d chars", len(root_text))
        logger.info("  resolution : %d chars", len(res_text))

        # Save uploaded images
        def _save_images(field):
            paths = []
            for f in request.files.getlist(field):
                if f.filename:
                    safe = f"{uuid.uuid4()}_{f.filename}"
                    path = os.path.join(UPLOAD_FOLDER, safe)
                    f.save(path)
                    paths.append(path)
            return paths

        rca_image_paths = {
            "problem":    _save_images("problem_images"),
            "rootcause":  _save_images("root_images"),
            "resolution": _save_images("resolution_images"),
        }

        logger.info("  Images: problem=%d root=%d resolution=%d",
                    len(rca_image_paths["problem"]),
                    len(rca_image_paths["rootcause"]),
                    len(rca_image_paths["resolution"]))

        date_str  = datetime.now().strftime("%d%b%Y").upper()
        out_name  = f"{incident_number}_RCA_{date_str}.pptx"
        out_dir   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path  = os.path.join(out_dir, out_name)

        create_rca_pptx(
            incident_data   = incident_data,
            incident_number = incident_number,
            rca_text        = {"problem": problem_text, "rootcause": root_text, "resolution": res_text},
            rca_image_paths = rca_image_paths,
            output_path     = out_path,
        )

        size_kb = os.path.getsize(out_path) // 1024
        logger.info("PPT SAVED: %s (%d KB)", out_name, size_kb)
        return jsonify({"filename": out_name, "size_kb": size_kb})

    except Exception as e:
        logger.error("PPT export failed: %s", str(e))
        return jsonify({"error": str(e)}), 500


@report_bp.route("/report/download-pptx/<filename>")
def report_download_pptx(filename):
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outputs")
    path    = os.path.join(out_dir, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    logger.info("PPTX DOWNLOAD: %s", filename)
    return send_file(path, as_attachment=True)
