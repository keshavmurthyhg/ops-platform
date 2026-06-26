import pandas as pd

from common.utils.parsers import (
    parse_mixed_date,
    normalize_priority
)

from common.utils.user_group import (
    build_group_mapping,
    filter_dataframe_by_group,
    get_available_groups
)

# -------------------------------
# NORMALIZE COLUMN NAMES
# -------------------------------
def norm(df):
    df.columns = df.columns.astype(str).str.strip().str.lower()
    return df


# -------------------------------
# SAFE COLUMN FETCH
# -------------------------------
def col(df, *names):
    for n in names:
        if n in df.columns:
            return df[n]
    return None


# -------------------------------
# AZURE
# -------------------------------
def build_azure(df):
    return pd.DataFrame({
        "Number": col(df, "id"),
        "Description": col(df, "title"),
        "Full Description": col(df, "description", "system info", "repro steps"),
        "Resolution Notes": col(df, "resolution", "resolution details", "comments"),
        "Priority": col(df, "release_windchill"),
        "Status": col(df, "state"),
        "Created By": col(df, "created by"),
        "Created Date": col(df, "created date"),
        "Assigned To": col(df, "assigned to"),
        "Resolved Date": col(df, "resolved date"),
        "Source": "AZURE"
    })


# ─────────────────────────────────────────────────
# REFERENCE EXTRACTION HELPERS
# ─────────────────────────────────────────────────
import re as _re

_AZURE_VPA_RE = _re.compile(
    r"https?://dev\.azure\.com/VolvoGroup-DVP/VPA/_workitems/edit/(\d+)/?",
    _re.IGNORECASE,
)
_PTC_ARTICLE_RE = _re.compile(
    r"https?://(?:www\.)?ptc\.com[^\s<>]*?/([A-Za-z]{2,3}\d{4,})/?(?:\b|$)",
    _re.IGNORECASE,
)
_AZURE_BUG_RE = _re.compile(
    r"dev\.azure\.com/VolvoGroup-DVP/VCEWindchillPLM/_workitems/edit/(\d+)",
    _re.IGNORECASE,
)

# Env patterns for fallback (Title suffix matching)
_ENV_TITLE_PATTERNS = [
    (_re.compile(r"[\s\-–]+PROD(?:UCTION)?\s*$", _re.IGNORECASE), "PROD"),
    (_re.compile(r"[\s\-–]+QA\s*$",               _re.IGNORECASE), "QA"),
    (_re.compile(r"[\s\-–]+TEST(?:ING)?\s*$",    _re.IGNORECASE), "TEST"),
    (_re.compile(r"[\s\-–]+UAT\s*$",             _re.IGNORECASE), "UAT"),
    (_re.compile(r"[\s\-–]+DEVA?\s*$",           _re.IGNORECASE), "DEV"),
    (_re.compile(r"[\s\-–]+WC13\s*$",            _re.IGNORECASE), "WC13"),
    # Also match mid-title like "... on PROD server" / "... in QA environment"
    (_re.compile(r"\bPROD(?:UCTION)?(?:\s+(?:server|env(?:ironment)?|instance))?\b", _re.IGNORECASE), "PROD"),
    (_re.compile(r"\bQA(?:\s+(?:server|env(?:ironment)?|instance))?\b",               _re.IGNORECASE), "QA"),
    (_re.compile(r"\bTEST(?:ING)?(?:\s+(?:server|env(?:ironment)?|instance))?\b",    _re.IGNORECASE), "TEST"),
    (_re.compile(r"\bUAT(?:\s+(?:server|env(?:ironment)?|instance))?\b",             _re.IGNORECASE), "UAT"),
    (_re.compile(r"\bDEVA?(?:\s+(?:server|env(?:ironment)?|instance))?\b",           _re.IGNORECASE), "DEV"),
    (_re.compile(r"\bWC13\b",                                                         _re.IGNORECASE), "WC13"),
]

