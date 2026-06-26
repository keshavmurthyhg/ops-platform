# =============================================================================
#  EMAIL DIGEST PREPARER  v2
#  operations_center/module/email_digest.py
#
#  Builds ready-to-send HTML email digests and saves to:
#    ops-platform/data/email_digests/YYYY-MM-DD/<type>/
#
#  Rules:
#   - Daily digests  : filter to TODAY + YESTERDAY only
#   - Weekly summary : Monday–Sunday window, stored in same folder
# =============================================================================

import os
import json
import logging
from datetime import datetime, timedelta, date
from pathlib import Path

log = logging.getLogger("email_digest")

# ── Config ────────────────────────────────────────────────────────────────────
FROM_ADDR      = "keshavamurthy.hg@consultant.volvo.com"
TO_ADDR        = "keshavamurthy.hg@consultant.volvo.com"
DIGEST_BASE    = Path("data") / "email_digests"

DIGEST_TYPES = [
    "integration_failures",
    "wm_transactions",
    "wvs_queue",
    "worker_stats",
    "incidents",
    "azure_bugs",
    "ptc_cases",
    "support_emails",
    "weekly_summary",       # Monday–Sunday rolling window
]

THRESHOLDS = {
    "failure_total"      : 5,
    "failure_prod"       : 1,
    "support_pending"    : 3,
    "incident_on_hold"   : 2,
    "azure_new"          : 3,
    "ptc_open"           : 3,
    "wm_tx_failed"       : 3,
    "wm_worker_fail_pct" : 10.0,
    "wm_wvs_failed"      : 2,
}


# ─────────────────────────────────────────────────────────────────────────────
#  Date window helpers
# ─────────────────────────────────────────────────────────────────────────────

def _today():
    return date.today()

def _yesterday():
    return date.today() - timedelta(days=1)

def _week_window():
    """Return (monday, sunday) of the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday

def _parse_date(val):
    """
    Try to parse various date strings → date object. Returns None on failure.
    Handles: "2026-06-24 07:28:22", "2026-06-24", "24-Jun-2026 04:32 CEST",
             "2026-05-05 13:19 CEST", "24/06/2026"
    """
    if not val or str(val).strip() in ("", "N/A", "—", "nan"):
        return None
    s = str(val).strip()
    # Strip timezone suffixes
    for tz in (" CEST", " CET", " UTC", " GMT"):
        s = s.replace(tz, "")
    s = s.strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def _is_recent(val, days=2):
    """Return True if val falls within today or the last `days` days."""
    d = _parse_date(val)
    if d is None:
        return False
    cutoff = date.today() - timedelta(days=days - 1)
    return d >= cutoff

def _is_this_week(val):
    """Return True if val falls within the current Mon–Sun week."""
    d = _parse_date(val)
    if d is None:
        return False
    monday, sunday = _week_window()
    return monday <= d <= sunday

def _filter_recent(rows, *date_keys, days=2):
    """Filter rows keeping only those whose date field falls within `days`."""
    filtered = [
        r for r in rows
        if _is_recent(_vf(r, *date_keys), days=days)
    ]
    return filtered if filtered else []

def _filter_week(rows, *date_keys):
    return [r for r in rows if _is_this_week(_vf(r, *date_keys))]


# ─────────────────────────────────────────────────────────────────────────────
#  Field value helpers
# ─────────────────────────────────────────────────────────────────────────────

def _vf(row, *keys):
    """Return first non-empty value for any of the given keys."""
    for k in keys:
        v = row.get(k, "")
        if v is not None and str(v).strip() not in ("", "nan", "None", "N/A"):
            return str(v).strip()
    return ""

def _safe(val, fallback="—"):
    v = str(val).strip() if val is not None else ""
    return v if v and v not in ("nan", "None", "N/A") else fallback

def _truncate(val, n=80):
    v = _safe(val)
    return v[:n] + "…" if len(v) > n else v


# ─────────────────────────────────────────────────────────────────────────────
#  HTML helpers
# ─────────────────────────────────────────────────────────────────────────────

_STYLE = """<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:Segoe UI,Arial,sans-serif; background:#f4f6f9;
       padding:20px; color:#374151; font-size:13px; }
