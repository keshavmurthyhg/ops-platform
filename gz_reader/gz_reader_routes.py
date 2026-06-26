"""
gz_reader/gz_reader_routes.py  —  v09
Endpoints:
  GET  /gz-reader/                       → main page
  POST /gz-reader/upload                 → upload .gz for server-side split
  GET  /gz-reader/split-stream           → SSE: stream chunks as written
  GET  /gz-reader/chunk-preview/<name>   → first 80 KB of chunk
  GET  /gz-reader/chunk-download/<name>  → download single chunk
  GET  /gz-reader/download/<safe_name>   → download full decompressed
  POST /gz-reader/save-summary           → save summary report to outputs/gz_summary/
  GET  /api/help/gz-reader               → help topics JSON (registered via help bp)
"""

import os, gzip, uuid, json, datetime
from collections import Counter
from flask import (
    Blueprint, render_template, request,
    jsonify, send_file, current_app, Response, stream_with_context,
)
from werkzeug.utils import secure_filename
from gz_reader.module.gz_parser import parse_gz_file, split_jmx_gz
from common.logger import setup_logger

logger = setup_logger("gz_reader")

gz_reader_bp = Blueprint(
    "gz_reader", __name__,
    template_folder="templates",
    static_folder="statics",
    static_url_path="/gz_reader/static",
    url_prefix="/gz-reader",
)

# ── helpers ───────────────────────────────────────────────────
def _upload_dir():
    d = os.path.join(current_app.config.get("UPLOAD_FOLDER", "uploads"), "gz_reader")
    os.makedirs(d, exist_ok=True); return d

def _output_dir():
    d = current_app.config.get("OUTPUT_FOLDER", "outputs")
    os.makedirs(d, exist_ok=True); return d

def _summary_dir():
    d = os.path.join(current_app.config.get("OUTPUT_FOLDER", "outputs"), "gz_summary")
    os.makedirs(d, exist_ok=True); return d

# ── routes ────────────────────────────────────────────────────
@gz_reader_bp.route("/")
def index():
    logger.info("GZ Reader page loaded")
    return render_template("gz_reader.html")


@gz_reader_bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        logger.warning("Upload called with no file part")
        return jsonify({"error": "No file part in request"}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "No file selected"}), 400
    if not f.filename.lower().endswith(".gz"):
        logger.warning("Rejected non-gz: %s", f.filename)
        return jsonify({"error": "Only .gz files are supported"}), 400

    uid = uuid.uuid4().hex[:8]
    safe_name = f"{uid}_{secure_filename(f.filename)}"
    save_path = os.path.join(_upload_dir(), safe_name)
    try:
        f.save(save_path)
    except Exception as exc:
        logger.error("Failed to save upload %s: %s", f.filename, exc, exc_info=True)
        return jsonify({"error": f"Save failed: {exc}"}), 500

    kb = os.path.getsize(save_path) / 1024
    logger.info("File saved: %s (%.1f KB)", safe_name, kb)

    try:
        result = parse_gz_file(save_path)
        result["_saved_as"] = safe_name
        result.pop("full_text", None)
        logger.info("Parsed %s → format=%s rows=%s file_kb=%.1f",
                    f.filename, result.get("format"),
                    result.get("total_rows") or result.get("line_count","?"),
                    result.get("file_size_kb", 0))
        return jsonify(result)
    except Exception as exc:
        logger.error("Parse failed for %s: %s", f.filename, exc, exc_info=True)
        return jsonify({"error": f"Parse error: {exc}"}), 500


@gz_reader_bp.route("/split-stream", methods=["GET"])
def split_stream():
    safe_name = request.args.get("saved_as", "")
    split_mb  = max(5, min(int(request.args.get("split_mb", 50)), 500))

    gz_path = os.path.join(_upload_dir(), safe_name)
    if not os.path.exists(gz_path):
        def _err():
            yield f'data: {json.dumps({"type":"error","message":"File not found — please re-upload"})}\n\n'
        return Response(stream_with_context(_err()), mimetype="text/event-stream")

    out_dir = _output_dir()

    def generate():
        logger.info("Split-stream: %s → %d MB chunks → %s", safe_name, split_mb, out_dir)
        try:
            for idx, path in enumerate(_split_streaming(gz_path, out_dir, split_mb), start=1):
                fname = os.path.basename(path)
                size_kb = round(os.path.getsize(path) / 1024, 1)
                payload = json.dumps({"type":"chunk","index":idx,"filename":fname,"size_kb":size_kb})
                logger.info("Chunk ready: %s (%.1f KB)", fname, size_kb)
                yield f"data: {payload}\n\n"
            yield f'data: {json.dumps({"type":"done"})}\n\n'
            logger.info("Split-stream complete: %s", safe_name)
        except Exception as exc:
            logger.error("Split-stream error for %s: %s", safe_name, exc, exc_info=True)
            yield f'data: {json.dumps({"type":"error","message":str(exc)})}\n\n'

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


