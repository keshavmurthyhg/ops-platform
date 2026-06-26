"""
references_service.py
=====================
Extracts external references from ServiceNow incident note fields:

  • Azure DevOps user stories (VPA pattern)
    URL: https://dev.azure.com/VolvoGroup-DVP/VPA/_workitems/edit/{ID}
  • PTC support articles
    URL: https://www.ptc.com/en/support/article/{ID}

For each Azure user story, the surrounding text is analysed to detect:
  - Which environment the story was created for (TEST / QA / PROD / UAT)
  - A short description of why it was created (from the surrounding sentence)

Returns a structured list of reference dicts, used by:
  - preview_ui.render_preview_html() → References section in preview
  - report module (Editable RCA → References zone)
  - converter module (Incident Preview → References section)
"""

import os
import re
import logging

import pandas as pd

logger = logging.getLogger("references_service")

# ─────────────────────────────────────────────────────────────────────────────
# URL patterns
# ─────────────────────────────────────────────────────────────────────────────

# Azure VPA user story: https://dev.azure.com/VolvoGroup-DVP/VPA/_workitems/edit/770315
_AZURE_VPA = re.compile(
    r"https?://dev\.azure\.com/VolvoGroup-DVP/VPA/_workitems/edit/(\d+)/?",
    re.IGNORECASE,
)

# PTC article: https://www.ptc.com/en/support/article/CS98274
_PTC_ARTICLE = re.compile(
    r"https?://(?:www\.)?ptc\.com/[^\s\"'<>]*?/(?:article|support)/([A-Z0-9]+)/?",
    re.IGNORECASE,
)
# Also catch the shorter form: https://www.ptc.com/en/support/article/CS98274
_PTC_ARTICLE2 = re.compile(
    r"https?://(?:www\.)?ptc\.com[^\s\"'<>]*?/([A-Za-z]{2}\d{4,})/?\b",
    re.IGNORECASE,
)

# Environment keywords for Tags and Title lookup
_ENV_TAG_PATTERNS = [
    (re.compile(r"\bPROD(?:UCTION)?\b", re.IGNORECASE), "PROD"),
    (re.compile(r"\bQA\b",               re.IGNORECASE), "QA"),
    (re.compile(r"\bTEST(?:ING)?\b",    re.IGNORECASE), "TEST"),
    (re.compile(r"\bUAT\b",             re.IGNORECASE), "UAT"),
    (re.compile(r"\bDEVA?\b",           re.IGNORECASE), "DEV"),
    (re.compile(r"\bWC13\b",            re.IGNORECASE), "WC13"),
    (re.compile(r"\bSTAGE?\b",          re.IGNORECASE), "STAGE"),
]
_ENV_TITLE_PATTERNS = [
    (re.compile(r"[\s\-–]+PROD(?:UCTION)?\s*$", re.IGNORECASE), "PROD"),
    (re.compile(r"[\s\-–]+QA\s*$",               re.IGNORECASE), "QA"),
    (re.compile(r"[\s\-–]+TEST(?:ING)?\s*$",    re.IGNORECASE), "TEST"),
    (re.compile(r"[\s\-–]+UAT\s*$",             re.IGNORECASE), "UAT"),
    (re.compile(r"[\s\-–]+DEVA?\s*$",           re.IGNORECASE), "DEV"),
    (re.compile(r"[\s\-–]+WC13\s*$",            re.IGNORECASE), "WC13"),
    (re.compile(r"\bPROD(?:UCTION)?(?:\s+(?:server|env(?:ironment)?))?\b", re.IGNORECASE), "PROD"),
    (re.compile(r"\bQA(?:\s+(?:server|env(?:ironment)?))?\b",               re.IGNORECASE), "QA"),
    (re.compile(r"\bTEST(?:ING)?(?:\s+(?:server|env(?:ironment)?))?\b",    re.IGNORECASE), "TEST"),
    (re.compile(r"\bUAT(?:\s+(?:server|env(?:ironment)?))?\b",             re.IGNORECASE), "UAT"),
    (re.compile(r"\bDEVA?(?:\s+(?:server|env(?:ironment)?))?\b",           re.IGNORECASE), "DEV"),
    (re.compile(r"\bWC13\b",                                                 re.IGNORECASE), "WC13"),
]

# Sentence splitter for context extraction
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


# ─────────────────────────────────────────────────────────────────────────────
# AOM USER STORIES LOOKUP  (Tags → Title → fallback None)
# ─────────────────────────────────────────────────────────────────────────────

_AOM_ENV_MAP = None   # dict: str(story_id) → env_label | ""