# Tags patterns (column may contain "QA", "TEST", "PROD" etc.)
_ENV_TAG_PATTERNS = [
    (_re.compile(r"\bPROD(?:UCTION)?\b", _re.IGNORECASE), "PROD"),
    (_re.compile(r"\bQA\b",               _re.IGNORECASE), "QA"),
    (_re.compile(r"\bTEST(?:ING)?\b",    _re.IGNORECASE), "TEST"),
    (_re.compile(r"\bUAT\b",             _re.IGNORECASE), "UAT"),
    (_re.compile(r"\bDEVA?\b",           _re.IGNORECASE), "DEV"),
    (_re.compile(r"\bWC13\b",            _re.IGNORECASE), "WC13"),
]


# ─────────────────────────────────────────────────
# AOM USER STORIES LOOKUP TABLE
# Loaded once at module level; maps story_id → env
# ─────────────────────────────────────────────────
_AOM_ENV_MAP = None   # dict: str(id) → env_str


def _load_aom_map():
    """
    Load AOM_user_stories.csv once and build id → env mapping.
    Priority: Tags column → Title suffix/content.
    """
    global _AOM_ENV_MAP
    if _AOM_ENV_MAP is not None:
        return _AOM_ENV_MAP

    import os
    _AOM_ENV_MAP = {}

    paths = [
        "data/AOM_user_stories.csv",
        "data/AOM_user_stories.xlsx",
    ]
    df_aom = None
    for p in paths:
        if os.path.exists(p):
            try:
                if p.endswith(".csv"):
                    df_aom = pd.read_csv(p, dtype=str)
                else:
                    df_aom = pd.read_excel(p, dtype=str)
                break
            except Exception:
                continue

    if df_aom is None:
        return _AOM_ENV_MAP

    # Normalize column names
    df_aom.columns = df_aom.columns.str.strip().str.lower()

    id_col    = next((c for c in df_aom.columns if c in ("id", "work item id", "workitemid")), None)
    title_col = next((c for c in df_aom.columns if c in ("title", "name")), None)
    tags_col  = next((c for c in df_aom.columns if c in ("tags", "tag")), None)

    if id_col is None:
        return _AOM_ENV_MAP

    for _, row in df_aom.iterrows():
        sid = str(row.get(id_col, "")).strip()
        if not sid or sid in ("nan", ""):
            continue

        env = None

        # Priority 1: Title suffix/content — most reliable
        if title_col:
            title_val = str(row.get(title_col, "")).strip()
            if title_val and title_val.lower() not in ("nan", ""):
                for pat, label in _ENV_TITLE_PATTERNS:
                    if pat.search(title_val):
                        env = label
                        break

        # Priority 2: Tags column — fallback if title gives nothing
        if not env and tags_col:
            tag_val = str(row.get(tags_col, "")).strip()
            if tag_val and tag_val.lower() not in ("nan", ""):
                for pat, label in _ENV_TAG_PATTERNS:
                    if pat.search(tag_val):
                        env = label
                        break

        _AOM_ENV_MAP[sid] = env or ""

    return _AOM_ENV_MAP


def _get_env_for_story(story_id):
    """Return environment label for a VPA story ID, or empty string."""
    aom = _load_aom_map()
    return aom.get(str(story_id), "")


def _env_from_context(text):
    """Last-resort: detect env from surrounding note text if AOM has no match."""
    for pat, label in _ENV_TITLE_PATTERNS:
        if pat.search(text):
            return label
    return ""


def _extract_azure_vpa(combined):
    """
    Return list of 'ID|ENV' strings from VPA Azure user story URLs.
    Priority: AOM Title → AOM Tags → surrounding Work Notes / Additional Comments text.
    """
    results = []
    seen = set()
    for m in _AZURE_VPA_RE.finditer(combined):
        sid = m.group(1)
        if sid in seen:
            continue
        seen.add(sid)
        env = _get_env_for_story(sid)
        # Fallback: scan surrounding 400 chars of note text
        if not env:
            ctx = combined[max(0, m.start()-400): m.end()+150]
            env = _env_from_context(ctx)
        results.append(f"{sid}|{env}")
    return results


