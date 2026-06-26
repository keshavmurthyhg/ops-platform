# =============================================================================
#  SHARED EMAIL NOTIFIER
#  common/utils/email_notifier.py
#
#  Sends HTML alert emails via SMTP for critical events across:
#    - Operations Center (5 trackers)
#    - Windchill Monitoring (3 trackers)
#
#  Usage:
#    from common.utils.email_notifier import send_alert_email, build_ops_alert, build_wm_alert
# =============================================================================

import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger("email_notifier")

# ── Config ────────────────────────────────────────────────────────────────────
ALERT_FROM    = "keshavamurthy.hg@consultant.volvo.com"
ALERT_TO      = ["keshavamurthy.hg@consultant.volvo.com"]

# SMTP — update to your relay/server
SMTP_HOST     = "smtp.office365.com"
SMTP_PORT     = 587
SMTP_USER     = "keshavamurthy.hg@consultant.volvo.com"
SMTP_PASSWORD = ""          # Set via env: EMAIL_PASSWORD or config.py

# Thresholds that trigger a critical alert
THRESHOLDS = {
    "failure_total"      : 10,   # OPS: integration failures
    "failure_prod"       : 3,    # OPS: PROD failures
    "support_pending"    : 5,    # OPS: action-required emails
    "incident_on_hold"   : 3,    # OPS: incidents on hold
    "azure_new"          : 5,    # OPS: new Azure bugs
    "ptc_open"           : 5,    # OPS: open PTC cases
    "wm_tx_failed"       : 5,    # WM: failed transactions
    "wm_worker_fail_pct" : 20.0, # WM: worker fail % threshold
    "wm_wvs_failed"      : 3,    # WM: WVS jobs failed
}


# ─────────────────────────────────────────────────────────────────────────────
#  HTML email template helpers
# ─────────────────────────────────────────────────────────────────────────────

_STYLE = """
<style>
  body { font-family: Segoe UI, Arial, sans-serif; background:#f4f6f9; margin:0; padding:20px; }
  .wrap { max-width:720px; margin:auto; }
  .header { background:linear-gradient(135deg,#1e3a5f,#1a2e4a); color:#fff;
            padding:20px 24px; border-radius:10px 10px 0 0; }
  .header h1 { margin:0; font-size:20px; }
  .header p  { margin:4px 0 0; font-size:12px; color:#93c5fd; }
  .body { background:#fff; padding:20px 24px; border:1px solid #e5e7eb; }
  .section { margin-bottom:20px; }
  .section-title { font-size:13px; font-weight:700; color:#374151;
                   border-left:4px solid #f28c38; padding-left:10px;
                   margin-bottom:10px; }
  .chip-row { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; }
  .chip { display:inline-flex; flex-direction:column; align-items:center;
          padding:4px 14px; border-radius:7px; border:2px solid; min-width:60px; }
  .chip-val { font-size:18px; font-weight:800; }
  .chip-lbl { font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; opacity:.8; }
  table { width:100%; border-collapse:collapse; font-size:12px; margin-top:6px; }
  th { background:#f9fafb; padding:7px 10px; text-align:left; font-weight:700;
       color:#374151; border-bottom:2px solid #e5e7eb; }
  td { padding:6px 10px; border-bottom:1px solid #f3f4f6; color:#374151; }
  tr:hover td { background:#f9fafb; }
  .badge { display:inline-block; padding:2px 8px; border-radius:999px; font-size:10px; font-weight:700; }
  .badge-red   { background:#fef2f2; color:#dc2626; }
  .badge-amber { background:#fffbeb; color:#d97706; }
  .badge-blue  { background:#eff6ff; color:#2563eb; }
  .badge-green { background:#f0fdf4; color:#16a34a; }
  .alert-banner { background:#fef2f2; border:1px solid #fca5a5; border-radius:8px;
                  padding:10px 14px; margin-bottom:14px; font-size:12px; color:#dc2626; }
  .footer { background:#f9fafb; padding:12px 24px; border-radius:0 0 10px 10px;
            border:1px solid #e5e7eb; border-top:none; font-size:11px; color:#9ca3af;
            text-align:center; }
  .critical { color:#dc2626; font-weight:700; }
</style>
"""