.wrap { max-width:960px; margin:auto; }
.header { background:linear-gradient(135deg,#1e3a5f,#1a2e4a); color:#fff;
          padding:18px 24px; border-radius:10px 10px 0 0; }
.header h1 { font-size:17px; font-weight:700; }
.header .meta { font-size:11px; color:#93c5fd; margin-top:5px;
                display:flex; gap:16px; flex-wrap:wrap; }
.body { background:#fff; padding:20px 24px;
        border:1px solid #e5e7eb; border-top:none; }
.kpi-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:18px; }
.kpi-box { flex:1; min-width:80px; background:#f9fafb;
           border:1px solid #e5e7eb; border-radius:8px;
           padding:10px 14px; text-align:center; }
.kpi-box-val { font-size:22px; font-weight:800; }
.kpi-box-lbl { font-size:9px; font-weight:700; text-transform:uppercase;
               letter-spacing:.05em; color:#6b7280; margin-top:2px; }
.kpi-box.alert { border-color:#fca5a5; background:#fef2f2; }
.section { margin-bottom:22px; }
.section-title { font-size:13px; font-weight:700; color:#374151;
                 border-left:4px solid #f28c38; padding-left:10px;
                 margin-bottom:10px; }
.alert-banner { background:#fef2f2; border:1px solid #fca5a5;
                border-radius:8px; padding:10px 14px; margin-bottom:14px;
                font-size:12px; color:#dc2626; line-height:1.6; }
.alert-banner ul { margin:6px 0 0 18px; }
.date-window { background:#eff6ff; border:1px solid #bfdbfe;
               border-radius:6px; padding:6px 14px; margin-bottom:14px;
               font-size:11px; color:#1e40af; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { background:#f9fafb; padding:7px 10px; text-align:left;
     font-weight:700; color:#374151; border-bottom:2px solid #e5e7eb;
     white-space:nowrap; }
td { padding:6px 10px; border-bottom:1px solid #f3f4f6; vertical-align:top; }
tr:hover td { background:#f9fafb; }
.badge { display:inline-block; padding:2px 7px; border-radius:999px;
         font-size:10px; font-weight:700; }
.red   { background:#fef2f2; color:#dc2626; }
.amber { background:#fffbeb; color:#d97706; }
.green { background:#f0fdf4; color:#16a34a; }
.blue  { background:#eff6ff; color:#2563eb; }
.gray  { background:#f3f4f6; color:#6b7280; }
.no-records { color:#9ca3af; text-align:center; padding:18px;
              font-style:italic; }
.breakdown-table td:last-child { font-weight:700; }
.footer { background:#f9fafb; padding:10px 24px;
          border-radius:0 0 10px 10px; border:1px solid #e5e7eb;
          border-top:none; font-size:11px; color:#9ca3af; }
.footer-row { display:flex; justify-content:space-between; flex-wrap:wrap; gap:6px; }
</style>"""


def _badge(val, cls="gray"):
    return f'<span class="badge {cls}">{_safe(val)}</span>'

def _status_badge(val):
    s = str(val).lower()
    if any(x in s for x in ("fail","error","critical","hold")):   return _badge(val, "red")
    if any(x in s for x in ("progress","pending","new","active","executing","open")): return _badge(val, "amber")
    if any(x in s for x in ("success","complete","resolved","closed","ready")):       return _badge(val, "green")
    return _badge(val, "gray")

def _kpi(val, label, color, alert=False):
    cls = "kpi-box alert" if alert else "kpi-box"
    return (f'<div class="{cls}">'
            f'<div class="kpi-box-val" style="color:{color};">{val}</div>'
            f'<div class="kpi-box-lbl">{label}</div></div>')

def _hdr(title, subtitle, now, date_window=""):
    window_html = f'<span>📅 {date_window}</span>' if date_window else ''
    return f"""<div class="header">
  <h1>{title}</h1>
  <div class="meta">
    <span>🕐 {now}</span>
    {window_html}
    <span>📤 {FROM_ADDR}</span>
    <span>📥 {TO_ADDR}</span>
    <span>📋 {subtitle}</span>
  </div>
</div>"""

def _ftr(now, dtype):
    return (f'<div class="footer"><div class="footer-row">'
            f'<span>Ops Platform · {dtype.replace("_"," ").title()} Digest</span>'
            f'<span>Generated: {now}</span>'
            f'</div></div>')

def _wrap(hdr, body_html, ftr):
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8">{_STYLE}</head>'
            f'<body><div class="wrap">{hdr}'
            f'<div class="body">{body_html}</div>'
            f'{ftr}</div></body></html>')

def _tbl(rows, cols, max_rows=200):
    """
    cols: list of (header, key1, key2, ...) or (header, key1, ..., renderer_fn)
    renderer_fn(raw_val, row) -> html string
    """
    head = "<thead><tr>" + "".join(f"<th>{c[0]}</th>" for c in cols) + "</tr></thead>"
    if not rows:
        return f"{head}<tbody><tr><td colspan='{len(cols)}' class='no-records'>No records in selected date range.</td></tr></tbody>"
    body = "<tbody>"
    for r in rows[:max_rows]:
        body += "<tr>"
        for col in cols:
            keys = [k for k in col[1:] if not callable(k)]
            fn   = next((k for k in col[1:] if callable(k)), None)
            raw  = _vf(r, *keys)
            body += f"<td>{fn(raw, r) if fn else _safe(raw)}</td>"
        body += "</tr>"
    if len(rows) > max_rows:
        body += (f"<tr><td colspan='{len(cols)}' style='color:#9ca3af;"
                 f"font-style:italic;padding:6px 10px;'>…and {len(rows)-max_rows} more rows</td></tr>")
    return f"<table>{head}{body}</tbody></table>"

def _breakdown(rows, key, title="Count"):
    counts = {}
    for r in rows:
        k = _vf(r, key) or "Unknown"
        counts[k] = counts.get(k, 0) + 1
    if not counts:
        return "<p class='no-records'>No data.</p>"
    body = "".join(f"<tr><td>{k}</td><td><strong>{v}</strong></td></tr>"
                   for k, v in sorted(counts.items(), key=lambda x: -x[1]))
    return (f"<table class='breakdown-table'>"
            f"<thead><tr><th>{key.replace('_',' ').title()}</th><th>{title}</th></tr></thead>"
            f"<tbody>{body}</tbody></table>")


# ─────────────────────────────────────────────────────────────────────────────
#  DAILY DIGEST BUILDERS  (filter: today + yesterday only)
# ─────────────────────────────────────────────────────────────────────────────

def _build_integration_failures(failure_data, now, date_label):
    T   = THRESHOLDS
    # Filter to today + yesterday only
    rows = _filter_recent(failure_data, "Failure Time", "failure_time", days=2)

    total = len(rows)
    prod  = [r for r in rows if _vf(r,"Environment","environment").upper() == "PROD"]
    devc  = [r for r in rows if _vf(r,"Environment","environment").upper() in ("DEVC","DEVA")]
    devb  = [r for r in rows if _vf(r,"Environment","environment").upper() == "DEVB"]
    unk   = [r for r in rows if _vf(r,"Environment","environment").upper() in ("UNKNOWN","")]

    alerts = []
    if total      >= T["failure_total"]:  alerts.append(f"Total failures ({total}) exceed threshold ({T['failure_total']})")
    if len(prod)  >= T["failure_prod"]:   alerts.append(f"PROD failures ({len(prod)}) exceed threshold ({T['failure_prod']})")

    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(total,       "Total",   "#ef4444", total >= T["failure_total"]) +
        _kpi(len(prod),   "PROD",    "#f59e0b", len(prod) >= T["failure_prod"]) +
        _kpi(len(devc),   "DEVC",    "#3b82f6") +
        _kpi(len(devb),   "DEVB",    "#8b5cf6") +
        _kpi(len(unk),    "Unknown", "#6b7280")
    )

    body = f"""
{banner}
<div class="date-window">📅 Showing: {date_label} (today + yesterday only)</div>
<div class="section">
  <div class="section-title">Summary KPIs</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">By Integration Type</div>
  {_breakdown(rows, "Integration")}
</div>
<div class="section">
  <div class="section-title">All Failures — Latest First</div>
  {_tbl(sorted(rows, key=lambda r: _vf(r,"Failure Time","failure_time"), reverse=True), [
      ("Failure Time",  "Failure Time",    "failure_time"),
      ("Integration",   "Integration",     "Target",        "target"),
      ("Object Number", "Object Number",   "Object",        "object"),
      ("Error Message", "Error Message",   "Notes",         "notes",
          lambda v,r: f'<span title="{v}">{_truncate(v,90)}</span>'),
      ("Environment",   "Environment",     "environment",
          lambda v,r: _status_badge(v) if v and v != "—" else "—"),
      ("WC Server",     "Windchill Server","wc_server"),
  ])}
</div>"""

    subject = f"[OPS] Integration Failures — {total} today/yesterday ({len(prod)} PROD) — {date_label}"
    return subject, body, bool(alerts)


def _build_wm_transactions(transactions, now, date_label):
    T    = THRESHOLDS
    rows = _filter_recent(transactions, "time", "Time", days=2)
    failed  = [r for r in rows if "FAIL" in _vf(r,"status","Status","").upper()
                                or "ERR"  in _vf(r,"status","Status","").upper()]
    success = [r for r in rows if "SUCC" in _vf(r,"status","Status","").upper()
                                or "COMP" in _vf(r,"status","Status","").upper()]

    alerts = []
    if len(failed) >= T["wm_tx_failed"]:
        alerts.append(f"Failed transactions ({len(failed)}) exceed threshold ({T['wm_tx_failed']})")
    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(len(rows),    "Total",   "#f28c38") +
        _kpi(len(failed),  "Failed",  "#ef4444", len(failed) >= T["wm_tx_failed"]) +
        _kpi(len(success), "Success", "#16a34a") +
        _kpi(len(rows)-len(failed)-len(success), "Other", "#6b7280")
    )

    body = f"""
{banner}
<div class="date-window">📅 Showing: {date_label} (today + yesterday only)</div>
<div class="section">
  <div class="section-title">Summary KPIs</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">By Target System</div>
  {_breakdown(failed or rows, "target")}
</div>
<div class="section">
  <div class="section-title">Failed Transactions</div>
  {_tbl(failed, [
      ("Time",     "time",    "Time"),
      ("Target",   "target",  "Target"),
      ("Action",   "action",  "Action"),
      ("Status",   "status",  "Status",   lambda v,r: _status_badge(v)),
      ("Object",   "object",  "Object"),
      ("State",    "state",   "State"),
      ("Attempts", "attempts","Attempts"),
      ("Notes",    "notes",   "Notes",    lambda v,r: f'<span title="{v}">{_truncate(v,70)}</span>'),
  ])}
</div>"""

    subject = f"[WM] Transactions — {len(failed)} failed / {len(rows)} today+yesterday — {date_label}"
    return subject, body, bool(alerts)


def _build_wvs_queue(wvs_queue, now, date_label):
    T      = THRESHOLDS
    # WVS queue is a snapshot - no date filter, show all current state
    ready  = [r for r in wvs_queue if "READY"  in _vf(r,"status","Status","").upper()]
    exec_  = [r for r in wvs_queue if "EXECUT" in _vf(r,"status","Status","").upper()]
    failed = [r for r in wvs_queue if "FAIL"   in _vf(r,"status","Status","").upper()
                                   or "ERR"    in _vf(r,"status","Status","").upper()]

    alerts = []
    if len(failed) >= T["wm_wvs_failed"]:
        alerts.append(f"WVS failed jobs ({len(failed)}) exceed threshold ({T['wm_wvs_failed']})")
    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(len(wvs_queue), "Total Jobs", "#0ea5e9") +
        _kpi(len(ready),     "Ready",      "#16a34a") +
        _kpi(len(exec_),     "Executing",  "#f59e0b") +
        _kpi(len(failed),    "Failed",     "#ef4444", len(failed) >= T["wm_wvs_failed"])
    )

    body = f"""
{banner}
<div class="date-window">📅 Current snapshot as of {now}</div>
<div class="section">
  <div class="section-title">WVS Queue Status</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">All Jobs</div>
  {_tbl(wvs_queue, [
      ("Queue",   "queue",   "Queue"),
      ("Job",     "job",     "Job"),
      ("Status",  "status",  "Status",  lambda v,r: _status_badge(v)),
      ("Name",    "name",    "Name"),
      ("Version", "version", "Version"),
      ("User",    "user",    "User"),
  ])}
</div>"""

    subject = f"[WM] WVS Queue — {len(wvs_queue)} jobs ({len(ready)} ready, {len(exec_)} executing, {len(failed)} failed) — {now}"
    return subject, body, bool(alerts)


def _build_worker_stats(worker_stats, now, date_label):
    T    = THRESHOLDS
    # Worker stats are cumulative totals - show all, highlight high fail%
    high_fail = []
    for w in worker_stats:
        try:
            pct = float(str(w.get("failed_pct","0")).replace("%","").strip() or "0")
            if pct >= T["wm_worker_fail_pct"]:
                high_fail.append((w, pct))
        except Exception:
            pass

    total_jobs = sum(_safe_int(w.get("total",0)) for w in worker_stats)
    total_fail = sum(_safe_int(w.get("failed",0)) for w in worker_stats)
    avg_pct    = round(total_fail / total_jobs * 100, 2) if total_jobs else 0

    alerts = []
    if high_fail:
        names = ", ".join(_vf(w,"name","Name") for w,_ in high_fail)
        alerts.append(f"High fail rate workers (≥{T['wm_worker_fail_pct']}%): {names}")
    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(len(worker_stats), "Workers",     "#374151") +
        _kpi(total_jobs,        "Total Jobs",  "#0ea5e9") +
        _kpi(total_fail,        "Total Failed","#ef4444") +
        _kpi(f"{avg_pct}%",     "Avg Fail %",  "#f59e0b")
    )

    def _pct_cell(v, r):
        try:
            pct = float(str(v).replace("%","").strip() or "0")
            c = "#dc2626" if pct >= T["wm_worker_fail_pct"] else ("#d97706" if pct >= 5 else "#16a34a")
            return f'<strong style="color:{c};">{v}</strong>'
        except Exception:
            return _safe(v)

    sorted_workers = sorted(worker_stats,
        key=lambda w: float(str(w.get("failed_pct","0")).replace("%","").strip() or "0"),
        reverse=True)

    body = f"""
{banner}
<div class="date-window">📅 Cumulative stats as of {now}</div>
<div class="section">
  <div class="section-title">Worker Summary</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">All Workers — Sorted by Fail %</div>
  {_tbl(sorted_workers, [
      ("Worker",  "name",       "Name"),
      ("Total",   "total",      "Total"),
      ("Failed",  "failed",     "Failed"),
      ("Success", "success",    "Success"),
      ("Fail %",  "failed_pct", _pct_cell),
  ])}
</div>"""

    subject = f"[WM] Worker Stats — {len(worker_stats)} workers, {total_fail} failures ({avg_pct}% avg) — {date_label}"
    return subject, body, bool(alerts)


def _safe_int(val):
    try: return int(str(val).replace(",","").strip() or "0")
    except Exception: return 0


def _build_incidents(incident_data, now, date_label):
    T       = THRESHOLDS
    # Incidents are open items - no date filter, show all active
    on_hold = [r for r in incident_data if _vf(r,"Status","status") == "On Hold"]
    in_prog = [r for r in incident_data if _vf(r,"Status","status") == "In Progress"]
    resolved= [r for r in incident_data if _vf(r,"Status","status") == "Resolved"]

    alerts = []
    if len(on_hold) >= T["incident_on_hold"]:
        alerts.append(f"Incidents on hold ({len(on_hold)}) exceed threshold ({T['incident_on_hold']})")
    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(len(incident_data), "Total",       "#f28c38") +
        _kpi(len(on_hold),       "On Hold",     "#ef4444", len(on_hold) >= T["incident_on_hold"]) +
        _kpi(len(in_prog),       "In Progress", "#3b82f6") +
        _kpi(len(resolved),      "Resolved",    "#16a34a")
    )

    body = f"""
{banner}
<div class="date-window">📅 All open incidents as of {now}</div>
<div class="section">
  <div class="section-title">Incident Summary</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">All Incidents</div>
  {_tbl(incident_data, [
      ("Number",      "Number",          "number"),
      ("Description", "Description",     "short_description"),
      ("Assigned To", "Assigned To",     "assigned_to"),
      ("Priority",    "Priority",        "priority"),
      ("Status",      "Status",          "status",  lambda v,r: _status_badge(v)),
  ])}
</div>"""

    subject = f"[OPS] Incidents — {len(incident_data)} total, {len(on_hold)} on hold — {date_label}"
    return subject, body, bool(alerts)


def _build_azure_bugs(azure_data, now, date_label):
    T      = THRESHOLDS
    new_   = [r for r in azure_data if _vf(r,"Status","status") == "New"]
    active = [r for r in azure_data if _vf(r,"Status","status") == "Active"]
    closed = [r for r in azure_data if _vf(r,"Status","status") in ("Closed","Resolved")]

    alerts = []
    if len(new_) >= T["azure_new"]:
        alerts.append(f"New Azure bugs ({len(new_)}) exceed threshold ({T['azure_new']})")
    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(len(azure_data), "Total",  "#0ea5e9") +
        _kpi(len(new_),       "New",    "#8b5cf6", len(new_) >= T["azure_new"]) +
        _kpi(len(active),     "Active", "#f59e0b") +
        _kpi(len(closed),     "Closed", "#16a34a")
    )

    body = f"""
{banner}
<div class="date-window">📅 All active Azure bugs as of {now}</div>
<div class="section">
  <div class="section-title">Azure Bug Summary</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">All Azure Bugs</div>
  {_tbl(azure_data, [
      ("Number",      "Number",      "number"),
      ("Description", "Description", "title"),
      ("Assigned To", "Assigned To", "assigned_to"),
      ("Priority",    "Priority",    "priority"),
      ("Status",      "Status",      "status", lambda v,r: _status_badge(v)),
  ])}
</div>"""

    subject = f"[OPS] Azure Bugs — {len(azure_data)} total, {len(new_)} new — {date_label}"
    return subject, body, bool(alerts)


def _build_ptc_cases(ptc_data, now, date_label):
    T    = THRESHOLDS
    open_= [r for r in ptc_data if _vf(r,"Status","status") not in ("Closed","Resolved","Cancelled")]
    closed=[r for r in ptc_data if _vf(r,"Status","status") in ("Closed","Resolved","Cancelled")]

    alerts = []
    if len(open_) >= T["ptc_open"]:
        alerts.append(f"Open PTC cases ({len(open_)}) exceed threshold ({T['ptc_open']})")
    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(len(ptc_data), "Total",  "#8b5cf6") +
        _kpi(len(open_),    "Open",   "#f59e0b", len(open_) >= T["ptc_open"]) +
        _kpi(len(closed),   "Closed", "#16a34a")
    )

    body = f"""
{banner}
<div class="date-window">📅 All PTC cases as of {now}</div>
<div class="section">
  <div class="section-title">PTC Case Summary</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">All PTC Cases</div>
  {_tbl(ptc_data, [
      ("Number",      "Number",      "number"),
      ("Description", "Description", "subject"),
      ("Priority",    "Priority",    "severity", "priority"),
      ("Status",      "Status",      "status",   lambda v,r: _status_badge(v)),
  ])}
</div>"""

    subject = f"[OPS] PTC Cases — {len(ptc_data)} total, {len(open_)} open — {date_label}"
    return subject, body, bool(alerts)


def _build_support_emails(support_data, now, date_label):
    T       = THRESHOLDS
    # Filter to today + yesterday
    rows    = _filter_recent(support_data, "date_received", "Date Received", "Date", days=2)
    pending = [r for r in rows if "Action Required" in _vf(r,"category","Categories","Category")]

    alerts = []
    if len(pending) >= T["support_pending"]:
        alerts.append(f"Action required emails ({len(pending)}) exceed threshold ({T['support_pending']})")
    banner = (f'<div class="alert-banner">⚠ <strong>Alert:</strong><ul>'
              + "".join(f"<li>{a}</li>" for a in alerts) + "</ul></div>") if alerts else ""

    kpis = (
        _kpi(len(rows),    "Total",          "#3b82f6") +
        _kpi(len(pending), "Action Required","#ef4444", len(pending) >= T["support_pending"]) +
        _kpi(len(rows)-len(pending), "Other","#6b7280")
    )

    body = f"""
{banner}
<div class="date-window">📅 Showing: {date_label} (today + yesterday only)</div>
<div class="section">
  <div class="section-title">Support Email Summary</div>
  <div class="kpi-row">{kpis}</div>
</div>
<div class="section">
  <div class="section-title">{'Action Required Emails' if pending else 'All Support Emails'}</div>
  {_tbl(pending or rows, [
      ("Date",     "date_received", "Date Received", "Date"),
      ("From",     "name",          "Name",          "From"),
      ("Subject",  "subject",       "Subject",
          lambda v,r: f'<span title="{v}">{_truncate(v,100)}</span>'),
      ("Category", "category",      "Categories",    "Category"),
  ])}
</div>"""

    subject = f"[OPS] Support Emails — {len(rows)} today/yesterday, {len(pending)} action required — {date_label}"
    return subject, body, bool(alerts)


# ─────────────────────────────────────────────────────────────────────────────
#  WEEKLY SUMMARY (Mon–Sun)
# ─────────────────────────────────────────────────────────────────────────────

def _build_weekly_summary(support_data, failure_data, incident_data,
                          azure_data, ptc_data, transactions,
                          wvs_queue, worker_stats, now):
    monday, sunday = _week_window()
    week_label = f"{monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"

    # Filter date-based trackers to this week
    fail_w    = _filter_week(failure_data,  "Failure Time",  "failure_time")
    support_w = _filter_week(support_data,  "date_received", "Date Received", "Date")
    tx_w      = _filter_week(transactions,  "time",          "Time")

    # Non-date trackers: show current state
    fail_prod  = len([r for r in fail_w  if _vf(r,"Environment","environment").upper() == "PROD"])
    sup_pend   = len([r for r in support_w if "Action Required" in _vf(r,"category","Categories","Category")])
    inc_hold   = len([r for r in incident_data if _vf(r,"Status","status") == "On Hold"])
    az_new     = len([r for r in azure_data    if _vf(r,"Status","status") == "New"])
    ptc_open   = len([r for r in ptc_data      if _vf(r,"Status","status") not in ("Closed","Resolved","Cancelled")])
    tx_failed  = len([r for r in tx_w   if "FAIL" in _vf(r,"status","Status","").upper()])
    wvs_failed = len([r for r in wvs_queue if "FAIL" in _vf(r,"status","Status","").upper()])

    kpis = (
        _kpi(len(fail_w),        "Failures (week)",  "#ef4444") +
        _kpi(fail_prod,          "PROD Fail",        "#f59e0b") +
        _kpi(len(support_w),     "Support (week)",   "#3b82f6") +
        _kpi(sup_pend,           "Action Req",       "#ef4444") +
        _kpi(len(incident_data), "Incidents",        "#f28c38") +
        _kpi(inc_hold,           "On Hold",          "#ef4444") +
        _kpi(len(azure_data),    "Azure Bugs",       "#0ea5e9") +
        _kpi(az_new,             "New Bugs",         "#8b5cf6") +
        _kpi(len(ptc_data),      "PTC Cases",        "#8b5cf6") +
        _kpi(ptc_open,           "PTC Open",         "#f59e0b") +
        _kpi(len(tx_w),          "WM Tx (week)",     "#f28c38") +
        _kpi(tx_failed,          "WM Tx Failed",     "#ef4444") +
        _kpi(len(wvs_queue),     "WVS Jobs",         "#0ea5e9") +
        _kpi(wvs_failed,         "WVS Failed",       "#ef4444") +
        _kpi(len(worker_stats),  "Workers",          "#374151")
    )

    def _mini(rows, cols, n=8):
        return _tbl(rows[:n], cols, n)

    sections = [
        ("Integration Failures this week", "#ef4444",
         _mini(sorted(fail_w, key=lambda r: _vf(r,"Failure Time","failure_time"), reverse=True), [
             ("Failure Time","Failure Time","failure_time"),
             ("Integration","Integration","Target","target"),
             ("Object","Object Number","Object","object"),
             ("Error","Error Message","Notes","notes",
              lambda v,r: f'<span title="{v}">{_truncate(v,60)}</span>'),
             ("Env","Environment","environment",
              lambda v,r: _status_badge(v) if v and v!="—" else "—"),
             ("Server","Windchill Server","wc_server"),
         ])),
        ("Support Emails — Action Required this week", "#3b82f6",
         _mini([r for r in support_w if "Action Required" in _vf(r,"category","Categories","Category")], [
             ("Date","date_received","Date Received","Date"),
             ("From","name","Name"),
             ("Subject","subject","Subject",
              lambda v,r: f'<span title="{v}">{_truncate(v,90)}</span>'),
             ("Category","category","Categories","Category"),
         ])),
        ("Incidents (current)", "#f28c38",
         _mini(incident_data, [
             ("Number","Number","number"),
             ("Description","Description","short_description"),
             ("Priority","Priority","priority"),
             ("Status","Status","status",lambda v,r:_status_badge(v)),
         ])),
        ("Azure Bugs (current)", "#0ea5e9",
         _mini(azure_data, [
             ("Number","Number","number"),
             ("Description","Description","title"),
             ("Priority","Priority","priority"),
             ("Status","Status","status",lambda v,r:_status_badge(v)),
         ])),
        ("PTC Cases (current)", "#8b5cf6",
         _mini(ptc_data, [
             ("Number","Number","number"),
             ("Description","Description","subject"),
             ("Priority","Priority","severity","priority"),
             ("Status","Status","status",lambda v,r:_status_badge(v)),
         ])),
        ("WM Transactions — Failed this week", "#f28c38",
         _mini([r for r in tx_w if "FAIL" in _vf(r,"status","Status","").upper()], [
             ("Time","time"),("Target","target"),("Action","action"),
             ("Status","status",lambda v,r:_status_badge(v)),
             ("Object","object"),("Notes","notes",
              lambda v,r: f'<span title="{v}">{_truncate(v,60)}</span>'),
         ])),
        ("WVS Queue (current)", "#0ea5e9",
         _mini(wvs_queue, [
             ("Queue","queue"),("Job","job"),
             ("Status","status",lambda v,r:_status_badge(v)),
             ("Name","name"),("User","user"),
         ])),
        ("Worker Stats", "#374151",
         _mini(sorted(worker_stats,
                      key=lambda w: float(str(w.get("failed_pct","0")).replace("%","").strip() or "0"),
                      reverse=True), [
             ("Worker","name"),("Total","total"),("Failed","failed"),
             ("Success","success"),("Fail %","failed_pct"),
         ])),
    ]

    sec_html = ""
    for title, color, tbl_html in sections:
        sec_html += f"""<div class="section">
  <div class="section-title" style="border-color:{color};">{title}</div>
  {tbl_html}
</div>"""

    body = f"""
<div class="date-window">📅 Week: {week_label} (Mon–Sun)</div>
<div class="section">
  <div class="section-title">Weekly KPI Overview</div>
  <div class="kpi-row">{kpis}</div>
</div>
{sec_html}"""

    subject = (f"[OPS WEEKLY] Summary {week_label} — "
               f"{len(fail_w)} failures, {len(incident_data)} incidents, "
               f"{tx_failed} WM tx failed")
    return subject, body, False


# ─────────────────────────────────────────────────────────────────────────────
#  Save + Public API
# ─────────────────────────────────────────────────────────────────────────────

def _save(digest_type, subject, html, date_str, ts, is_alert):
    folder = DIGEST_BASE / date_str / digest_type
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "email_body.html").write_text(html, encoding="utf-8")
    (folder / "email_meta.json").write_text(
        json.dumps({"digest_type":digest_type,"subject":subject,
                    "from":FROM_ADDR,"to":TO_ADDR,
                    "generated_at":ts,"date":date_str,
                    "is_alert":is_alert,
                    "html_file":str(folder/"email_body.html")},
                   indent=2), encoding="utf-8")
    log.info(f"Digest saved: {folder}")
    return folder


def prepare_daily_digest(digest_type, support_data=None, failure_data=None,
                         incident_data=None, azure_data=None, ptc_data=None,
                         transactions=None, wvs_queue=None, worker_stats=None):
    now      = datetime.now().strftime("%d %b %Y %H:%M")
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    today    = date.today()
    yest     = today - timedelta(days=1)
    date_label = f"{yest.strftime('%d %b')} – {today.strftime('%d %b %Y')}"

    support_data  = support_data  or []
    failure_data  = failure_data  or []
    incident_data = incident_data or []
    azure_data    = azure_data    or []
    ptc_data      = ptc_data      or []
    transactions  = transactions  or []
    wvs_queue     = wvs_queue     or []
    worker_stats  = worker_stats  or []

    builders = {
        "integration_failures": lambda: _build_integration_failures(failure_data, now, date_label),
        "wm_transactions"     : lambda: _build_wm_transactions(transactions, now, date_label),
        "wvs_queue"           : lambda: _build_wvs_queue(wvs_queue, now, date_label),
        "worker_stats"        : lambda: _build_worker_stats(worker_stats, now, date_label),
        "incidents"           : lambda: _build_incidents(incident_data, now, date_label),
        "azure_bugs"          : lambda: _build_azure_bugs(azure_data, now, date_label),
        "ptc_cases"           : lambda: _build_ptc_cases(ptc_data, now, date_label),
        "support_emails"      : lambda: _build_support_emails(support_data, now, date_label),
        "weekly_summary"      : lambda: _build_weekly_summary(
            support_data, failure_data, incident_data, azure_data, ptc_data,
            transactions, wvs_queue, worker_stats, now),
    }

    if digest_type not in builders:
        return {"success": False, "message": f"Unknown type: {digest_type}"}
    try:
        subject, body_html, is_alert = builders[digest_type]()
        icon   = "⚠ " if is_alert else "📋 "
        sub_lbl= "⚠ Action Required" if is_alert else "Daily Report"
        if digest_type == "weekly_summary":
            sub_lbl = "Weekly Summary"
        hdr  = _hdr(icon + digest_type.replace("_"," ").title(), sub_lbl, now,
                    date_window=date_label if digest_type not in ("wvs_queue","worker_stats","weekly_summary") else "")
        html = _wrap(hdr, body_html, _ftr(now, digest_type))
        folder = _save(digest_type, subject, html, date_str, ts, is_alert)
        return {"success":True, "digest_type":digest_type, "subject":subject,
                "is_alert":is_alert, "folder":str(folder),
                "html_file":str(folder/"email_body.html"),
                "meta_file":str(folder/"email_meta.json"), "date":date_str}
    except Exception as exc:
        log.error(f"Digest build failed [{digest_type}]: {exc}", exc_info=True)
        return {"success":False, "digest_type":digest_type, "message":str(exc)}


def prepare_all_digests(support_data=None, failure_data=None, incident_data=None,
                        azure_data=None, ptc_data=None,
                        transactions=None, wvs_queue=None, worker_stats=None):
    kwargs  = dict(support_data=support_data, failure_data=failure_data,
                   incident_data=incident_data, azure_data=azure_data, ptc_data=ptc_data,
                   transactions=transactions, wvs_queue=wvs_queue, worker_stats=worker_stats)
    return [prepare_daily_digest(t, **kwargs) for t in DIGEST_TYPES]


def list_saved_digests(days=7):
    out = []
    if not DIGEST_BASE.exists():
        return out
    for date_dir in sorted(DIGEST_BASE.iterdir(), reverse=True)[:days]:
        if not date_dir.is_dir(): continue
        for dtype_dir in sorted(date_dir.iterdir()):
            mf = dtype_dir / "email_meta.json"
            if mf.exists():
                try: out.append(json.loads(mf.read_text(encoding="utf-8")))
                except Exception: pass
    return out
