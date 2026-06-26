"""
gz_reader/module/gz_parser.py
==============================
Memory-safe parsing of Windchill .gz exports.

Design constraints
------------------
JMXData.gz decompresses to ~3.7 GB. Everything is STREAMED:
  - gzip file is never fully read into RAM
  - preview is capped at MAX_PREVIEW_ROWS rows
  - total_rows is counted without storing rows
  - split() writes directly to output files chunk by chunk
  - detection uses only the first DETECT_BYTES of the stream

Supported inner formats: JMX binary, XML, CSV/TSV, JSON, plain text.
"""

import gzip
import io
import os
import re
import csv
import json
from datetime import datetime

# ── Tunables ───────────────────────────────────────────────────────────────────
MAX_PREVIEW_ROWS = 500          # rows shown in table preview
MAX_RAW_CHARS    = 60_000       # chars shown in raw text view
DETECT_BYTES     = 64 * 1024    # bytes read for format/JMX detection (64 KB)
STREAM_CHUNK     = 4 * 1024 * 1024   # 4 MB read chunk for streaming


# ── Encoding ───────────────────────────────────────────────────────────────────

def _decode_bytes(b: bytes) -> str:
    """Decode a byte string without third-party libraries."""
    if b.startswith(b"\xef\xbb\xbf"):
        try: return b[3:].decode("utf-8")
        except UnicodeDecodeError: pass
    if b.startswith(b"\xff\xfe") or b.startswith(b"\xfe\xff"):
        try: return b.decode("utf-16")
        except UnicodeDecodeError: pass
    try: return b.decode("utf-8")
    except UnicodeDecodeError: pass
    try: return b.decode("cp1252")
    except UnicodeDecodeError: pass
    return b.decode("utf-8", errors="replace")


# ── JMX detection & streaming parse ───────────────────────────────────────────

_JMX_MARKERS = [
    b"wt.queue", b"wt.folder", b"wt.fv.", b"wt.admin",
    b"com.ptc.core", b"com.ptc.windchill",
    b"wt.intersr", b"wt.method", b"wt.inf.",
    b"fv.FileServers", b"esi.tgt",
]

# Printable segment extractor (works on raw bytes, avoids decode issues)
_PRINT_RE   = re.compile(rb"[ -~\t\r\n\x80-\xff]{6,}")

# MBean / namespace pattern
_MBEAN_RE   = re.compile(
    r"((?:wt|com\.ptc|fv|esi)\.[A-Za-z0-9.$_]+)"
    r"(?:[^A-Za-z0-9.$_\n]([A-Za-z][A-Za-z0-9_]*))?",
    re.MULTILINE,
)
# Timestamp
_TS_RE      = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
    r"|(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})"
)
# Key=value pairs
_KV_RE      = re.compile(r"([A-Za-z][A-Za-z0-9_]{1,40})\s*[=:]\s*(\S{1,80})")
# User / principal
_USER_RE    = re.compile(
    r"(?:user|principal|subject|login|uid)[=:\s]+([A-Za-z0-9@._-]{3,60})",
    re.IGNORECASE,
)


def _is_jmx(header: bytes) -> bool:
    hits = sum(1 for m in _JMX_MARKERS if m in header)
    return hits >= 3


def _segments_from_chunk(chunk: bytes):
    """Yield decoded printable text segments from a raw byte chunk."""
    for m in _PRINT_RE.finditer(chunk):
        try:
            seg = m.group().decode("cp1252", errors="replace").strip()
            if seg:
                yield seg
        except Exception:
            pass


