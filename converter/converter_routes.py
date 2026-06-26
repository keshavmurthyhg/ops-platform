import os
import re
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file

from converter.module.converted_preview import generate_slide_preview
from converter.module.converter import convert_ppt
from converter.module.ppt_metadata import extract_slide1_metadata
from converter.module.doc_to_pdf import doc_to_pdf
from converter.module.ppt_creator import create_rca_pptx

# Report module — shared word/pdf generators
from report.module.doc_generator import generate_word_doc_wrapper, generate_pdf, prepare_data
from report.module.services.preview_service import get_preview_data

from common.ui.preview_ui import render_preview_html
from common.logger import setup_logger

logger = setup_logger("converter")

converter_bp = Blueprint(
    "converter", __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/converter/static"
)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
PREVIEW_FOLDER = os.path.join("outputs", "preview_images")

os.makedirs(UPLOAD_FOLDER,  exist_ok=True)
os.makedirs(OUTPUT_FOLDER,  exist_ok=True)
os.makedirs(PREVIEW_FOLDER, exist_ok=True)

# In-memory store: filename → absolute path
preview_image_store = {}

# In-memory: incident_number → prepared incident_data (so generate can reuse)
_incident_cache = {}


def extract_full_incident_from_filename(filename):
    match = re.search(r"(INC\d{6,})", filename.upper())
    return match.group(1) if match else None


def _log_preferences(label, form):
    logger.info("-" * 60)
    logger.info("USER PREFERENCES — %s", label)
    logger.info("  Skip title slides : %s", form.get("skip_title_slides", "true"))
    logger.info("  Skip dividers     : %s", form.get("skip_dividers",     "true"))
    logger.info("  Slide DPI         : %s", form.get("dpi",               "200"))
    logger.info("  Output format     : %s", form.get("format",            "word"))
    logger.info("  Images in doc     : %s", form.get("images_in_doc",     "all"))
    logger.info("-" * 60)


def _resolve_img_path(fn):
    """Return absolute path for a preview image filename."""
    p = preview_image_store.get(fn)
    if p and os.path.exists(p):
        return p
    p2 = os.path.join(PREVIEW_FOLDER, fn)
    if os.path.exists(p2):
        return p2
    return None


# ═══════════════════════════════════════════════════════════════════
# CONVERTER PAGE
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter")
def converter_page():
    logger.info("Converter page loaded")
    return render_template("converter.html")


