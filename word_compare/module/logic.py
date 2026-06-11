"""
word_compare/module/logic.py
Core comparison engine for Word documents.
Produces:
  - structured diff rows (paragraphs + tables) for preview
  - base64-encoded images extracted from each document
  - highlighted .docx bundle (ZIP)
"""

import os
import base64
import difflib
import hashlib
import html
import zipfile
import tempfile
from copy import deepcopy
from datetime import datetime, timezone, timedelta

from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


# ─────────────────────────────────────────
# Highlight helpers
# ─────────────────────────────────────────

def _highlight_run(run, color="yellow"):
    if color == "yellow":
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    elif color == "green":
        run.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN
    elif color == "red":
        run.font.color.rgb = RGBColor(255, 255, 255)
        shading = parse_xml(r'<w:shd {} w:fill="FF0000"/>'.format(nsdecls("w")))
        run._r.get_or_add_rPr().append(shading)


# ─────────────────────────────────────────
# Content extraction
# ─────────────────────────────────────────

def _extract_lines(doc_path):
    """Return flat list of text lines (paragraphs + table cells) from docx."""
    doc = Document(doc_path)
    lines = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append({"type": "para", "text": text})

    for t_idx, table in enumerate(doc.tables):
        lines.append({"type": "table_header", "text": f"[TABLE {t_idx + 1}]"})
        for row in table.rows:
            row_text = " │ ".join(cell.text.strip() for cell in row.cells)
            if row_text.strip("│ "):
                lines.append({"type": "table_row", "text": row_text})

    return lines


def _extract_images_b64(doc_path):
    """Return list of base64-encoded images from docx."""
    doc = Document(doc_path)
    images = []
    seen = set()

    for rel in doc.part.rels.values():
        try:
            if rel.is_external:
                continue
            if "image" in rel.target_ref.lower():
                blob = rel.target_part.blob
                img_hash = hashlib.md5(blob).hexdigest()
                if img_hash in seen:
                    continue
                seen.add(img_hash)

                ext = rel.target_ref.rsplit(".", 1)[-1].lower()
                mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                            "gif": "gif", "bmp": "png", "wmf": "png"}
                mime = mime_map.get(ext, "png")
                b64 = base64.b64encode(blob).decode("utf-8")
                images.append({"mime": f"image/{mime}", "data": b64})
        except Exception:
            continue

    return images


# ─────────────────────────────────────────
# Diff row builder
# ─────────────────────────────────────────

def _escape(text):
    return html.escape(text)


def _build_row(text, css_class, prefix=""):
    safe = _escape(text)
    display = f"{prefix}{safe}" if text else ""
    return {"html": display, "css": css_class, "text": text}


def _build_diff_rows(old_lines, new_lines):
    old_texts = [l["text"] for l in old_lines]
    new_texts = [l["text"] for l in new_lines]

    matcher = difflib.SequenceMatcher(None, old_texts, new_texts, autojunk=False)
    old_rows, new_rows = [], []

    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            for k in range(i2 - i1):
                old_rows.append(_build_row(old_texts[i1 + k], "normal"))
                new_rows.append(_build_row(new_texts[j1 + k], "normal"))

        elif opcode == "delete":
            for line in old_texts[i1:i2]:
                old_rows.append(_build_row(line, "removed", "❌ "))
                new_rows.append(_build_row("", "blank"))

        elif opcode == "insert":
            for line in new_texts[j1:j2]:
                old_rows.append(_build_row("", "blank"))
                new_rows.append(_build_row(line, "added", "➕ "))

        elif opcode == "replace":
            old_chunk = old_texts[i1:i2]
            new_chunk = new_texts[j1:j2]
            max_len = max(len(old_chunk), len(new_chunk))
            for k in range(max_len):
                o = old_chunk[k] if k < len(old_chunk) else ""
                n = new_chunk[k] if k < len(new_chunk) else ""
                old_rows.append(_build_row(o, "updated" if o else "blank", "🔄 " if o else ""))
                new_rows.append(_build_row(n, "updated" if n else "blank", "🔄 " if n else ""))

    return old_rows, new_rows


# ─────────────────────────────────────────
# Public: run_compare
# ─────────────────────────────────────────