def _load_aom_map():
    global _AOM_ENV_MAP
    if _AOM_ENV_MAP is not None:
        return _AOM_ENV_MAP

    _AOM_ENV_MAP = {}

    for path in ("data/AOM_user_stories.csv", "data/AOM_user_stories.xlsx"):
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, dtype=str) if path.endswith(".csv") else pd.read_excel(path, dtype=str)
        except Exception:
            continue

        df.columns = df.columns.str.strip().str.lower()
        id_col    = next((c for c in df.columns if c in ("id", "work item id", "workitemid")), None)
        title_col = next((c for c in df.columns if c in ("title", "name")), None)
        tags_col  = next((c for c in df.columns if c in ("tags", "tag")), None)

        if id_col is None:
            break

        for _, row in df.iterrows():
            sid = str(row.get(id_col, "")).strip()
            if not sid or sid in ("nan", ""):
                continue
            env = None

            # Priority 1: Title — most reliable (suffix like "- PROD" or "on QA server")
            if title_col:
                title_val = str(row.get(title_col, "")).strip()
                if title_val and title_val.lower() not in ("nan", ""):
                    for pat, label in _ENV_TITLE_PATTERNS:
                        if pat.search(title_val):
                            env = label
                            break

            # Priority 2: Tags — fallback when title yields nothing
            if not env and tags_col:
                tag_val = str(row.get(tags_col, "")).strip()
                if tag_val and tag_val.lower() not in ("nan", ""):
                    for pat, label in _ENV_TAG_PATTERNS:
                        if pat.search(tag_val):
                            env = label
                            break

            _AOM_ENV_MAP[sid] = env or ""
        break

    logger.info("AOM map loaded: %d entries", len(_AOM_ENV_MAP))
    return _AOM_ENV_MAP


def _get_env_for_story(story_id: str) -> str:
    """Return environment label for a VPA story ID from AOM map."""
    return _load_aom_map().get(str(story_id), "")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe(v):
    if not v:
        return ""
    v = str(v).strip()
    return "" if v.lower() in ("nan", "nat", "none") else v


def _get_context_sentence(text, url_start, url_end):
    """Return the sentence immediately BEFORE the URL (explains why it was created)."""
    # Take text up to 500 chars before the URL
    pre = text[max(0, url_start - 500):url_start].strip()
    if not pre:
        return ""
    # Split into lines/sentences and take the last meaningful one
    lines = [l.strip() for l in pre.split("\n") if l.strip()]
    # Filter out timestamp lines and attribution lines
    clean_lines = []
    for l in lines:
        if re.match(r"^\d{4}-\d{2}-\d{2}", l):
            continue  # skip timestamps
        if re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+\s*$", l):
            continue  # skip bare person names
        if "User story details" in l or "Please find details" in l or "details below" in l:
            continue  # skip the "User story details:" label line
        cl = re.sub(r"https?://\S+", "", l).strip()
        cl = re.sub(r"\s{2,}", " ", cl).strip()
        if len(cl) > 15:
            clean_lines.append(cl)
    return clean_lines[-1] if clean_lines else ""


def _detect_environment(context_text):
    """Legacy: detect env from surrounding text. Prefer AOM lookup (_get_env_for_story)."""
    for pattern, label in _ENV_TAG_PATTERNS:
        if pattern.search(context_text):
            return label
    return None


def _clean_context(ctx):
    """Strip timestamps, name prefixes, and excess whitespace from context."""
    # Remove "Firstname Lastname (Work notes)" attribution
    ctx = re.sub(
        r"[A-Z][a-z]+\s+[A-Z][a-z]+\s*\((?:Work notes|Additional comments|Resolution notes)\)\s*",
        "", ctx, flags=re.IGNORECASE
    )
    # Remove timestamps
    ctx = re.sub(r"\d{4}-\d{2}-\d{2}[\s\d:]*", "", ctx)
    # Remove leading dashes/bullets
    ctx = re.sub(r"^\s*[-•]\s*", "", ctx)
    ctx = re.sub(r"\s{2,}", " ", ctx).strip()
    return ctx


# ─────────────────────────────────────────────────────────────────────────────
# Core extractors
# ─────────────────────────────────────────────────────────────────────────────

def _extract_azure_refs(text):
    """Extract all Azure VPA user story references from text.
    Priority: AOM Title → AOM Tags → surrounding Work Notes / Additional Comments text.
    """
    refs = []
    seen = set()
    for m in _AZURE_VPA.finditer(text):
        story_id = m.group(1)
        if story_id in seen:
            continue
        seen.add(story_id)
        ctx_raw = _get_context_sentence(text, m.start(), m.end())
        ctx     = _clean_context(ctx_raw)
        env     = _get_env_for_story(story_id)
        # Fallback: scan surrounding note text if AOM yields nothing
        if not env:
            surrounding = text[max(0, m.start()-400): m.end()+150]
            env = _detect_environment(surrounding) or None
        refs.append({
            "type":        "azure_user_story",
            "id":          story_id,
            "url":         f"https://dev.azure.com/VolvoGroup-DVP/VPA/_workitems/edit/{story_id}",
            "label":       f"Azure User Story #{story_id}",
            "environment": env or None,
            "context":     ctx,
        })
    return refs


