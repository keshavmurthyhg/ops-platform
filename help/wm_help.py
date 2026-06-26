# =============================================================================
#  WINDCHILL MONITORING — HELP CONTENT API
#  windchill_monitoring/wm_help.py
#
#  Serves the help topics consumed by the platform's common help modal.
#  The common.js toggleHelpSystemModal() opens #helpSystemModal and calls
#  loadModuleHelpData(), which fetches GET /api/help/windchill-monitoring.
#
#  This file must be registered as a Blueprint in the main app:
#      from windchill_monitoring.wm_help import wm_help_bp
#      app.register_blueprint(wm_help_bp)
# =============================================================================

from flask import Blueprint, jsonify

# Blueprint — no static folder needed (content is returned as JSON)
wm_help_bp = Blueprint("wm_help", __name__)


# ── Help topic definitions ────────────────────────────────────────────────────

_WM_HELP_TOPICS = [
    {
        "id"     : "overview",
        "title"  : "📊 Dashboard Overview",
        "content": """
            <h3>Dashboard Overview</h3>
            <p>The Windchill Active Operations Monitoring dashboard provides real-time
               visibility into three critical Windchill subsystems:</p>
            <ul>
                <li><strong>⚠️ Integration Failures</strong> — failed transaction exports
                    from Windchill to downstream systems over the last 7 days.</li>
                <li><strong>⚡ WVS Job Queue</strong> — live queue of CAD visualisation
                    (WVS) jobs in Ready, Executing, or Failed state.</li>
                <li><strong>🖥️ CAD Worker Stats</strong> — publishing performance metrics
                    per worker node including failure rates and busy-time.</li>
            </ul>
            <p>All three panels update automatically every <strong>30 minutes</strong>
               when automation is running, or on demand via <strong>Run Now</strong>
               in the sidebar.</p>
        """,
    },
    {
        "id"     : "automation",
        "title"  : "⚙️ Automation Setup",
        "content": """
            <h3>Automation Setup</h3>
            <p>The monitoring tool connects to Windchill through Edge running in
               remote debug mode on port <code>9222</code>.</p>
            <h4>First-Time Setup</h4>
            <ol>
                <li>Click <strong>Launch Edge Debug</strong> in the sidebar — this starts
                    Edge with <code>--remote-debugging-port=9222</code>.</li>
                <li>Log in to Windchill inside that Edge window if prompted.</li>
                <li>Click <strong>Run Now</strong> to immediately scrape Failures
                    and the WVS Queue.</li>
            </ol>
            <h4>Auto-Refresh</h4>
            <p>Once running, the scraper repeats every <strong>30 minutes</strong>
               automatically. The sidebar shows the last run time.</p>
            <p><strong>Important:</strong> Edge must remain open for automation to work.
               Do not close the Edge debug window during a session.</p>
        """,
    },
    {
        "id"     : "workers",
        "title"  : "🖥️ Worker Statistics",
        "content": """
            <h3>Collecting Worker Statistics</h3>
            <p>Worker statistics require a short manual step inside the Windchill UI:</p>
            <ol>
                <li>In the Edge debug window, navigate to the WVS Monitor page.</li>
                <li>Click <strong>Actions → Job Statistics</strong> to open the popup.</li>
                <li>Inside the popup, click
                    <strong style="color:#fbbf24;">Display Summary Statistics</strong>.</li>
                <li>Wait approximately <strong>2 minutes</strong> for Windchill to
                    compute the totals.</li>
                <li>Return to this dashboard and click
                    <strong style="color:#86efac;">Collect Stats</strong>
                    in the sidebar.</li>
            </ol>
            <p>Collected stats are saved to
               <code>&lt;project_root&gt;/data/history/worker_stats_history.csv</code>
               for trend analysis.</p>
        """,
    },
    {
        "id"     : "exports",
        "title"  : "📥 Exporting Reports",
        "content": """
            <h3>Exporting Reports</h3>
            <p>Switch to the <strong>Reports</strong> dock (📊 icon) in the left
               sidebar and click the relevant button:</p>
            <ul>
                <li><strong>📥 Export Failures</strong> — downloads the full integration
                    failure log as a CSV file.</li>
                <li><strong>📥 Export WVS Queue</strong> — downloads the current job
                    queue snapshot as CSV.</li>
                <li><strong>📥 Export Workers</strong> — downloads CAD worker performance
                    data as CSV.</li>
            </ul>
            <p>Files are saved to your browser's default download folder with a
               timestamped filename.</p>
        """,
    },
    {
        "id"     : "alerts",
        "title"  : "🚨 Alert Thresholds",
        "content": """
            <h3>Alert Thresholds</h3>
            <p>The dashboard raises automatic alerts when these conditions are met:</p>
            <ul>
                <li><strong>Worker failure rate &gt; 40%</strong> — a warning badge
                    appears on the Worker Stats panel and a modal alert is raised.</li>
                <li><strong>WVS Ready queue &gt; 750 jobs and growing</strong> — raised
                    after 3 consecutive refreshes with an increasing Ready count.</li>
                <li><strong>Executing jobs stuck</strong> — if the same job appears
                    in Executing state across 3+ refreshes, an alert is triggered.</li>
            </ul>
            <p>Click <strong>Acknowledge</strong> in the alert modal to dismiss it.
               Alerts re-trigger on the next refresh if the condition persists.</p>
        """,
    },
    {
        "id"     : "logs",
        "title"  : "📋 Activity Logs",
        "content": """
            <h3>Activity Logs</h3>
            <p>All Windchill monitoring activity is logged to:</p>
            <p><code>&lt;project_root&gt;/logs/windchill_monitoring.log</code></p>
            <p>Log files rotate at 5 MB and keep 7 backups. Each entry includes:</p>
            <ul>
                <li>Timestamp (YYYY-MM-DD HH:MM:SS)</li>
                <li>Level — INFO, WARNING, or ERROR</li>
                <li>Module name</li>
                <li>Activity description and any exception detail</li>
            </ul>
            <p>Use these logs to diagnose Edge connection failures, scraping errors,
               or unexpected empty panels after a Run Now.</p>
        """,
    },
]


# ── API endpoint ──────────────────────────────────────────────────────────────

@wm_help_bp.route("/api/help/windchill-monitoring")
def wm_help_api():
    """
    Return the help topics for the Windchill Monitoring module.
    Called automatically by common.js loadModuleHelpData() when the
    platform ? button is clicked.
    """
    return jsonify({
        "module_title": "Windchill Monitoring — Help Guide",
        "topics"      : _WM_HELP_TOPICS,
    })
