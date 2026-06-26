# =============================================================================
#  SHARED EMAIL NOTIFIER  v2
#  common/utils/email_notifier.py
# =============================================================================

import os
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

log = logging.getLogger("email_notifier")

# ── Config ────────────────────────────────────────────────────────────────────
ALERT_FROM    = "keshavamurthy.hg@consultant.volvo.com"
ALERT_TO      = ["keshavamurthy.hg@consultant.volvo.com"]

SMTP_HOST     = "smtp.office365.com"
SMTP_PORT     = 587
SMTP_USER     = "keshavamurthy.hg@consultant.volvo.com"
SMTP_PASSWORD = ""   # Leave blank — set env var EMAIL_PASSWORD instead

# ── Alert thresholds ──────────────────────────────────────────────────────────
THRESHOLDS = {
    "failure_total"      : 10,
    "failure_prod"       : 3,
    "support_pending"    : 5,
    "incident_on_hold"   : 3,
    "azure_new"          : 5,
    "ptc_open"           : 5,
    "wm_tx_failed"       : 5,
    "wm_worker_fail_pct" : 20.0,
    "wm_wvs_failed"      : 3,
}

# ── Summary report output folder ─────────────────────────────────────────────
SUMMARY_OUTPUT_DIR = Path("output/summary_report")


# ─────────────────────────────────────────────────────────────────────────────
#  HTML / CSS shared template
# ─────────────────────────────────────────────────────────────────────────────