# ═══════════════════════════════════════════════════════════════════
# PREVIEW — fetch incident + generate slide thumbnails
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/preview", methods=["POST"])
def preview_converter():
    try:
        file = request.files.get("ppt_file")
        if not file:
            return jsonify({"error": "No PPT uploaded"}), 400

        _log_preferences("PREVIEW", request.form)
        logger.info("FILE: %s", file.filename)

        ppt_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(ppt_path)

        # ── Incident detection ─────────────────────────────────────────
        metadata        = extract_slide1_metadata(ppt_path)
        incident_number = metadata.get("incident")
        if not incident_number or len(incident_number) < 8:
            incident_number = extract_full_incident_from_filename(file.filename)
        if not incident_number:
            return jsonify({"error": "Valid incident not found in filename or slide 1"}), 400

        logger.info("Incident: %s", incident_number)

        # ── Fetch + prepare incident data (includes build_rca) ─────────
        try:
            incident_data = get_preview_data(incident_number)
            _incident_cache[incident_number] = incident_data
        except Exception as e:
            logger.warning("Incident fetch failed: %s", e)
            incident_data = {}

        # ── Build preview HTML ─────────────────────────────────────────
        preview_html = render_preview_html(incident_data)

        # ── RCA prefill — use keys produced by prepare_data / build_rca ─
        # prepare_data sets: problem, analysis, resolution
        rca_prefill = {}
        for ui_key, data_keys in [
            ("problem",    ["problem", "problem_statement", "PROBLEM STATEMENT"]),
            ("rootcause",  ["analysis", "root_cause", "ROOT CAUSE", "Root Cause"]),
            ("resolution", ["resolution", "RESOLUTION"]),
        ]:
            for dk in data_keys:
                val = incident_data.get(dk, "")
                if val and str(val).strip() not in ("-", "", "None", "nan"):
                    rca_prefill[ui_key] = str(val).strip()
                    break

        logger.info("RCA PREFILL: problem=%s rootcause=%s resolution=%s",
                    bool(rca_prefill.get("problem")),
                    bool(rca_prefill.get("rootcause")),
                    bool(rca_prefill.get("resolution")))

        # ── Slide preview images ────────────────────────────────────────
        skip_titles = request.form.get("skip_title_slides", "true").lower() != "false"
        result      = generate_slide_preview(ppt_path, skip_title_slides=skip_titles)
        slide_images = []
        if result["success"]:
            # Clear stale entries — new conversion replaces all previous slides
            preview_image_store.clear()
            for img in result["images"]:
                preview_image_store[img["filename"]] = img["filepath"]
                slide_images.append({"filename": img["filename"]})
            logger.info("PREVIEW_IMAGE_STORE cleared and refreshed: %d entries",
                        len(preview_image_store))
        else:
            logger.warning("Slide preview failed: %s", result.get("error"))

        logger.info("PREVIEW COMPLETE: %d slide(s) — auto-conversion will follow", len(slide_images))
        return jsonify({
            "preview_html":    preview_html,
            "slide_images":    slide_images,
            "rca_prefill":     rca_prefill,
            "incident_number": incident_number,
            "incident_data":   incident_data,   # sent to JS for PPT export
        })

    except Exception as e:
        logger.error("Preview error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# SERVE SLIDE PREVIEW IMAGE
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/slide-preview/<filename>")
def serve_slide_preview(filename):
    path = _resolve_img_path(filename)
    if path:
        return send_file(path)
    return jsonify({"error": "Image not found"}), 404


# ═══════════════════════════════════════════════════════════════════
# SERVE UPLOADED PREVIEW FILES — render_preview_html uses /uploads/<file>
# Must mirror the report module's /uploads/<filename> route
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    from flask import send_from_directory
    # Check PREVIEW_FOLDER first, then UPLOAD_FOLDER
    for folder in [PREVIEW_FOLDER, UPLOAD_FOLDER]:
        path = os.path.join(os.path.abspath(folder), filename)
        if os.path.exists(path):
            logger.debug("Serving upload: %s", path)
            return send_from_directory(os.path.abspath(folder), filename)
    return jsonify({"error": "File not found"}), 404


# ═══════════════════════════════════════════════════════════════════
# UPDATE PREVIEW — refresh incident preview panel with edited RCA + images
# Mirror of report module /update-preview
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/update-preview", methods=["POST"])
def update_preview():
    """
    Refresh the incident preview panel with edited RCA text + assigned slide images.
    The JS sends each zone's images as blobs under problem_images / root_images / resolution_images.
    Mirrors report module /update-preview exactly.
    """
    import uuid as _uuid
    try:
        incident_number  = request.form.get("incident_number")
        final_problem    = request.form.get("problem",    "")
        final_analysis   = request.form.get("analysis",   "")
        final_resolution = request.form.get("resolution", "")

        logger.info("=" * 60)
        logger.info("UPDATE PREVIEW: %s", incident_number)
        logger.info("  problem    : %d chars", len(final_problem))
        logger.info("  analysis   : %d chars", len(final_analysis))
        logger.info("  resolution : %d chars", len(final_resolution))

        # Use cached incident data
        incident_data = _incident_cache.get(incident_number, {})
        if not incident_data and incident_number:
            try:
                incident_data = get_preview_data(incident_number)
                _incident_cache[incident_number] = incident_data
            except Exception:
                incident_data = {}

        # Merge edited RCA text
        incident_data = dict(incident_data)
        incident_data["problem"]    = final_problem
        incident_data["analysis"]   = final_analysis
        incident_data["resolution"] = final_resolution

        # Save uploaded section image blobs (sent from JS as File objects)
        saved_problem_images    = []
        saved_root_images       = []
        saved_resolution_images = []

        for field, target in [
            ("problem_images",    saved_problem_images),
            ("root_images",       saved_root_images),
            ("resolution_images", saved_resolution_images),
        ]:
            files = request.files.getlist(field)
            logger.info("  %s: %d file(s) received", field, len(files))
            for img_file in files:
                if img_file and img_file.filename:
                    # Save to UPLOAD_FOLDER — render_preview_html generates
                    # <img src="/uploads/filename"> so we need them served there
                    safe_name = f"prev_{_uuid.uuid4().hex[:8]}_{img_file.filename}"
                    path      = os.path.join(UPLOAD_FOLDER, safe_name)
                    img_file.save(path)
                    target.append(path)
                    preview_image_store[safe_name] = path
                    logger.info("    saved: %s → %s", img_file.filename, path)

        logger.info("  problem_images   : %d", len(saved_problem_images))
        logger.info("  root_images      : %d", len(saved_root_images))
        logger.info("  resolution_images: %d", len(saved_resolution_images))

        preview_html = render_preview_html(
            incident_data,
            root=final_problem,
            l2=final_analysis,
            resolution=final_resolution,
            problem_images=saved_problem_images,
            root_images=saved_root_images,
            resolution_images=saved_resolution_images,
        )

        logger.info("UPDATE PREVIEW complete: %s", incident_number)
        return preview_html

    except Exception as e:
        logger.error("Update preview error: %s", e)
        return f"<p class='preview-placeholder'>Preview update failed: {e}</p>"


# ═══════════════════════════════════════════════════════════════════
# CLEAR SERVER-SIDE CACHE (called on Clear Workspace from JS)
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/clear-cache", methods=["POST"])
def clear_cache():
    """Clear the server-side preview image store and preview folder."""
    try:
        n = len(preview_image_store)
        preview_image_store.clear()
        # Remove old preview images from disk
        cleared = 0
        for f in os.listdir(PREVIEW_FOLDER):
            try:
                os.remove(os.path.join(PREVIEW_FOLDER, f))
                cleared += 1
            except Exception:
                pass
        logger.info("CACHE CLEARED: %d store entries, %d files removed", n, cleared)
        return jsonify({"cleared": True, "entries": n, "files": cleared})
    except Exception as e:
        logger.error("Cache clear error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# CONVERT PPT SLIDES (re-render with current options)
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/convert", methods=["POST"])
def convert_ppt_route():
    try:
        ppt_file = request.files.get("ppt_file")
        if not ppt_file:
            return jsonify({"error": "No file uploaded"}), 400

        _log_preferences("CONVERT", request.form)
        upload_path = os.path.join(UPLOAD_FOLDER, ppt_file.filename)
        ppt_file.save(upload_path)

        skip_titles = request.form.get("skip_title_slides", "true").lower() != "false"
        result      = generate_slide_preview(upload_path, skip_title_slides=skip_titles)
        slide_images = []
        if result["success"]:
            # Clear stale entries — new conversion replaces all previous slides
            preview_image_store.clear()
            for img in result["images"]:
                preview_image_store[img["filename"]] = img["filepath"]
                slide_images.append({"filename": img["filename"]})
            logger.info("PREVIEW_IMAGE_STORE cleared and refreshed: %d entries",
                        len(preview_image_store))

        logger.info("CONVERT COMPLETE: %d slide(s)", len(slide_images))
        return jsonify({"success": True, "slide_images": slide_images})

    except Exception as e:
        logger.error("Convert error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# GENERATE STANDARD REPORT (Word / PDF / Both)
# Uses the same report module word_renderer as Report + Bulk
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/generate", methods=["POST"])
def generate_converter():
    try:
        file        = request.files.get("ppt_file")
        format_type = request.form.get("format", "word")
        if not file:
            return jsonify({"error": "No PPT uploaded"}), 400

        _log_preferences("GENERATE", request.form)
        filename = file.filename
        ppt_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(ppt_path):
            file.save(ppt_path)

        metadata        = extract_slide1_metadata(ppt_path)
        incident_number = metadata.get("incident") or extract_full_incident_from_filename(filename)

        logger.info("GENERATING: %s format=%s", incident_number, format_type.upper())

        # Use cached or freshly fetched incident data
        incident_data = _incident_cache.get(incident_number)
        if not incident_data:
            incident_data = get_preview_data(incident_number)
            _incident_cache[incident_number] = incident_data

        # Generate using the shared report word renderer
        # ppt_data is passed so PPT slides are appended at the end
        date_str  = datetime.now().strftime("%d%b%Y").upper()
        base_name = os.path.splitext(filename)[0]
        docx_name = f"{base_name}.docx"
        docx_path = os.path.join(OUTPUT_FOLDER, docx_name)

        word_bytes = generate_word_doc_wrapper(
            data     = incident_data,
            ppt_data = ppt_path,
        )
        with open(docx_path, "wb") as f_out:
            f_out.write(word_bytes)

        docx_kb = os.path.getsize(docx_path) // 1024
        logger.info("DOCX CREATED: %s  (%d KB)", docx_name, docx_kb)

        result = {"docx_filename": docx_name, "filename": docx_name}

        if format_type in ("pdf", "both"):
            try:
                pdf_path = doc_to_pdf(docx_path, OUTPUT_FOLDER)
                result["pdf_filename"] = os.path.basename(pdf_path)
                logger.info("PDF CREATED: %s", result["pdf_filename"])
            except Exception as pdf_err:
                logger.error("PDF failed: %s", pdf_err)
                result["pdf_error"] = str(pdf_err)
                if format_type == "pdf":
                    return jsonify({"error": f"PDF failed: {pdf_err}"}), 500

        return jsonify(result)

    except Exception as e:
        logger.error("Generate error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# GENERATE RCA REPORT (Word / PDF / Both)
# Uses the same report word_renderer, passes images per section
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/generate-rca", methods=["POST"])
def generate_rca_converter():
    try:
        file            = request.files.get("ppt_file")
        format_type     = request.form.get("format",           "word")
        rca_raw         = request.form.get("rca_assignments",  "{}")
        text_raw        = request.form.get("rca_text",         "{}")
        images_mode     = request.form.get("images_in_doc",    "all")
        all_slides_raw  = request.form.get("all_slide_filenames", "[]")

        if not file:
            return jsonify({"error": "No PPT uploaded"}), 400

        _log_preferences("GENERATE-RCA", request.form)

        assignments    = json.loads(rca_raw)
        rca_text       = json.loads(text_raw)
        all_slide_fns  = json.loads(all_slides_raw)

        logger.info("=" * 60)
        logger.info("RCA DOCUMENT GENERATION")
        for key in ("problem", "rootcause", "resolution"):
            imgs = assignments.get(key, [])
            txt  = (rca_text.get(key) or "").strip()
            logger.info("  %-12s: %d img, %d chars", key.upper(), len(imgs), len(txt))
        logger.info("  images_mode : %s", images_mode)
        logger.info("  format      : %s", format_type.upper())
        logger.info("=" * 60)

        filename = file.filename
        ppt_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(ppt_path):
            file.save(ppt_path)

        metadata        = extract_slide1_metadata(ppt_path)
        incident_number = metadata.get("incident") or extract_full_incident_from_filename(filename)

        incident_data = _incident_cache.get(incident_number)
        if not incident_data:
            try:
                incident_data = get_preview_data(incident_number)
                _incident_cache[incident_number] = incident_data
            except Exception:
                incident_data = {}

        # ── Build images dict for word_renderer ────────────────────────
        # word_renderer expects: {"problem": [paths], "root": [paths], "resolution": [paths]}
        def _paths_for(zone_fns):
            return [p for fn in zone_fns
                    for p in [_resolve_img_path(fn)] if p]

        images_dict = {
            "problem":    _paths_for(assignments.get("problem",    [])),
            "root":       _paths_for(assignments.get("rootcause",  [])),
            "resolution": _paths_for(assignments.get("resolution", [])),
        }

        logger.info("Image paths resolved: problem=%d root=%d resolution=%d",
                    len(images_dict["problem"]),
                    len(images_dict["root"]),
                    len(images_dict["resolution"]))

        # ── Override RCA text if user edited it ───────────────────────
        root_text  = rca_text.get("problem",    "").strip() or incident_data.get("problem", "")
        l2_text    = rca_text.get("rootcause",  "").strip() or incident_data.get("analysis", "")
        res_text   = rca_text.get("resolution", "").strip() or incident_data.get("resolution", "")

        # ── Determine which PPT slides go in the "PPT Slides" section ──
        assigned_all = set()
        for fns in assignments.values():
            assigned_all.update(fns)

        if images_mode == "assigned":
            remaining_fns = [fn for fn in all_slide_fns if fn not in assigned_all]
        else:
            remaining_fns = all_slide_fns   # all slides

        # Determine ppt_data_arg based on images_mode
        # "all"      → pass ppt_path, renderer appends all slides
        # "assigned" → only unassigned slides needed; pass ppt_path + filter in renderer
        # "none"     → no PPT slides section
        if images_mode == "none" or not remaining_fns:
            ppt_data_arg = None
        else:
            ppt_data_arg = ppt_path

        logger.info("ppt_data_arg: %s (mode=%s, remaining=%d)",
                    ppt_data_arg or "None", images_mode, len(remaining_fns))

        # Build the word doc using the shared report renderer
        word_bytes = generate_word_doc_wrapper(
            data     = incident_data,
            root     = root_text,
            l2       = l2_text,
            res      = res_text,
            images   = images_dict,
            ppt_data = ppt_data_arg,
        )

        base      = os.path.splitext(filename)[0]
        date_str  = datetime.now().strftime("%d%b%Y").upper()
        docx_name = f"{base}_RCA_{date_str}.docx"
        docx_path = os.path.join(OUTPUT_FOLDER, docx_name)
        with open(docx_path, "wb") as f_out:
            f_out.write(word_bytes)

        docx_kb = os.path.getsize(docx_path) // 1024
        logger.info("RCA DOCX: %s  (%d KB)", docx_name, docx_kb)

        result = {"docx_filename": docx_name, "filename": docx_name}

        if format_type in ("pdf", "both"):
            try:
                pdf_path = doc_to_pdf(docx_path, OUTPUT_FOLDER)
                result["pdf_filename"] = os.path.basename(pdf_path)
                logger.info("RCA PDF: %s", result["pdf_filename"])
            except Exception as pdf_err:
                logger.error("RCA PDF failed: %s", pdf_err)
                result["pdf_error"] = str(pdf_err)
                if format_type == "pdf":
                    return jsonify({"error": f"PDF failed: {pdf_err}"}), 500

        logger.info("RCA GENERATE COMPLETE: %s", result)
        return jsonify(result)

    except Exception as e:
        logger.error("RCA Generate error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# DOWNLOAD GENERATED FILE
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/download/<filename>")
def download_converter(filename):
    try:
        path = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(path):
            return jsonify({"error": "File not found"}), 404
        logger.info("DOWNLOAD: %s  (%d KB)", filename, os.path.getsize(path)//1024)
        return send_file(path, as_attachment=True)
    except Exception as e:
        logger.error("Download error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# DOWNLOAD INDIVIDUAL SLIDE IMAGE
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/download-image/<filename>")
def download_slide_image(filename):
    try:
        path = _resolve_img_path(filename)
        if not path:
            return jsonify({"error": "Image not found"}), 404
        incident = request.args.get("incident", "IMG")
        idx      = request.args.get("idx", "001")
        date_str = datetime.now().strftime("%d%b%Y").upper()
        dl_name  = f"{incident}_image-{str(idx).zfill(3)}_{date_str}.png"
        logger.info("DOWNLOAD IMAGE: %s → %s", filename, dl_name)
        return send_file(path, as_attachment=True, download_name=dl_name)
    except Exception as e:
        logger.error("Download image error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# DOWNLOAD MULTIPLE IMAGES AS ZIP
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/download-images-zip", methods=["POST"])
def download_images_zip():
    try:
        import zipfile, io
        data      = request.get_json()
        filenames = data.get("filenames", [])
        incident  = data.get("incident", "IMG")
        if not filenames:
            return jsonify({"error": "No files specified"}), 400

        date_str = datetime.now().strftime("%d%b%Y").upper()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, fn in enumerate(filenames, 1):
                path = _resolve_img_path(fn)
                if path:
                    arc_name = f"{incident}_image-{str(i).zfill(3)}_{date_str}.png"
                    zf.write(path, arc_name)
                    logger.info("  Zipped: %s → %s", fn, arc_name)

        buf.seek(0)
        zip_name = f"{incident}_slides_{date_str}.zip"
        logger.info("ZIP: %s (%d files)", zip_name, len(filenames))
        return send_file(buf, as_attachment=True, download_name=zip_name,
                         mimetype="application/zip")
    except Exception as e:
        logger.error("ZIP error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# CREATE RCA PPTX (reverse: RCA → PowerPoint)
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/create-ppt", methods=["POST"])
def create_rca_ppt():
    try:
        file            = request.files.get("ppt_file")
        rca_raw         = request.form.get("rca_assignments", "{}")
        text_raw        = request.form.get("rca_text", "{}")
        incident_raw    = request.form.get("incident_data", "{}")

        assignments   = json.loads(rca_raw)
        rca_text      = json.loads(text_raw)
        incident_data = json.loads(incident_raw)

        filename = file.filename if file else request.form.get("filename", "report.pptx")
        ppt_path = os.path.join(UPLOAD_FOLDER, filename)
        if file and not os.path.exists(ppt_path):
            file.save(ppt_path)

        metadata        = extract_slide1_metadata(ppt_path) if os.path.exists(ppt_path) else {}
        incident_number = (metadata.get("incident")
                           or extract_full_incident_from_filename(filename)
                           or "INC000000")

        if not incident_data:
            incident_data = _incident_cache.get(incident_number, {})
            if not incident_data:
                try:
                    incident_data = get_preview_data(incident_number)
                except Exception:
                    incident_data = {}

        logger.info("=" * 60)
        logger.info("CREATE RCA PPTX: %s", incident_number)
        for key in ("problem", "rootcause", "resolution"):
            imgs = assignments.get(key, [])
            txt  = (rca_text.get(key) or "").strip()
            logger.info("  %-12s: %d img, %d chars", key, len(imgs), len(txt))

        # Resolve image paths
        rca_image_paths = {}
        for zone, fns in assignments.items():
            paths = [p for fn in fns for p in [_resolve_img_path(fn)] if p]
            rca_image_paths[zone] = paths

        base     = os.path.splitext(filename)[0]
        date_str = datetime.now().strftime("%d%b%Y").upper()
        out_name = f"{base}_RCA_{date_str}.pptx"
        out_path = os.path.join(OUTPUT_FOLDER, out_name)

        create_rca_pptx(
            incident_data   = incident_data,
            incident_number = incident_number,
            rca_text        = rca_text,
            rca_image_paths = rca_image_paths,
            output_path     = out_path,
        )

        size_kb = os.path.getsize(out_path) // 1024
        logger.info("RCA PPTX: %s  (%d KB)", out_name, size_kb)
        return jsonify({"pptx_filename": out_name, "size_kb": size_kb})

    except Exception as e:
        logger.error("Create PPT error: %s", e)
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# DOWNLOAD PPTX
# ═══════════════════════════════════════════════════════════════════
@converter_bp.route("/converter/download-pptx/<filename>")
def download_pptx(filename):
    try:
        path = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(path):
            return jsonify({"error": "File not found"}), 404
        logger.info("DOWNLOAD PPTX: %s  (%d KB)", filename, os.path.getsize(path)//1024)
        return send_file(path, as_attachment=True)
    except Exception as e:
        logger.error("Download PPTX error: %s", e)
        return jsonify({"error": str(e)}), 500