def run_compare(path1, path2):
    old_lines = _extract_lines(path1)
    new_lines = _extract_lines(path2)
    old_rows, new_rows = _build_diff_rows(old_lines, new_lines)

    # Build stats
    added = sum(1 for r in new_rows if r["css"] == "added")
    removed = sum(1 for r in old_rows if r["css"] == "removed")
    modified = sum(1 for r in old_rows if r["css"] == "updated")
    total = added + removed + modified

    images_old = _extract_images_b64(path1)
    images_new = _extract_images_b64(path2)

    return {
        "diff": {"old": old_rows, "new": new_rows},
        "stats": {"added": added, "removed": removed, "modified": modified, "total": total},
        "images_old": images_old,
        "images_new": images_new,
    }


# ─────────────────────────────────────────
# Highlighted .docx generation
# ─────────────────────────────────────────

def _compare_and_highlight(path1, path2, out_old, out_new):
    old_doc = Document(path1)
    new_doc = Document(path2)
    old_out = deepcopy(old_doc)
    new_out = deepcopy(new_doc)

    # Paragraphs
    old_paras = old_doc.paragraphs
    new_paras = new_doc.paragraphs
    max_len = max(len(old_paras), len(new_paras))

    for i in range(max_len):
        if i >= len(old_paras):
            if i < len(new_out.paragraphs):
                for run in new_out.paragraphs[i].runs:
                    _highlight_run(run, "green")
            continue
        if i >= len(new_paras):
            if i < len(old_out.paragraphs):
                for run in old_out.paragraphs[i].runs:
                    _highlight_run(run, "red")
            continue

        old_text = old_paras[i].text.strip()
        new_text = new_paras[i].text.strip()
        if old_text == new_text:
            continue

        old_words = old_text.split()
        new_words = new_text.split()
        m = difflib.SequenceMatcher(None, old_words, new_words)
        ops = m.get_opcodes()

        if any(t == "delete" for t, *_ in ops):
            old_out.paragraphs[i].clear()
            for tag, a1, a2, b1, b2 in ops:
                seg = " ".join(old_words[a1:a2])
                if not seg:
                    continue
                run = old_out.paragraphs[i].add_run(seg + " ")
                if tag == "delete":
                    _highlight_run(run, "red")

        if any(t in ("insert", "replace") for t, *_ in ops):
            for run in new_out.paragraphs[i].runs:
                if any(t == "replace" for t, *_ in ops):
                    _highlight_run(run, "yellow")
                else:
                    _highlight_run(run, "green")

    # Tables
    for t_idx in range(min(len(old_doc.tables), len(new_doc.tables))):
        old_tbl = old_doc.tables[t_idx]
        new_tbl = new_doc.tables[t_idx]
        old_out_tbl = old_out.tables[t_idx]
        new_out_tbl = new_out.tables[t_idx]

        for r_idx in range(min(len(old_tbl.rows), len(new_tbl.rows))):
            for c_idx in range(min(len(old_tbl.rows[r_idx].cells),
                                   len(new_tbl.rows[r_idx].cells))):
                ot = old_tbl.rows[r_idx].cells[c_idx].text
                nt = new_tbl.rows[r_idx].cells[c_idx].text
                if ot == nt:
                    continue
                if ot and not nt:
                    for p in old_out_tbl.rows[r_idx].cells[c_idx].paragraphs:
                        for run in p.runs:
                            _highlight_run(run, "red")
                for p in new_out_tbl.rows[r_idx].cells[c_idx].paragraphs:
                    for run in p.runs:
                        _highlight_run(run, "yellow")

    old_out.save(out_old)
    new_out.save(out_new)


def generate_highlighted_bundle(path1, path2, name1, name2):
    ist = timezone(timedelta(hours=5, minutes=30))
    date_str = datetime.now(ist).strftime("%d%b%Y")

    base1 = os.path.splitext(name1)[0]
    base2 = os.path.splitext(name2)[0]
    out_name1 = f"{base1}_Diff-Highlighted_{date_str}.docx"
    out_name2 = f"{base2}_Diff-Highlighted_{date_str}.docx"
    zip_name = f"Word-Compare_{date_str}.zip"

    with tempfile.TemporaryDirectory() as tmp:
        out1 = os.path.join(tmp, out_name1)
        out2 = os.path.join(tmp, out_name2)
        _compare_and_highlight(path1, path2, out1, out2)

        zip_path = os.path.join(tempfile.gettempdir(), zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(out1, out_name1)
            zf.write(out2, out_name2)

    return zip_path, zip_name