_STYLE = """
<style>
  * { box-sizing: border-box; }
  body { font-family: Segoe UI, Arial, sans-serif; background: #f4f6f9;
         margin: 0; padding: 20px; color: #374151; }
  .wrap { max-width: 1100px; margin: auto; }
  .header { background: linear-gradient(135deg,#1e3a5f,#1a2e4a); color:#fff;
            padding: 20px 24px; border-radius: 10px 10px 0 0; }
  .header h1 { margin: 0; font-size: 20px; }
  .header p  { margin: 4px 0 0; font-size: 12px; color: #93c5fd; }
  .body { background: #fff; padding: 20px 24px;
          border: 1px solid #e5e7eb; border-top: none; }
  .section { margin-bottom: 20px; }
  .section-title { font-size: 13px; font-weight: 700; color: #374151;
                   border-left: 4px solid #f28c38; padding-left: 10px;
                   margin-bottom: 10px; }
  .chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
  .chip { display: inline-flex; flex-direction: column; align-items: center;
          padding: 4px 14px; border-radius: 7px; border: 2px solid;
          min-width: 60px; background: #fff; }
  .chip-val { font-size: 18px; font-weight: 800; }
  .chip-lbl { font-size: 9px; font-weight: 700; text-transform: uppercase;
              letter-spacing: .06em; opacity: .8; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 6px; }
  th { background: #f9fafb; padding: 7px 10px; text-align: left;
       font-weight: 700; color: #374151; border-bottom: 2px solid #e5e7eb; }
  td { padding: 6px 10px; border-bottom: 1px solid #f3f4f6;
       max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  tr:hover td { background: #f9fafb; }
  .alert-banner { background: #fef2f2; border: 1px solid #fca5a5;
                  border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;
                  font-size: 12px; color: #dc2626; }
  .footer { background: #f9fafb; padding: 12px 24px; border-radius: 0 0 10px 10px;
            border: 1px solid #e5e7eb; border-top: none;
            font-size: 11px; color: #9ca3af; text-align: center; }
  /* Download button (summary report only) */
  .dl-bar { text-align: right; padding: 10px 0 4px; }
  .dl-btn { display: inline-block; padding: 7px 18px; background: #1e3a5f;
            color: #fff; border-radius: 8px; font-size: 12px; font-weight: 700;
            text-decoration: none; cursor: pointer; border: none; }
  .dl-btn:hover { background: #1d4ed8; }
  /* Summary grid */
  .rep-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .rep-card { border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }
  .rep-card-header { background: #f9fafb; padding: 10px 14px;
                     display: flex; align-items: center;
                     justify-content: space-between; flex-wrap: wrap; gap: 8px; }
  .rep-card-title { font-size: 13px; font-weight: 700; color: #111; }
  .rep-card-body  { overflow-x: auto; }
  .rep-card-body table { margin: 0; }
  .kpi-overview { display: grid; grid-template-columns: repeat(4,1fr);
                  gap: 10px; margin-bottom: 20px; }
  .kpi-box { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
             padding: 12px 16px; text-align: center; }
  .kpi-box-val { font-size: 26px; font-weight: 800; }
  .kpi-box-lbl { font-size: 10px; font-weight: 600; text-transform: uppercase;
                 letter-spacing: .05em; color: #6b7280; margin-top: 2px; }
  @media (max-width: 700px) {
    .rep-grid { grid-template-columns: 1fr; }
    .kpi-overview { grid-template-columns: repeat(2,1fr); }
  }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _chip(val, label, color):
    return (
        f'<div class="chip" style="color:{color};border-color:{color};">'
        f'<span class="chip-val">{val}</span>'
        f'<span class="chip-lbl">{label}</span></div>'
    )


def _v(row, *keys):
    """Return first non-empty value for any of the given keys."""
    for k in keys:
        v = row.get(k, "")
        if v and str(v).strip() and str(v).strip() not in ("nan", "None"):
            return str(v).strip()
    return "—"


def _td(row, *keys):
    v = _v(row, *keys)
    title = v if len(v) > 40 else ""
    display = v[:60] + "…" if len(v) > 60 else v
    return f'<td title="{title}">{display}</td>'


def _table(rows, col_specs, max_rows=10):
    """
    col_specs: list of (header, *keys) tuples.
    Returns <thead><tr>…</tr></thead><tbody>…</tbody>
    """
    if not rows:
        colspan = len(col_specs)
        return (
            f"<thead><tr>{''.join(f'<th>{s[0]}</th>' for s in col_specs)}</tr></thead>"
            f"<tbody><tr><td colspan='{colspan}' style='color:#9ca3af;text-align:center;"
            f"padding:10px;'>No records</td></tr></tbody>"
        )
    head = "<thead><tr>" + "".join(f"<th>{s[0]}</th>" for s in col_specs) + "</tr></thead>"
    body = "<tbody>"
    for r in rows[:max_rows]:
        body += "<tr>" + "".join(_td(r, *s[1:]) for s in col_specs) + "</tr>"
    if len(rows) > max_rows:
        body += (
            f"<tr><td colspan='{len(col_specs)}' style='color:#9ca3af;"
            f"font-style:italic;padding:6px 10px;'>…and {len(rows)-max_rows} more rows</td></tr>"
        )
    body += "</tbody>"
    return head + body


# ─────────────────────────────────────────────────────────────────────────────
#  OPS CENTER — alert builder
# ─────────────────────────────────────────────────────────────────────────────

def build_ops_alert(support_data, failure_data, incident_data, azure_data, ptc_data):
    T   = THRESHOLDS
    now = datetime.now().strftime("%d %b %Y %H:%M")

    fail_total  = len(failure_data)
    fail_prod   = sum(1 for r in failure_data if _v(r,"Environment","environment").upper() == "PROD")
    sup_pending = sum(1 for r in support_data if "Action Required" in _v(r,"Categories","Category","category"))
    inc_on_hold = sum(1 for r in incident_data if _v(r,"Status","status") == "On Hold")
    az_new      = sum(1 for r in azure_data    if _v(r,"Status","status") == "New")
    ptc_open    = sum(1 for r in ptc_data      if _v(r,"Status","status") not in ("Closed","Resolved","Cancelled","—"))

    alerts = []
    if fail_total  >= T["failure_total"]:   alerts.append(f"🔴 Integration Failures: {fail_total} total (threshold {T['failure_total']})")
    if fail_prod   >= T["failure_prod"]:    alerts.append(f"🔴 PROD Failures: {fail_prod} (threshold {T['failure_prod']})")
    if sup_pending >= T["support_pending"]: alerts.append(f"🟠 Support Emails — Action Required: {sup_pending} pending")
    if inc_on_hold >= T["incident_on_hold"]:alerts.append(f"🟠 Incidents On Hold: {inc_on_hold}")
    if az_new      >= T["azure_new"]:       alerts.append(f"🔵 New Azure Bugs: {az_new}")
    if ptc_open    >= T["ptc_open"]:        alerts.append(f"🟡 Open PTC Cases: {ptc_open}")

    banner = ""
    if alerts:
        items  = "".join(f"<li>{a}</li>" for a in alerts)
        banner = (f'<div class="alert-banner"><strong>⚠ Critical Alerts Triggered:</strong>'
                  f'<ul style="margin:6px 0 0 16px;padding:0;">{items}</ul></div>')

    # Tables
    fail_tbl = _table(
        sorted(failure_data, key=lambda r: _v(r,"Failure Time"), reverse=True),
        [("Failure Time","Failure Time","failure_time"),
         ("Integration","Integration","Target","target"),
         ("Object","Object Number","Object","object"),
         ("Error","Error Message","Notes","notes"),
         ("Env","Environment","environment"),
         ("Server","Windchill Server","wc_server","Status")],
        max_rows=12
    )
    sup_tbl = _table(
        [r for r in support_data if "Action Required" in _v(r,"Categories","Category","category")],
        [("Date","Date Received","date_received","Date"),
         ("Name","Name","name","From"),
         ("Subject","Subject","subject"),
         ("Category","Categories","Category","category")],
        max_rows=10
    )
    inc_tbl = _table(
        [r for r in incident_data if _v(r,"Status","status") == "On Hold"],
        [("Number","Number","number"),
         ("Description","Description","short_description"),
         ("Assigned To","Assigned To","assigned_to"),
         ("Priority","Priority","priority"),
         ("Status","Status","status")],
        max_rows=10
    )

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_STYLE}</head>
<body><div class="wrap">
<div class="header"><h1>⚠ Operations Center — Critical Alert</h1>
<p>Generated: {now} | Auto-triggered by threshold breach</p></div>
<div class="body">
  {banner}
  <div class="section">
    <div class="section-title">Integration Failures</div>
    <div class="chip-row">{_chip(fail_total,"Total Failed","#ef4444")}{_chip(fail_prod,"PROD","#f59e0b")}</div>
    <table>{fail_tbl}</table>
  </div>
  <div class="section">
    <div class="section-title">Support Emails — Action Required</div>
    <div class="chip-row">{_chip(len(support_data),"Total","#3b82f6")}{_chip(sup_pending,"Pending","#ef4444")}</div>
    <table>{sup_tbl}</table>
  </div>
  <div class="section">
    <div class="section-title">Incidents On Hold</div>
    <div class="chip-row">{_chip(len(incident_data),"Total","#f28c38")}{_chip(inc_on_hold,"On Hold","#ef4444")}
    {_chip(sum(1 for r in incident_data if _v(r,"Status")=="In Progress"),"In Progress","#3b82f6")}</div>
    <table>{inc_tbl}</table>
  </div>
  <div class="section">
    <div class="section-title">Azure / PTC Summary</div>
    <div class="chip-row">
      {_chip(len(azure_data),"Azure Total","#0ea5e9")}{_chip(az_new,"New","#8b5cf6")}
      {_chip(len(ptc_data),"PTC Total","#8b5cf6")}{_chip(ptc_open,"PTC Open","#f59e0b")}
    </div>
  </div>
</div>
<div class="footer">Ops Platform · Auto Alert · {now}</div>
</div></body></html>"""

    return {"should_send": bool(alerts), "subject": f"[OPS ALERT] Critical thresholds breached — {now}",
            "html": html, "alerts": alerts}