def _parse_jmx_streaming(filepath: str) -> dict:
    """
    Stream through a JMX gz file without loading it into RAM.

    Strategy
    --------
    - Read the gz in STREAM_CHUNK byte blocks
    - Extract printable text segments per block
    - Parse MBean/KV records from each segment
    - Collect only MAX_PREVIEW_ROWS rows; count the rest
    - Track decompressed size byte-by-byte
    """
    preview_rows  = []
    total_rows    = 0
    total_bytes   = 0
    segment_count = 0
    current_ts    = ""
    current_user  = ""
    collecting    = True   # stop storing rows after MAX_PREVIEW_ROWS

    # Keep a small overlap buffer between chunks so segments aren't split
    # at chunk boundaries (max JMX segment is a few KB so 8 KB overlap is fine)
    OVERLAP = 8192
    leftover = b""

    with gzip.open(filepath, "rb") as fh:
        while True:
            raw = fh.read(STREAM_CHUNK)
            if not raw:
                break
            total_bytes += len(raw)
            chunk = leftover + raw
            # save the tail as leftover for next iteration
            leftover = chunk[-OVERLAP:] if len(chunk) > OVERLAP else b""
            # only process up to the overlap boundary (avoid double-counting)
            process = chunk if not raw else chunk[:-OVERLAP] if len(chunk) > OVERLAP else chunk

            for seg in _segments_from_chunk(process):
                segment_count += 1

                ts_hit = _TS_RE.search(seg)
                if ts_hit:
                    current_ts = ts_hit.group(1) or ts_hit.group(2) or current_ts

                user_hit = _USER_RE.search(seg)
                if user_hit:
                    current_user = user_hit.group(1)

                mbean_hits = list(_MBEAN_RE.finditer(seg))
                kv_hits    = _KV_RE.findall(seg)

                new_rows = []
                if mbean_hits:
                    for mhit in mbean_hits:
                        mbean     = mhit.group(1)
                        attr      = mhit.group(2) or ""
                        parts     = mbean.split(".")
                        component = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
                        if kv_hits:
                            for k, v in kv_hits:
                                new_rows.append([current_ts, current_user,
                                                 component, mbean, attr or k, v, seg[:120]])
                        else:
                            new_rows.append([current_ts, current_user,
                                             component, mbean, attr, "", seg[:120]])
                elif kv_hits:
                    for k, v in kv_hits:
                        new_rows.append([current_ts, current_user, "", "", k, v, seg[:120]])

                total_rows += len(new_rows)
                if collecting:
                    preview_rows.extend(new_rows)
                    if len(preview_rows) >= MAX_PREVIEW_ROWS:
                        preview_rows = preview_rows[:MAX_PREVIEW_ROWS]
                        collecting   = False

        # process final leftover
        for seg in _segments_from_chunk(leftover):
            segment_count += 1
            mbean_hits = list(_MBEAN_RE.finditer(seg))
            kv_hits    = _KV_RE.findall(seg)
            if mbean_hits:
                total_rows += len(mbean_hits) * max(len(kv_hits), 1)
            elif kv_hits:
                total_rows += len(kv_hits)

    return {
        "format":        "jmx",
        "parsed":        True,
        "headers":       ["Timestamp", "User", "Component", "MBean / Cache",
                          "Attribute", "Value", "Raw Segment"],
        "rows":          preview_rows,
        "total_rows":    total_rows,
        "truncated":     total_rows > MAX_PREVIEW_ROWS,
        "segment_count": segment_count,
        "file_size_kb":  round(total_bytes / 1024, 1),
    }


# ── Split (streaming) ──────────────────────────────────────────────────────────