def _extract_ptc_refs(text):
    """Extract all PTC article references from text."""
    refs = []
    seen = set()

    # Extract full PTC URLs and parse article IDs from them
    for m in re.finditer(r"https?://(?:www[.])?ptc[.]com[^\s<>]+", text, re.IGNORECASE):
        url = m.group(0).rstrip("/")
        # Find article ID at the end: e.g. /CS98274 or /TPI12345
        id_match = re.search(r"/([A-Z]{2,3}\d{4,})/?$", url, re.IGNORECASE)
        if not id_match:
            continue
        article_id = id_match.group(1).upper()
        if article_id in seen:
            continue
        seen.add(article_id)
        canonical = f"https://www.ptc.com/en/support/article/{article_id}"
        ctx_raw = _get_context_sentence(text, m.start(), m.end())
        ctx     = _clean_context(ctx_raw)
        refs.append({
            "type":        "ptc_article",
            "id":          article_id,
            "url":         canonical,
            "label":       f"PTC Article {article_id}",
            "environment": None,
            "context":     ctx,
        })
    return refs


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def extract_references(data: dict) -> list:
    """
    Extract all Azure VPA user stories and PTC articles from the incident
    note fields (work_notes, additional_comments, resolution_notes).

    Returns a list of dicts:
    {
        type:        "azure_user_story" | "ptc_article"
        id:          str           # work item ID or article ID
        url:         str           # canonical URL
        label:       str           # human-readable label
        environment: str | None    # TEST / QA / PROD / UAT / DEV or None
        context:     str           # surrounding sentence explaining why
    }
    Deduplicated by (type, id).
    """
    note_fields = [
        _safe(data.get("work_notes",         data.get("Work notes",         ""))),
        _safe(data.get("additional_comments", data.get("Additional comments",""))),
        _safe(data.get("resolution_notes",    data.get("Resolution notes",  ""))),
    ]
    combined = "\n".join(f for f in note_fields if f)

    if not combined:
        logger.debug("extract_references: no note fields found")
        return []

    azure_refs = _extract_azure_refs(combined)
    ptc_refs   = _extract_ptc_refs(combined)

    # Deduplicate by (type, id)
    seen = set()
    result = []
    for r in azure_refs + ptc_refs:
        key = (r["type"], r["id"])
        if key not in seen:
            seen.add(key)
            result.append(r)

    logger.info("References extracted: %d azure, %d ptc (total=%d)",
                len([r for r in result if r["type"]=="azure_user_story"]),
                len([r for r in result if r["type"]=="ptc_article"]),
                len(result))
    return result


def format_references_text(refs: list) -> str:
    """
    Format extracted references as plain text for the RCA editor
    (pre-fills the References zone in the UI).
    """
    if not refs:
        return ""

    lines = []
    for r in refs:
        env_tag = f" [{r['environment']} environment]" if r["environment"] else ""
        ctx_tag = f" — {r['context']}" if r["context"] else ""
        lines.append(f"• {r['label']}{env_tag}{ctx_tag}\n  {r['url']}")

    return "\n\n".join(lines)


def render_references_html(refs: list) -> str:
    """
    Render references as an HTML block for inclusion in the preview panel.
    Each item is a clickable link with environment badge and context.
    """
    if not refs:
        return ""

    AZURE_COLOR = "#2563EB"
    PTC_COLOR   = "#9333EA"
    ENV_COLORS  = {
        "PROD": "#16a34a", "QA": "#d97706", "TEST": "#0891b2",
        "UAT": "#7c3aed",  "DEV": "#64748b", "STAGE": "#64748b",
        "WC13": "#0f766e",
    }

    rows = []
    for r in refs:
        color   = AZURE_COLOR if r["type"] == "azure_user_story" else PTC_COLOR
        icon    = "🔵" if r["type"] == "azure_user_story" else "🟣"
        env     = r.get("environment")
        ctx     = r.get("context", "")
        env_badge = ""
        if env:
            ec = ENV_COLORS.get(env, "#64748b")
            env_badge = (
                f'<span style="display:inline-block;background:{ec};color:white;'
                f'font-size:10px;font-weight:700;padding:1px 6px;border-radius:10px;'
                f'margin-left:6px;vertical-align:middle;">{env}</span>'
            )
        ctx_html = (
            f'<div style="font-size:11px;color:#64748b;margin-top:3px;line-height:1.4;">'
            f'{ctx}</div>'
        ) if ctx else ""

        rows.append(
            f'<tr>'
            f'<td style="padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top;width:160px;">'
            f'<span style="font-size:11px;font-weight:700;color:{color};">'
            f'{icon} {r["label"]}</span>{env_badge}'
            f'</td>'
            f'<td style="padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top;">'
            f'<a href="{r["url"]}" target="_blank" style="color:{color};word-break:break-all;">'
            f'{r["url"]}</a>'
            f'{ctx_html}'
            f'</td>'
            f'</tr>'
        )

    return (
        '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        '<thead><tr style="background:#f1f5f9;">'
        '<th style="padding:6px 10px;text-align:left;border:1px solid #e2e8f0;font-size:11px;">Reference</th>'
        '<th style="padding:6px 10px;text-align:left;border:1px solid #e2e8f0;font-size:11px;">Link &amp; Context</th>'
        '</tr></thead>'
        '<tbody>'
        + "".join(rows)
        + '</tbody></table>'
    )