# ─────────────────────────────────────────────────────────────────────────────
#  WINDCHILL MONITORING — alert builder
# ─────────────────────────────────────────────────────────────────────────────

def build_wm_alert(transactions, wvs_queue, worker_stats):
    T   = THRESHOLDS
    now = datetime.now().strftime("%d %b %Y %H:%M")

    tx_failed  = [r for r in transactions if "FAIL" in (_v(r,"status","Status") or "").upper()
                                          or "ERR"  in (_v(r,"status","Status") or "").upper()]
    wvs_failed = [r for r in wvs_queue   if "FAIL" in (_v(r,"status","Status") or "").upper()]

    high_fail_workers = []
    for w in worker_stats:
        try:
            pct = float(str(w.get("failed_pct","0")).replace("%","").strip())
            if pct >= T["wm_worker_fail_pct"]:
                high_fail_workers.append({**w, "_pct": pct})
        except Exception:
            pass

    alerts = []
    if len(tx_failed)  >= T["wm_tx_failed"]:  alerts.append(f"🔴 Transaction Failures: {len(tx_failed)} (threshold {T['wm_tx_failed']})")
    if len(wvs_failed) >= T["wm_wvs_failed"]: alerts.append(f"🔴 WVS Queue Failures: {len(wvs_failed)}")
    if high_fail_workers:                       alerts.append(f"🟠 Workers with high failure rate: {', '.join(_v(w,'name','Name') for w in high_fail_workers)}")

    banner = ""
    if alerts:
        items  = "".join(f"<li>{a}</li>" for a in alerts)
        banner = (f'<div class="alert-banner"><strong>⚠ Critical Alerts Triggered:</strong>'
                  f'<ul style="margin:6px 0 0 16px;padding:0;">{items}</ul></div>')

    tx_tbl  = _table(tx_failed[:15],
        [("Time","time","Time"),("Target","target","Target"),("Action","action","Action"),
         ("Status","status","Status"),("Object","object","Object"),("Notes","notes","Notes")], 12)
    wvs_tbl = _table(wvs_failed[:15],
        [("Queue","queue","Queue"),("Job","job","Job"),("Status","status","Status"),
         ("Name","name","Name"),("Version","version","Version"),("User","user","User")], 12)
    wk_tbl  = _table(worker_stats[:25],
        [("Worker","name","Name"),("Total","total","Total"),("Failed","failed","Failed"),
         ("Success","success","Success"),("Fail %","failed_pct","failed_pct")], 25)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_STYLE}</head>