# ─────────────────────────────────────────────────
# AOM USER STORIES SOURCE
# ─────────────────────────────────────────────────
def build_aom(df):
    """Build AOM user stories as a searchable source (Source = AOM)."""
    env_series = []
    id_col_name = next((c for c in df.columns if c == "id"), None)
    title_col_name = next((c for c in df.columns if c == "title"), None)
    tags_col_name  = next((c for c in df.columns if c == "tags"), None)

    n = len(df)
    for i in range(n):
        env = None
        if title_col_name is not None:
            title_val = str(df[title_col_name].iloc[i]).strip()
            if title_val and title_val.lower() not in ("nan", ""):
                for pat, label in _ENV_TITLE_PATTERNS:
                    if pat.search(title_val):
                        env = label
                        break
        if not env and tags_col_name is not None:
            tag_val = str(df[tags_col_name].iloc[i]).strip()
            if tag_val and tag_val.lower() not in ("nan", ""):
                for pat, label in _ENV_TAG_PATTERNS:
                    if pat.search(tag_val):
                        env = label
                        break
        env_series.append(env or "")

    return pd.DataFrame({
        "Number":           col(df, "id"),
        "Description":      col(df, "title"),
        "Full Description": col(df, "title"),
        "Resolution Notes": None,
        "Environment":      env_series,
        "Priority":         col(df, "priority", "tags"),
        "Status":           col(df, "state"),
        "Created By":       col(df, "created by"),
        "Created Date":     col(df, "created date"),
        "Assigned To":      col(df, "assigned to"),
        "Resolved Date":    col(df, "resolved date"),
        "Source":           "AOM"
    })


def _extract_ptc_articles(combined):
    """Return list of article IDs from PTC article URLs."""
    results = []
    seen = set()
    for m in _PTC_ARTICLE_RE.finditer(combined):
        aid = m.group(1).upper()
        if aid in seen:
            continue
        seen.add(aid)
        results.append(aid)
    return results


def _extract_azure_bugs(resolution_text):
    """Return list of VCEWindchillPLM bug IDs from resolution notes."""
    results = []
    seen = set()
    if not resolution_text:
        return results
    for m in _AZURE_BUG_RE.finditer(str(resolution_text)):
        bid = m.group(1)
        if bid not in seen:
            seen.add(bid)
            results.append(bid)
    return results


# -------------------------------
# SNOW
# -------------------------------
def build_snow(df):

    resolution_col   = col(df, "close notes", "resolution notes", "resolution")
    work_notes_col   = col(df, "work notes", "work_notes")
    add_comments_col = col(df, "additional comments", "additional_comments", "comments")

    def _safe_str(v):
        return "" if (v is None or (isinstance(v, float) and v != v)) else str(v)

    def _combined_notes(row_idx):
        parts = []
        if work_notes_col is not None:
            parts.append(_safe_str(work_notes_col.iloc[row_idx]))
        if add_comments_col is not None:
            parts.append(_safe_str(add_comments_col.iloc[row_idx]))
        if resolution_col is not None:
            parts.append(_safe_str(resolution_col.iloc[row_idx]))
        return "\n".join(p for p in parts if p)

    n = len(df)

    azure_bug_list, vpa_list, ptc_list = [], [], []

    for i in range(n):
        res_text  = _safe_str(resolution_col.iloc[i]) if resolution_col is not None else ""
        combined  = _combined_notes(i)

        azure_bug_list.append(", ".join(_extract_azure_bugs(res_text)))
        vpa_list.append(", ".join(_extract_azure_vpa(combined)))
        ptc_list.append(", ".join(_extract_ptc_articles(combined)))

    import pandas as _pd

    return _pd.DataFrame({
        "Number":           col(df, "number"),
        "Description":      col(df, "short description", "description"),
        "Full Description": col(df, "description", "detailed description"),
        "Resolution Notes": resolution_col,
        "Vendor Ticket":    col(df, "u_vendor_reference", "vendor ticket",
                                "vendor_ticket", "vendor reference",
                                "u_vendor_ticket"),
        "Azure Bug":        azure_bug_list,
        "Azure User Story": vpa_list,
        "PTC Articles":     ptc_list,
        "Priority":         col(df, "priority"),
        "Status":           col(df, "incident state"),
        "Created By":       col(df, "opened by", "created by"),
        "Created Date":     col(df, "created", "date"),
        "Assigned To":      col(df, "assigned to"),
        "Resolved Date":    col(df, "resolved"),
        "Source":           "SNOW"
    })