def split_jmx_gz(filepath: str, out_dir: str, split_mb: int = 50) -> list[str]:
    """
    Decompress a JMX gz and write readable plain-text chunks.
    Fully streaming — never loads the whole file into RAM.
    Returns list of output file paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    # strip uid prefix (9 chars: 8hex + underscore) and .gz
    base = os.path.basename(filepath)
    if len(base) > 9:
        base = base[9:]
    if base.lower().endswith(".gz"):
        base = base[:-3]

    chunk_limit = split_mb * 1024 * 1024   # bytes per output file
    out_paths   = []
    part        = 1
    part_bytes  = 0
    leftover    = b""
    OVERLAP     = 8192

    def _open_part():
        name = os.path.join(out_dir, f"{base}_part{part:03d}.txt")
        return open(name, "w", encoding="utf-8", errors="replace"), name

    fout, fout_name = _open_part()
    out_paths.append(fout_name)

    try:
        with gzip.open(filepath, "rb") as fh:
            while True:
                raw = fh.read(STREAM_CHUNK)
                if not raw:
                    break
                chunk   = leftover + raw
                leftover = chunk[-OVERLAP:] if len(chunk) > OVERLAP else b""
                process  = chunk[:-OVERLAP] if len(chunk) > OVERLAP else chunk

                for seg in _segments_from_chunk(process):
                    line       = seg + "\n"
                    line_bytes = len(line.encode("utf-8", errors="replace"))
                    if part_bytes > 0 and part_bytes + line_bytes > chunk_limit:
                        fout.close()
                        part      += 1
                        part_bytes = 0
                        fout, fout_name = _open_part()
                        out_paths.append(fout_name)
                    fout.write(line)
                    part_bytes += line_bytes

            # flush leftover
            for seg in _segments_from_chunk(leftover):
                fout.write(seg + "\n")
    finally:
        fout.close()

    # remove empty last file if nothing was written
    if out_paths and os.path.getsize(out_paths[-1]) == 0:
        os.remove(out_paths[-1])
        out_paths.pop()

    return out_paths


# ── JMX detection (header only) ────────────────────────────────────────────────

def _peek_gz(filepath: str, n: int = DETECT_BYTES) -> bytes:
    """Read first n bytes of a gz stream without loading the whole file."""
    buf = b""
    with gzip.open(filepath, "rb") as fh:
        buf = fh.read(n)
    return buf


# ── Generic text format helpers ────────────────────────────────────────────────

def _sniff_format(sample: str, filename: str) -> str:
    lower = filename.lower()
    inner = lower[:-3] if lower.endswith(".gz") else lower
    if inner.endswith(".xml"):  return "xml"
    if inner.endswith(".json"): return "json"
    if inner.endswith(".csv"):  return "csv"
    if inner.endswith(".tsv") or inner.endswith(".tab"): return "tsv"
    stripped = sample.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<"): return "xml"
    if stripped.startswith("{") or stripped.startswith("["):     return "json"
    try:
        dialect = csv.Sniffer().sniff("\n".join(sample.splitlines()[:10]), delimiters=",\t|;")
        return "tsv" if dialect.delimiter == "\t" else "csv"
    except csv.Error:
        pass
    return "text"


def _stream_text_gz(filepath: str) -> tuple[str, int, int]:
    """
    Stream a text gz and return (preview_text, total_chars, total_lines).
    Reads at most MAX_RAW_CHARS characters for preview.
    """
    preview    = []
    total_chars = 0
    total_lines = 0
    leftover   = b""

    with gzip.open(filepath, "rb") as fh:
        while True:
            raw = fh.read(STREAM_CHUNK)
            if not raw:
                break
            chunk  = leftover + raw
            leftover = b""
            try:
                text = chunk.decode("utf-8", errors="replace")
            except Exception:
                text = chunk.decode("cp1252", errors="replace")
            total_chars += len(text)
            total_lines += text.count("\n")
            if len("".join(preview)) < MAX_RAW_CHARS:
                preview.append(text)

    preview_text = "".join(preview)[:MAX_RAW_CHARS]
    return preview_text, total_chars, total_lines


def _stream_csv_gz(filepath: str, delimiter: str) -> dict:
    """Stream a delimited text gz, collect MAX_PREVIEW_ROWS + count total."""
    headers    = []
    rows       = []
    total_rows = 0
    buf        = io.StringIO()
    leftover   = ""

    with gzip.open(filepath, "rt", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        for i, row in enumerate(reader):
            if i == 0:
                headers = row
            else:
                total_rows += 1
                if len(rows) < MAX_PREVIEW_ROWS:
                    rows.append(row)

    return {
        "headers":   headers,
        "rows":      rows,
        "total_rows": total_rows,
        "truncated": total_rows > MAX_PREVIEW_ROWS,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_gz_file(filepath: str) -> dict:
    """
    Parse a .gz file safely with bounded memory usage.
    Never loads the full decompressed content into RAM for JMX or large files.
    """
    filename      = os.path.basename(filepath)
    compressed_kb = os.path.getsize(filepath) / 1024
    base_result   = {
        "filename":      filename,
        "compressed_kb": round(compressed_kb, 1),
        "file_size_kb":  0.0,
        "parsed_at":     datetime.now().isoformat(timespec="seconds"),
        "error":         None,
    }

    # ── Peek at the header for format detection ──
    try:
        header = _peek_gz(filepath)
    except Exception as exc:
        base_result.update({"format": "unknown", "parsed": False,
                             "error": f"Cannot read gz: {exc}"})
        return base_result

    # ── JMX binary? → stream parse ──
    if _is_jmx(header):
        try:
            parsed = _parse_jmx_streaming(filepath)
            base_result.update(parsed)
            # file_size_kb filled in by streaming parse
            return base_result
        except Exception as exc:
            base_result.update({"format": "jmx", "parsed": False,
                                 "error": f"JMX parse error: {exc}"})
            return base_result

    # ── Text-based formats ──
    # Use header sample (already decoded) for format sniffing
    sample = _decode_bytes(header)
    fmt    = _sniff_format(sample, filename)
    base_result["format"] = fmt

    try:
        if fmt in ("csv", "tsv"):
            delim  = "\t" if fmt == "tsv" else ","
            parsed = _stream_csv_gz(filepath, delim)
            base_result.update(parsed)
            base_result["parsed"] = True

        elif fmt in ("xml", "json"):
            # XML/JSON must be loaded fully (structure-dependent) but are
            # typically small — guard with a size limit
            if compressed_kb > 200 * 1024:   # >200 MB compressed → warn
                base_result.update({
                    "parsed": False,
                    "error":  "File too large for XML/JSON in-memory parse (>200 MB compressed). "
                              "Use the Split feature to break it into smaller files.",
                })
                return base_result
            with gzip.open(filepath, "rb") as fh:
                raw = fh.read()
            base_result["file_size_kb"] = round(len(raw) / 1024, 1)
            content = _decode_bytes(raw)
            del raw   # free immediately
            if fmt == "xml":
                base_result.update(_parse_xml(content))
            else:
                base_result.update(_parse_json(content))

        else:   # plain text
            preview, total_chars, total_lines = _stream_text_gz(filepath)
            base_result.update({
                "parsed":     True,
                "raw":        preview,
                "truncated":  total_chars > MAX_RAW_CHARS,
                "line_count": total_lines,
                "file_size_kb": round(total_chars / 1024, 1),
            })

    except Exception as exc:
        base_result.update({"parsed": False, "error": f"Parse error: {exc}"})

    return base_result


# ── XML / JSON parsers (small files only) ─────────────────────────────────────

def _parse_xml(content: str) -> dict:
    try:
        import xml.etree.ElementTree as ET
        root       = ET.fromstring(content)
        tag_counts: dict = {}
        for child in root.iter():
            tag_counts[child.tag] = tag_counts.get(child.tag, 0) + 1
        if not tag_counts:
            return {"raw": content[:MAX_RAW_CHARS], "parsed": False}
        row_tag  = max(tag_counts, key=lambda t: tag_counts[t] if t != root.tag else 0)
        elements = root.findall(f".//{row_tag}")
        if not elements:
            return {"raw": content[:MAX_RAW_CHARS], "parsed": False}
        keys: list = []; seen: set = set()
        for el in elements[:50]:
            for k in list(el.attrib.keys()) + [ch.tag for ch in el]:
                if k not in seen: keys.append(k); seen.add(k)
        rows = []
        for el in elements[:MAX_PREVIEW_ROWS]:
            row = []
            for k in keys:
                val = el.attrib.get(k)
                if val is None:
                    ch  = el.find(k)
                    val = (ch.text or "").strip() if ch is not None else ""
                row.append(val or "")
            rows.append(row)
        return {"parsed": True, "headers": keys, "rows": rows,
                "total_rows": len(elements), "truncated": len(elements) > MAX_PREVIEW_ROWS,
                "root_tag": root.tag, "row_tag": row_tag}
    except Exception as exc:
        return {"raw": content[:MAX_RAW_CHARS], "parsed": False, "error": str(exc)}


def _parse_json(content: str) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return {"raw": content[:MAX_RAW_CHARS], "parsed": False, "error": str(exc)}
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = list(data[0].keys())
        rows = [[str(r.get(k, "")) for k in keys] for r in data[:MAX_PREVIEW_ROWS]]
        return {"parsed": True, "table": True, "headers": keys, "rows": rows,
                "total_rows": len(data), "truncated": len(data) > MAX_PREVIEW_ROWS}
    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    return {"parsed": True, "table": False, "raw": pretty[:MAX_RAW_CHARS],
            "truncated": len(pretty) > MAX_RAW_CHARS}