<body><div class="wrap">
<div class="header"><h1>⚠ Windchill Monitoring — Critical Alert</h1>
<p>Generated: {now} | Auto-triggered by threshold breach</p></div>
<div class="body">
  {banner}
  <div class="section">
    <div class="section-title">Transaction Failures</div>
    <div class="chip-row">{_chip(len(transactions),"Total","#f28c38")}{_chip(len(tx_failed),"Failed","#ef4444")}</div>
    <table>{tx_tbl}</table>
  </div>
  <div class="section">
    <div class="section-title">WVS Queue — Failures</div>
    <div class="chip-row">{_chip(len(wvs_queue),"Total Jobs","#0ea5e9")}{_chip(len(wvs_failed),"Failed","#ef4444")}</div>
    <table>{wvs_tbl}</table>
  </div>
  <div class="section">
    <div class="section-title">Worker Statistics</div>
    <table>{wk_tbl}</table>
  </div>
</div>
<div class="footer">Ops Platform · Windchill Alert · {now}</div>
</div></body></html>"""

    return {"should_send": bool(alerts), "subject": f"[WM ALERT] Windchill critical thresholds breached — {now}",
            "html": html, "alerts": alerts}


# ─────────────────────────────────────────────────────────────────────────────
#  SUMMARY REPORT — all 8 trackers
# ─────────────────────────────────────────────────────────────────────────────

def build_summary_report(support_data, failure_data, incident_data,
                         azure_data, ptc_data, transactions, wvs_queue, worker_stats):
    now = datetime.now().strftime("%d %b %Y %H:%M")
    ts  = datetime.now().strftime("%Y%m%d_%H%M")

    # KPI counts
    fail_prod   = sum(1 for r in failure_data  if _v(r,"Environment","environment").upper() == "PROD")
    sup_pending = sum(1 for r in support_data  if "Action Required" in _v(r,"Categories","Category","category"))
    inc_on_hold = sum(1 for r in incident_data if _v(r,"Status","status") == "On Hold")
    inc_inprog  = sum(1 for r in incident_data if _v(r,"Status","status") == "In Progress")
    az_new      = sum(1 for r in azure_data    if _v(r,"Status","status") == "New")
    az_active   = sum(1 for r in azure_data    if _v(r,"Status","status") == "Active")
    ptc_open    = sum(1 for r in ptc_data      if _v(r,"Status","status") not in ("Closed","Resolved","Cancelled","—"))
    tx_failed   = sum(1 for r in transactions  if "FAIL" in (_v(r,"status","Status") or "").upper())
    wvs_failed  = sum(1 for r in wvs_queue     if "FAIL" in (_v(r,"status","Status") or "").upper())

    def card(title, color, chips_html, tbl_html):
        return f"""<div class="rep-card">
  <div class="rep-card-header" style="border-left:4px solid {color};">
    <span class="rep-card-title">{title}</span>
    <div class="chip-row" style="margin:0;">{chips_html}</div>
  </div>
  <div class="rep-card-body"><table>{tbl_html}</table></div>