# -------------------------------
# PTC
# -------------------------------
def build_ptc(df):
    return pd.DataFrame({
        "Number": col(df, "case number"),
        "Description": col(df, "subject"),
        "Full Description": col(df, "description", "problem description"),
        "Resolution Notes": col(df, "resolution", "resolution notes", "solution"),
        "Priority": col(df, "severity"),
        "Status": col(df, "status"),
        "Created By": col(df, "case contact"),
        "Created Date": col(df, "created date"),
        "Assigned To": col(df, "case assignee"),
        "Resolved Date": col(df, "resolved date"),
        "Source": "PTC"
    })


# -------------------------------
# LOAD DATA
# -------------------------------
def load_data():

    # Reset AOM cache on each data reload so new AOM file is picked up
    global _AOM_ENV_MAP
    _AOM_ENV_MAP = None

    import os, logging as _log
    _dl_log = _log.getLogger("search")

    try:
        azure = pd.read_csv("data/Azure.csv")
        _dl_log.info(f"Loaded Azure.csv — {len(azure)} rows")

        snow = pd.read_excel("data/Snow.xlsx", engine="openpyxl")
        _dl_log.info(f"Loaded Snow.xlsx — {len(snow)} rows")

        ptc = pd.read_csv("data/Ptc.csv", index_col=False, engine="python")
        ptc = ptc.reset_index(drop=True)
        _dl_log.info(f"Loaded Ptc.csv — {len(ptc)} rows")

    except Exception as e:
        _dl_log.error(f"Data load failed: {e}", exc_info=True)
        return pd.DataFrame(), {}

    # Load AOM user stories (optional — skip if file missing)
    aom_frames = []
    for aom_path in ("data/AOM_user_stories.csv", "data/AOM_user_stories.xlsx"):
        if os.path.exists(aom_path):
            try:
                aom_raw = (pd.read_csv(aom_path, dtype=str) if aom_path.endswith(".csv")
                           else pd.read_excel(aom_path, dtype=str))
                aom_raw = norm(aom_raw)
                aom_frames.append(build_aom(aom_raw))
                _dl_log.info(f"Loaded {aom_path} — {len(aom_raw)} rows")
            except Exception as e:
                _dl_log.warning(f"AOM load skipped ({aom_path}): {e}")
            break

    azure = norm(azure)
    snow  = norm(snow)
    ptc   = norm(ptc)

    frames = [build_azure(azure), build_snow(snow), build_ptc(ptc)] + aom_frames

    df = pd.concat(frames, ignore_index=True)

    df = df.reset_index(drop=True)

    # ---------- DATE NORMALIZATION ----------
    for col_name in ["Created Date", "Resolved Date"]:
        if col_name in df.columns:
            df[col_name] = df[col_name].apply(parse_mixed_date)

    # ---------- PRIORITY NORMALIZATION ----------

    if "Priority" in df.columns:

        df["Priority"] = df["Priority"].apply(
            normalize_priority
        )

    df = df.fillna("")

    from datetime import datetime
    info = datetime.now().strftime("%d-%b-%Y %H:%M")

    return df, info


# -------------------------------
# LOAD GROUP FILTERS
# -------------------------------
def load_group_filters():

    df, _ = load_data()

    mapping_df = build_group_mapping(df)

    groups = get_available_groups(
        mapping_df
    )

    return groups


def load_group_users():

    import pandas as pd

    from pathlib import Path

    # Try user_group_mapping.csv first, fall back to group_mapping.csv
    csv_path = Path("data") / "user_group_mapping.csv"

    if not csv_path.exists():
        csv_path = Path("data") / "group_mapping.csv"

    if not csv_path.exists():
        return []

    df = pd.read_csv(csv_path)

    users = set()

    if "Name" in df.columns:

        df["Name"] = (
            df["Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        users.update(
            df["Name"]
            .tolist()
        )

    return sorted(
        x for x in users if x
    )