@gz_reader_bp.route("/chunk-preview/<filename>")
def chunk_preview(filename):
    safe = secure_filename(filename)
    path = os.path.join(_output_dir(), safe)
    if not os.path.exists(path):
        logger.warning("Chunk preview not found: %s", safe)
        return jsonify({"error": "Chunk not found"}), 404
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read(81920)
        size_kb = round(os.path.getsize(path) / 1024, 1)
        logger.info("Chunk preview served: %s (%.1f KB)", safe, size_kb)
        return jsonify({"content": content, "size_kb": size_kb, "filename": safe})
    except Exception as exc:
        logger.error("Chunk preview error for %s: %s", safe, exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


@gz_reader_bp.route("/chunk-download/<filename>")
def chunk_download(filename):
    safe = secure_filename(filename)
    path = os.path.join(_output_dir(), safe)
    if not os.path.exists(path):
        logger.warning("Chunk download not found: %s", safe)
        return jsonify({"error": "Chunk not found"}), 404
    logger.info("Chunk download: %s", safe)
    return send_file(path, as_attachment=True, download_name=safe)


@gz_reader_bp.route("/download/<string:safe_name>")
def download(safe_name):
    gz_path = os.path.join(_upload_dir(), safe_name)
    if not os.path.exists(gz_path):
        logger.warning("Download not found: %s", safe_name)
        return jsonify({"error": "File not found"}), 404
    inner = safe_name[9:] if len(safe_name) > 9 else safe_name
    if inner.lower().endswith(".gz"):
        inner = inner[:-3]
    out_path = os.path.join(_output_dir(), inner)
    logger.info("Decompressing %s → %s", safe_name, inner)
    try:
        with gzip.open(gz_path, "rb") as gi, open(out_path, "wb") as fo:
            fo.write(gi.read())
        logger.info("Download served: %s", inner)
        return send_file(out_path, as_attachment=True, download_name=inner)
    except Exception as exc:
        logger.error("Decompress error %s: %s", safe_name, exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


@gz_reader_bp.route("/save-summary", methods=["POST"])
def save_summary():
    """
    Receive summary data from the browser, write to outputs/gz_summary/,
    and return the file for browser download — all local, no external transmission.
    Body JSON: { filename, metadata, top_mbeans, top_components, top_attrs,
                  top_users, filtered_rows (up to 10000), headers }
    """
    try:
        body = request.get_json(force=True) or {}
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = body.get("filename", f"jmx_summary_{ts}").replace(" ", "_")
        if not fname.endswith(".txt"):
            fname = fname + f"_{ts}.txt"

        out_dir  = _summary_dir()
        out_path = os.path.join(out_dir, fname)

        lines = []
        lines.append("=" * 70)
        lines.append("  GZ READER — JMX SUMMARY REPORT")
        lines.append(f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")

        meta = body.get("metadata", {})
        lines.append("FILE INFORMATION")
        lines.append("-" * 40)
        for k, v in meta.items():
            lines.append(f"  {k:<22}: {v}")
        lines.append("")

        for section_key, section_title in [
            ("top_mbeans",     "TOP MBEAN / CACHE NAMES"),
            ("top_components", "TOP COMPONENT NAMESPACES"),
            ("top_attrs",      "TOP ATTRIBUTE NAMES"),
            ("top_users",      "TOP USERS / PRINCIPALS"),
        ]:
            items = body.get(section_key, [])
            if items:
                lines.append(section_title)
                lines.append("-" * 40)
                for item in items:
                    lines.append(f"  {item.get('count',''):>8}  {item.get('name','')}")
                lines.append("")

        rows = body.get("filtered_rows", [])
        headers = body.get("headers", [])
        if rows:
            lines.append(f"FILTERED RECORDS ({len(rows):,} rows)")
            lines.append("-" * 40)
            if headers:
                lines.append("  " + " | ".join(f"{h:<20}" for h in headers))
                lines.append("  " + "-" * (len(headers) * 22))
            for row in rows[:10000]:
                lines.append("  " + " | ".join(f"{str(c):<20}" for c in row))
            lines.append("")

        lines.append("=" * 70)
        lines.append("  END OF REPORT  —  Data is confidential. Do not share externally.")
        lines.append("=" * 70)

        content = "\n".join(lines)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        logger.info("GZ summary saved: %s (%d KB)", fname, len(content) // 1024)
        return send_file(out_path, as_attachment=True, download_name=fname,
                         mimetype="text/plain")

    except Exception as exc:
        logger.error("save_summary error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


# ── Streaming split helper ────────────────────────────────────
from gz_reader.module.gz_parser import _segments_from_chunk, STREAM_CHUNK

def _split_streaming(filepath, out_dir, split_mb):
    import gzip as _gzip
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(filepath)
    if len(base) > 9: base = base[9:]
    if base.lower().endswith(".gz"): base = base[:-3]

    limit    = split_mb * 1024 * 1024
    overlap  = 8192
    leftover = b""
    part = 1; part_bytes = 0

    def _open(n):
        name = os.path.join(out_dir, f"{base}_part{n:03d}.txt")
        return open(name, "w", encoding="utf-8", errors="replace"), name

    fout, fname = _open(part)
    try:
        with _gzip.open(filepath, "rb") as fh:
            while True:
                raw = fh.read(STREAM_CHUNK)
                if not raw: break
                chunk = leftover + raw
                leftover = chunk[-overlap:] if len(chunk) > overlap else b""
                process  = chunk[:-overlap] if len(chunk) > overlap else chunk
                for seg in _segments_from_chunk(process):
                    line = seg + "\n"
                    lb   = len(line.encode("utf-8", errors="replace"))
                    if part_bytes > 0 and part_bytes + lb > limit:
                        fout.close(); yield fname
                        part += 1; part_bytes = 0
                        fout, fname = _open(part)
                    fout.write(line); part_bytes += lb
        for seg in _segments_from_chunk(leftover):
            fout.write(seg + "\n")
    finally:
        fout.close()
    if os.path.getsize(fname) > 0:
        yield fname
    elif os.path.exists(fname):
        os.remove(fname)