</div>"""

    # Tables — using correct field names
    fail_tbl = _table(
        sorted(failure_data, key=lambda r: _v(r,"Failure Time"), reverse=True),
        [("Failure Time","Failure Time","failure_time"),
         ("Integration","Integration","Target","target"),
         ("Object","Object Number","Object","object"),
         ("Error Message","Error Message","Notes","notes"),
         ("Env","Environment","environment"),
         ("Server","Windchill Server","wc_server")], 8)

    sup_tbl = _table(
        [r for r in support_data if "Action Required" in _v(r,"Categories","Category","category")] or support_data,
        [("Date","Date Received","date_received","Date"),
         ("Name","Name","name","From"),
         ("Subject","Subject","subject"),
         ("Category","Categories","Category","category")], 8)

    inc_tbl = _table(incident_data,
        [("Number","Number","number"),
         ("Description","Description","short_description"),
         ("Assigned To","Assigned To","assigned_to"),
         ("Priority","Priority","priority"),
         ("Status","Status","status")], 8)

    az_tbl = _table(azure_data,
        [("Number","Number","number"),
         ("Description","Description","title"),
         ("Assigned To","Assigned To","assigned_to"),
         ("Priority","Priority","priority"),
         ("Status","Status","status")], 8)

    ptc_tbl = _table(ptc_data,
        [("Number","Number","number"),
         ("Description","Description","subject"),
         ("Priority","Priority","severity","priority"),
         ("Status","Status","status")], 8)

    tx_tbl = _table(
        [r for r in transactions if "FAIL" in (_v(r,"status","Status") or "").upper()],
        [("Time","time","Time"),("Target","target","Target"),
         ("Action","action","Action"),("Status","status","Status"),
         ("Object","object","Object"),("Notes","notes","Notes")], 8)

    wvs_tbl = _table(
        [r for r in wvs_queue if "FAIL" in (_v(r,"status","Status") or "").upper()] or wvs_queue,
        [("Queue","queue","Queue"),("Job","job","Job"),
         ("Status","status","Status"),("Name","name","Name"),("User","user","User")], 8)

    wk_tbl = _table(worker_stats,
        [("Worker","name","Name"),("Total","total","Total"),
         ("Failed","failed","Failed"),("Success","success","Success"),
         ("Fail %","failed_pct")], 10)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_STYLE}
<title>Ops Platform — Summary Report {ts}</title>
</head><body><div class="wrap">
<div class="header">
  <h1>📊 Ops Platform — Summary Report</h1>
  <p>All 8 Trackers · Generated: {now}</p>
</div>
<div class="body">
  <div class="dl-bar">
    <button class="dl-btn" onclick="downloadReport()">⬇ Download Report</button>
  </div>

  <!-- KPI Overview -->
  <div class="kpi-overview">
    <div class="kpi-box"><div class="kpi-box-val" style="color:#ef4444">{len(failure_data)}</div><div class="kpi-box-lbl">Integration Failures</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#f59e0b">{fail_prod}</div><div class="kpi-box-lbl">PROD Failures</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#3b82f6">{len(support_data)}</div><div class="kpi-box-lbl">Support Emails</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#ef4444">{sup_pending}</div><div class="kpi-box-lbl">Action Required</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#f28c38">{len(incident_data)}</div><div class="kpi-box-lbl">Incidents</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#0ea5e9">{len(azure_data)}</div><div class="kpi-box-lbl">Azure Bugs</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#8b5cf6">{len(ptc_data)}</div><div class="kpi-box-lbl">PTC Cases</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#dc2626">{tx_failed}</div><div class="kpi-box-lbl">WM Tx Failures</div></div>
  </div>

  <!-- 8 tracker cards -->
  <div class="rep-grid">
    {card("Integration Failures","#ef4444",
      _chip(len(failure_data),"Total","#ef4444")+_chip(fail_prod,"PROD","#f59e0b"), fail_tbl)}
    {card("Support Emails","#3b82f6",
      _chip(len(support_data),"Total","#3b82f6")+_chip(sup_pending,"Pending Actions","#ef4444"), sup_tbl)}
    {card("Incident Tracker","#f28c38",
      _chip(len(incident_data),"Total","#f28c38")+_chip(inc_on_hold,"On Hold","#ef4444")+_chip(inc_inprog,"In Progress","#3b82f6"), inc_tbl)}
    {card("Azure Tracker","#0ea5e9",
      _chip(len(azure_data),"Total","#0ea5e9")+_chip(az_new,"New","#8b5cf6")+_chip(az_active,"Active","#22c55e"), az_tbl)}
    {card("PTC Cases","#8b5cf6",
      _chip(len(ptc_data),"Total","#8b5cf6")+_chip(ptc_open,"Open","#f59e0b"), ptc_tbl)}
    {card("WM — Transactions","#f28c38",
      _chip(len(transactions),"Total","#f28c38")+_chip(tx_failed,"Failed","#ef4444"), tx_tbl)}
    {card("WM — WVS Queue","#0ea5e9",
      _chip(len(wvs_queue),"Total","#0ea5e9")+_chip(wvs_failed,"Failed","#ef4444"), wvs_tbl)}
    {card("WM — Worker Stats","#374151",
      _chip(len(worker_stats),"Workers","#374151"), wk_tbl)}
  </div>
</div>
<div class="footer">Ops Platform · Summary Report · {now} · All 8 Trackers</div>
</div>

<script>
function downloadReport() {{
  const blob = new Blob([document.documentElement.outerHTML], {{type:'text/html'}});
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = 'ops_summary_report_{ts}.html';
  a.click();
}}
</script>
</body></html>"""

    return html, ts   # return both html and timestamp for file saving