def _chip(val, label, color):
    return (
        f'<div class="chip" style="color:{color};border-color:{color};">'
        f'<span class="chip-val">{val}</span>'
        f'<span class="chip-lbl">{label}</span></div>'
    )


def _table_rows(rows, cols):
    """Render up to 20 rows of a data list as an HTML table."""
    if not rows:
        return "<tr><td colspan='99' style='color:#9ca3af;text-align:center;'>No records</td></tr>"
    out = ""
    for r in rows[:20]:
        out += "<tr>" + "".join(f"<td>{r.get(c, '—')}</td>" for c in cols) + "</tr>"
    if len(rows) > 20:
        out += f"<tr><td colspan='{len(cols)}' style='color:#9ca3af;font-style:italic;'>… and {len(rows)-20} more rows</td></tr>"
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  OPS CENTER — alert builder
# ─────────────────────────────────────────────────────────────────────────────

def build_ops_alert(
    support_data, failure_data, incident_data, azure_data, ptc_data
) -> dict:
    """
    Analyse OPS data, decide if a critical alert is warranted, and build HTML.
    Returns  { "should_send": bool, "subject": str, "html": str, "alerts": list[str] }
    """
    T = THRESHOLDS
    now = datetime.now().strftime("%d %b %Y %H:%M")

    # ── Derive counts ─────────────────────────────────────────────────────────
    fail_total    = len(failure_data)
    fail_prod     = sum(1 for r in failure_data if (r.get("Environment","") or "").upper() == "PROD")
    sup_pending   = sum(1 for r in support_data if "Action Required" in str(r.get("Categories","") or r.get("Category","")))
    inc_on_hold   = sum(1 for r in incident_data if r.get("Status","") == "On Hold")
    az_new        = sum(1 for r in azure_data if r.get("Status","") == "New")
    ptc_open      = sum(1 for r in ptc_data if r.get("Status","") not in ("Closed","Resolved","Cancelled"))

    # ── Detect which thresholds are breached ──────────────────────────────────
    alerts = []
    if fail_total  >= T["failure_total"]:  alerts.append(f"🔴 Integration Failures: {fail_total} total (threshold {T['failure_total']})")
    if fail_prod   >= T["failure_prod"]:   alerts.append(f"🔴 PROD Failures: {fail_prod} (threshold {T['failure_prod']})")
    if sup_pending >= T["support_pending"]:alerts.append(f"🟠 Support Emails — Action Required: {sup_pending} pending")
    if inc_on_hold >= T["incident_on_hold"]:alerts.append(f"🟠 Incidents On Hold: {inc_on_hold}")
    if az_new      >= T["azure_new"]:      alerts.append(f"🔵 New Azure Bugs: {az_new}")
    if ptc_open    >= T["ptc_open"]:       alerts.append(f"🟡 Open PTC Cases: {ptc_open}")

    should_send = bool(alerts)

    # ── Build HTML ─────────────────────────────────────────────────────────────
    alert_banner = ""
    if alerts:
        items = "".join(f"<li>{a}</li>" for a in alerts)
        alert_banner = f'<div class="alert-banner"><strong>⚠ Critical Alerts Triggered:</strong><ul style="margin:6px 0 0 16px;padding:0;">{items}</ul></div>'

    # Integration Failures top 10
    fail_rows = _table_rows(
        sorted(failure_data, key=lambda r: r.get("Failure Time",""), reverse=True)[:10],
        ["Failure Time","Integration","Object Number","Error Message","Environment","WC Server"]
    )
    # Support top 10 pending
    sup_rows = _table_rows(
        [r for r in support_data if "Action Required" in str(r.get("Categories","") or r.get("Category",""))][:10],
        ["Date","From","Subject","Categories"]
    )
    # Incidents on hold
    inc_rows = _table_rows(
        [r for r in incident_data if r.get("Status","") == "On Hold"][:10],
        ["Number","Short Description","Assigned To","Priority","Status"]
    )

    html = f"""<!DOCTYPE html><html><head>{_STYLE}</head><body><div class="wrap">
<div class="header">
  <h1>⚠ Operations Center — Critical Alert</h1>
  <p>Generated: {now} | Auto-triggered by threshold breach</p>
</div>
<div class="body">
  {alert_banner}

  <!-- Integration Failures -->
  <div class="section">
    <div class="section-title">Integration Failures</div>
    <div class="chip-row">
      {_chip(fail_total, "Total Failed", "#ef4444")}
      {_chip(fail_prod, "PROD", "#f59e0b")}
    </div>
    <table>
      <tr><th>Failure Time</th><th>Integration</th><th>Object Number</th><th>Error Message</th><th>Env</th><th>Server</th></tr>
      {fail_rows}
    </table>
  </div>

  <!-- Support Emails -->
  <div class="section">
    <div class="section-title">Support Emails — Action Required</div>
    <div class="chip-row">
      {_chip(len(support_data), "Total", "#3b82f6")}
      {_chip(sup_pending, "Pending Actions", "#ef4444")}
    </div>
    <table>
      <tr><th>Date</th><th>From</th><th>Subject</th><th>Category</th></tr>
      {sup_rows}
    </table>
  </div>

  <!-- Incidents -->
  <div class="section">
    <div class="section-title">Incident Tracker</div>
    <div class="chip-row">
      {_chip(len(incident_data), "Total", "#f28c38")}
      {_chip(inc_on_hold, "On Hold", "#ef4444")}
      {_chip(sum(1 for r in incident_data if r.get("Status","")=="In Progress"), "In Progress", "#3b82f6")}
    </div>
    <table>
      <tr><th>Number</th><th>Short Description</th><th>Assigned To</th><th>Priority</th><th>Status</th></tr>
      {inc_rows}
    </table>
  </div>

  <!-- Azure -->
  <div class="section">
    <div class="section-title">Azure Tracker</div>
    <div class="chip-row">
      {_chip(len(azure_data), "Total", "#0ea5e9")}
      {_chip(az_new, "New", "#8b5cf6")}
      {_chip(sum(1 for r in azure_data if r.get("Status","")=="Active"), "Active", "#22c55e")}
    </div>
  </div>

  <!-- PTC -->
  <div class="section">
    <div class="section-title">PTC Cases</div>
    <div class="chip-row">
      {_chip(len(ptc_data), "Total", "#8b5cf6")}
      {_chip(ptc_open, "Open", "#f59e0b")}
      {_chip(sum(1 for r in ptc_data if r.get("Status","")=="Closed"), "Closed", "#6b7280")}
    </div>
  </div>
</div>
<div class="footer">Ops Platform · Auto Alert · {now}</div>
</div></body></html>"""

    return {
        "should_send": should_send,
        "subject"    : f"[OPS ALERT] Critical thresholds breached — {now}",
        "html"       : html,
        "alerts"     : alerts,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  WINDCHILL MONITORING — alert builder
# ─────────────────────────────────────────────────────────────────────────────

def build_wm_alert(transactions, wvs_queue, worker_stats) -> dict:
    """
    Analyse Windchill data, decide if alert warranted, and build HTML.
    Returns  { "should_send": bool, "subject": str, "html": str, "alerts": list[str] }
    """
    T = THRESHOLDS
    now = datetime.now().strftime("%d %b %Y %H:%M")

    tx_failed  = [r for r in transactions if "FAIL" in (r.get("status","") or "").upper() or "ERR" in (r.get("status","") or "").upper()]
    wvs_failed = [r for r in wvs_queue   if "FAIL" in (r.get("status","") or "").upper()]

    high_fail_workers = []
    for w in worker_stats:
        try:
            pct = float(str(w.get("failed_pct","0")).replace("%","").strip())
            if pct >= T["wm_worker_fail_pct"]:
                high_fail_workers.append({**w, "_pct": pct})
        except Exception:
            pass

    alerts = []
    if len(tx_failed)  >= T["wm_tx_failed"]:     alerts.append(f"🔴 Transaction Failures: {len(tx_failed)} (threshold {T['wm_tx_failed']})")
    if len(wvs_failed) >= T["wm_wvs_failed"]:    alerts.append(f"🔴 WVS Queue Failures: {len(wvs_failed)}")
    if high_fail_workers:                          alerts.append(f"🟠 Workers with high failure rate: {', '.join(w['name'] for w in high_fail_workers)}")

    should_send = bool(alerts)

    alert_banner = ""
    if alerts:
        items = "".join(f"<li>{a}</li>" for a in alerts)
        alert_banner = f'<div class="alert-banner"><strong>⚠ Critical Alerts Triggered:</strong><ul style="margin:6px 0 0 16px;padding:0;">{items}</ul></div>'

    # Transactions table — most recent 15 failed
    tx_rows = _table_rows(tx_failed[:15], ["time","target","action","status","object","state","attempts","notes"])

    # WVS table
    wvs_rows = _table_rows(wvs_failed[:15], ["queue","job","status","name","version","user"])

    # Worker table
    wk_rows = _table_rows(worker_stats[:20], ["name","total","failed","success","failed_pct"])

    html = f"""<!DOCTYPE html><html><head>{_STYLE}</head><body><div class="wrap">
<div class="header">
  <h1>⚠ Windchill Monitoring — Critical Alert</h1>
  <p>Generated: {now} | Auto-triggered by threshold breach</p>
</div>
<div class="body">
  {alert_banner}

  <!-- Transactions -->
  <div class="section">
    <div class="section-title">Transaction Failures</div>
    <div class="chip-row">
      {_chip(len(transactions), "Total", "#f28c38")}
      {_chip(len(tx_failed), "Failed", "#ef4444")}
    </div>
    <table>
      <tr><th>Time</th><th>Target</th><th>Action</th><th>Status</th><th>Object</th><th>State</th><th>Attempts</th><th>Notes</th></tr>
      {tx_rows}
    </table>
  </div>

  <!-- WVS Queue -->
  <div class="section">
    <div class="section-title">WVS Queue — Failures</div>
    <div class="chip-row">
      {_chip(len(wvs_queue), "Total Jobs", "#0ea5e9")}
      {_chip(len(wvs_failed), "Failed", "#ef4444")}
    </div>
    <table>
      <tr><th>Queue</th><th>Job</th><th>Status</th><th>Name</th><th>Version</th><th>User</th></tr>
      {wvs_rows}
    </table>
  </div>

  <!-- Worker Stats -->
  <div class="section">
    <div class="section-title">Worker Statistics</div>
    <table>
      <tr><th>Worker</th><th>Total</th><th>Failed</th><th>Success</th><th>Fail %</th></tr>
      {wk_rows}
    </table>
  </div>
</div>
<div class="footer">Ops Platform · Windchill Alert · {now}</div>
</div></body></html>"""

    return {
        "should_send": should_send,
        "subject"    : f"[WM ALERT] Windchill critical thresholds breached — {now}",
        "html"       : html,
        "alerts"     : alerts,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  SUMMARY REPORT — all 8 trackers
# ─────────────────────────────────────────────────────────────────────────────

def build_summary_report(
    support_data, failure_data, incident_data, azure_data, ptc_data,
    transactions, wvs_queue, worker_stats
) -> str:
    """
    Build a single-page HTML summary report covering all 8 trackers.
    Returns raw HTML string (for inline render or email).
    """
    now = datetime.now().strftime("%d %b %Y %H:%M")

    fail_prod    = sum(1 for r in failure_data if (r.get("Environment","") or "").upper() == "PROD")
    sup_pending  = sum(1 for r in support_data if "Action Required" in str(r.get("Categories","") or r.get("Category","")))
    inc_on_hold  = sum(1 for r in incident_data if r.get("Status","") == "On Hold")
    inc_inprog   = sum(1 for r in incident_data if r.get("Status","") == "In Progress")
    az_new       = sum(1 for r in azure_data if r.get("Status","") == "New")
    az_active    = sum(1 for r in azure_data if r.get("Status","") == "Active")
    ptc_open     = sum(1 for r in ptc_data if r.get("Status","") not in ("Closed","Resolved","Cancelled"))
    tx_failed    = sum(1 for r in transactions if "FAIL" in (r.get("status","") or "").upper())
    wvs_failed   = sum(1 for r in wvs_queue   if "FAIL" in (r.get("status","") or "").upper())

    def section_card(title, color, chips_html, table_html, cols):
        return f"""
<div class="rep-card">
  <div class="rep-card-header" style="border-left:4px solid {color};">
    <span class="rep-card-title">{title}</span>
    <div class="chip-row" style="margin:0;">{chips_html}</div>
  </div>
  <div class="rep-card-body">
    <table><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr>{table_html}</table>
  </div>
</div>"""

    extra_style = """
    .rep-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    .rep-card { border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }
    .rep-card-header { background:#f9fafb; padding:10px 14px; display:flex;
                       align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }
    .rep-card-title { font-size:13px; font-weight:700; color:#111; }
    .rep-card-body { overflow-x:auto; }
    .rep-card-body table { margin:0; }
    .kpi-overview { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:20px; }
    .kpi-box { background:#fff; border:1px solid #e5e7eb; border-radius:8px;
               padding:12px 16px; text-align:center; }
    .kpi-box-val { font-size:26px; font-weight:800; }
    .kpi-box-lbl { font-size:10px; font-weight:600; text-transform:uppercase;
                   letter-spacing:.05em; color:#6b7280; margin-top:2px; }
    @media (max-width:600px){ .rep-grid{grid-template-columns:1fr;} .kpi-overview{grid-template-columns:repeat(2,1fr);} }
    """

    return f"""<!DOCTYPE html><html><head>
{_STYLE}
<style>{extra_style}</style>
<meta charset="utf-8">
<title>Ops Platform — Summary Report</title>
</head><body><div class="wrap" style="max-width:1100px;">
<div class="header">
  <h1>📊 Ops Platform — Summary Report</h1>
  <p>All 8 Trackers · Generated: {now}</p>
</div>
<div class="body">

  <!-- ── Overview KPI boxes ─────────────────────────────────────────── -->
  <div class="kpi-overview">
    <div class="kpi-box"><div class="kpi-box-val" style="color:#ef4444">{len(failure_data)}</div><div class="kpi-box-lbl">Integration Failures</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#3b82f6">{len(support_data)}</div><div class="kpi-box-lbl">Support Emails</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#f28c38">{len(incident_data)}</div><div class="kpi-box-lbl">Incidents</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#0ea5e9">{len(azure_data)}</div><div class="kpi-box-lbl">Azure Bugs</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#8b5cf6">{len(ptc_data)}</div><div class="kpi-box-lbl">PTC Cases</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#ef4444">{tx_failed}</div><div class="kpi-box-lbl">WM Tx Failures</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#dc2626">{wvs_failed}</div><div class="kpi-box-lbl">WVS Failures</div></div>
    <div class="kpi-box"><div class="kpi-box-val" style="color:#374151">{len(worker_stats)}</div><div class="kpi-box-lbl">WM Workers</div></div>
  </div>

  <!-- ── 8 tracker cards in 2-col grid ─────────────────────────────── -->
  <div class="rep-grid">

    {section_card("Integration Failures", "#ef4444",
      _chip(len(failure_data),"Total","#ef4444") + _chip(fail_prod,"PROD","#f59e0b"),
      _table_rows(sorted(failure_data, key=lambda r:r.get("Failure Time",""), reverse=True)[:8],
                  ["Failure Time","Integration","Environment","WC Server"]),
      ["Failure Time","Integration","Environment","Server"])}

    {section_card("Support Emails", "#3b82f6",
      _chip(len(support_data),"Total","#3b82f6") + _chip(sup_pending,"Pending","#ef4444"),
      _table_rows([r for r in support_data if "Action Required" in str(r.get("Categories","") or r.get("Category",""))][:8],
                  ["Date","From","Subject"]),
      ["Date","From","Subject"])}

    {section_card("Incident Tracker", "#f28c38",
      _chip(len(incident_data),"Total","#f28c38") + _chip(inc_on_hold,"On Hold","#ef4444") + _chip(inc_inprog,"In Progress","#3b82f6"),
      _table_rows(incident_data[:8], ["Number","Short Description","Priority","Status"]),
      ["Number","Short Description","Priority","Status"])}

    {section_card("Azure Tracker", "#0ea5e9",
      _chip(len(azure_data),"Total","#0ea5e9") + _chip(az_new,"New","#8b5cf6") + _chip(az_active,"Active","#22c55e"),
      _table_rows(azure_data[:8], ["Number","Title","Priority","Status"]),
      ["Number","Title","Priority","Status"])}

    {section_card("PTC Cases", "#8b5cf6",
      _chip(len(ptc_data),"Total","#8b5cf6") + _chip(ptc_open,"Open","#f59e0b"),
      _table_rows(ptc_data[:8], ["Number","Subject","Priority","Status"]),
      ["Number","Subject","Priority","Status"])}

    {section_card("WM — Transactions", "#f28c38",
      _chip(len(transactions),"Total","#f28c38") + _chip(tx_failed,"Failed","#ef4444"),
      _table_rows([r for r in transactions if "FAIL" in (r.get("status","") or "").upper()][:8],
                  ["time","target","action","status","object"]),
      ["Time","Target","Action","Status","Object"])}

    {section_card("WM — WVS Queue", "#0ea5e9",
      _chip(len(wvs_queue),"Total","#0ea5e9") + _chip(wvs_failed,"Failed","#ef4444"),
      _table_rows([r for r in wvs_queue if "FAIL" in (r.get("status","") or "").upper()][:8],
                  ["queue","job","status","name","user"]),
      ["Queue","Job","Status","Name","User"])}

    {section_card("WM — Worker Stats", "#374151",
      _chip(len(worker_stats),"Workers","#374151"),
      _table_rows(worker_stats[:8], ["name","total","failed","success","failed_pct"]),
      ["Worker","Total","Failed","Success","Fail %"])}

  </div>
</div>
<div class="footer">Ops Platform · Summary Report · {now} · All 8 Trackers</div>
</div></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
#  SMTP sender
# ─────────────────────────────────────────────────────────────────────────────

def send_alert_email(subject: str, html: str, to: list = None) -> dict:
    """
    Send an HTML email. Returns { "success": bool, "message": str }.
    If SMTP_PASSWORD is empty, logs a warning and returns success=False.
    """
    import os
    recipients = to or ALERT_TO
    password   = SMTP_PASSWORD or os.environ.get("EMAIL_PASSWORD", "")

    if not password:
        log.warning("EMAIL_PASSWORD not set — email not sent. Set env var EMAIL_PASSWORD or SMTP_PASSWORD in email_notifier.py")
        return {"success": False, "message": "SMTP password not configured. Set EMAIL_PASSWORD env variable."}

    try:
        msg                    = MIMEMultipart("alternative")
        msg["Subject"]         = subject
        msg["From"]            = ALERT_FROM
        msg["To"]              = ", ".join(recipients)
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, password)
            server.sendmail(ALERT_FROM, recipients, msg.as_string())

        log.info(f"Alert email sent to {recipients}: {subject}")
        return {"success": True, "message": f"Email sent to {', '.join(recipients)}"}

    except Exception as exc:
        log.error(f"Email send failed: {exc}")
        return {"success": False, "message": str(exc)}