# ─────────────────────────────────────────────────────────────────────────────
#  Save summary report to disk
# ─────────────────────────────────────────────────────────────────────────────

def save_summary_report(html: str, ts: str) -> Path:
    """Save HTML report to output/summary_report/ and return the Path."""
    out_dir = SUMMARY_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"ops_summary_report_{ts}.html"
    file_path.write_text(html, encoding="utf-8")
    log.info(f"Summary report saved: {file_path}")
    return file_path


# ─────────────────────────────────────────────────────────────────────────────
#  SMTP sender
# ─────────────────────────────────────────────────────────────────────────────

def send_alert_email(subject: str, html: str, to: list = None) -> dict:
    recipients = to or ALERT_TO
    password   = SMTP_PASSWORD or os.environ.get("EMAIL_PASSWORD", "")

    if not password:
        log.warning("EMAIL_PASSWORD not set — email not sent.")
        return {"success": False,
                "message": "SMTP password not configured. Set the EMAIL_PASSWORD environment variable."}
    try:
        msg            = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = ALERT_FROM
        msg["To"]      = ", ".join(recipients)
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, password)
            server.sendmail(ALERT_FROM, recipients, msg.as_string())

        log.info(f"Email sent → {recipients}: {subject}")
        return {"success": True, "message": f"Email sent to {', '.join(recipients)}"}
    except Exception as exc:
        log.error(f"Email send failed: {exc}")
        return {"success": False, "message": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
#  Email test helper
# ─────────────────────────────────────────────────────────────────────────────

def send_test_email() -> dict:
    """Send a plain test email to verify SMTP config is working."""
    now  = datetime.now().strftime("%d %b %Y %H:%M:%S")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_STYLE}</head>
<body><div class="wrap">
<div class="header"><h1>✅ Ops Platform — Email Test</h1><p>Sent: {now}</p></div>
<div class="body">
  <p style="font-size:14px;">This is a <strong>test email</strong> from the Ops Platform notification system.</p>
  <p>If you received this, your SMTP configuration is working correctly.</p>
  <ul style="font-size:13px;line-height:1.8;">
    <li><strong>SMTP Host:</strong> {SMTP_HOST}:{SMTP_PORT}</li>
    <li><strong>From:</strong> {ALERT_FROM}</li>
    <li><strong>To:</strong> {", ".join(ALERT_TO)}</li>
    <li><strong>Time:</strong> {now}</li>
  </ul>
  <p style="color:#16a34a;font-weight:700;">✅ Notification system is ready.</p>
</div>
<div class="footer">Ops Platform · Email Test · {now}</div>
</div></body></html>"""

    return send_alert_email(
        subject=f"[OPS TEST] Email notification test — {now}",
        html=html
    )
