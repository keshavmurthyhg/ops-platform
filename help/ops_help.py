# =============================================================================
#  OPERATIONS CENTER — HELP CONTENT API
#  operations_center/ops_help.py
#
#  Serves the help topics consumed by the platform's common help modal.
#  The common.js toggleHelpSystemModal() opens #helpSystemModal and calls
#  loadModuleHelpData(), which fetches GET /api/help/operations-center.
#
#  This file must be registered as a Blueprint in the main app:
#      from operations_center.ops_help import ops_help_bp
#      app.register_blueprint(ops_help_bp)
# =============================================================================

from flask import Blueprint, jsonify

# Blueprint — no static folder needed (content is returned as JSON)
ops_help_bp = Blueprint("ops_help", __name__)


# ── Help topic definitions ────────────────────────────────────────────────────
# Each topic has:
#   id      — unique string used for internal routing
#   title   — shown in the left index pane
#   content — raw HTML rendered in the right content pane

_OPS_HELP_TOPICS = [
    {
        "id"     : "overview",
        "title"  : "📊 Dashboard Overview",
        "content": """
            <h3>Dashboard Overview</h3>
            <p>The Operations Center aggregates live data from five sources into a
               single unified monitoring view:</p>
            <ul>
                <li><strong>Support Emails</strong> — Outlook inbox items flagged for action.</li>
                <li><strong>PROD Failures</strong> — Integration failure log from Windchill.</li>
                <li><strong>SNOW Incidents</strong> — ServiceNow tickets assigned to the team.</li>
                <li><strong>Azure Bugs</strong> — Active DevOps bugs tracked in Azure.</li>
                <li><strong>PTC Cases</strong> — Open support cases from the PTC portal.</li>
            </ul>
            <p>Click any KPI tile at the top to jump to the full table for that category.
               The three mini cards on the dashboard show the most recent items from each
               live data source with a last-updated timestamp at the bottom.</p>
        """,
    },
    {
        "id"     : "data-sources",
        "title"  : "📂 Data Source Files",
        "content": """
            <h3>Data Sources &amp; File Locations</h3>
            <p>The dashboard reads from three source files inside the <code>data/</code>
               folder (relative to the ops-platform project root):</p>
            <ul>
                <li><code>data/Snow.xlsx</code> — ServiceNow incident export (Excel format)</li>
                <li><code>data/Azure.csv</code> — Azure DevOps bug export (CSV format)</li>
                <li><code>data/Ptc.csv</code> — PTC Case Tracker CSV export</li>
            </ul>
            <p>To update these files, use the <strong>📡 Data Collectors</strong> dock
               (third icon in the left sidebar) and click
               <strong>Upload Data Files</strong>. Files are saved with the correct
               canonical names automatically.</p>
            <h4>Last-Updated Timestamps</h4>
            <p>The bottom of each mini card shows when its source file was last written
               to disk. If a timestamp looks stale, refresh via the Data Collectors dock.</p>
        """,
    },
    {
        "id"     : "ptc-refresh",
        "title"  : "🛠 Refreshing PTC Cases",
        "content": """
            <h3>Refreshing PTC Cases Automatically</h3>
            <p>To download the latest PTC cases without logging into the portal manually:</p>
            <ol>
                <li>Open the <strong>📡 Data Collectors</strong> dock in the sidebar.</li>
                <li>Click <strong>Launch Edge (Debug)</strong> — opens Edge on port 9222.</li>
                <li>Log in to the PTC portal in that Edge window if prompted.</li>
                <li>Click <strong>Refresh PTC Cases</strong> — the script opens the
                    All Filters panel, sets Opened By = Both, Status = Both,
                    Date = 01-Jan-2020 → today, clicks Apply, waits for all rows
                    to load, then exports and saves as <code>data/Ptc.csv</code>.</li>
            </ol>
            <p><strong>Note:</strong> The full table load (5000+ rows) takes 1–2 minutes.
               The script waits automatically.</p>
        """,
    },
    {
        "id"     : "filters",
        "title"  : "🔍 Filtering &amp; Searching",
        "content": """
            <h3>Filtering &amp; Searching</h3>
            <p>Use the <strong>Filters</strong> dock (funnel icon) in the left sidebar
               to narrow results within any active section:</p>
            <ul>
                <li>Filters apply to the currently visible tab (Support, Incidents, etc.).</li>
                <li>Click <strong>Apply Filters</strong> in the toolbar to refresh the view.</li>
                <li>Click <strong>Clear Workspace</strong> to reset all active filters.</li>
            </ul>
            <p>Each table section also has an inline search bar that filters rows
               in real-time without reloading data from the server.</p>
            <p>The global search icon (🔍) in the top-right searches all visible
               text on the current page and highlights matches in yellow.</p>
        """,
    },
    {
        "id"     : "exports",
        "title"  : "📥 Exporting Data",
        "content": """
            <h3>Exporting Data</h3>
            <p>Switch to the <strong>Downloads</strong> dock (⬇ icon) in the sidebar:</p>
            <ul>
                <li><strong>Export CSV</strong> — downloads the current view as a
                    comma-separated file, respecting active filters.</li>
                <li><strong>Export Excel</strong> — downloads as a formatted XLSX file.</li>
            </ul>
            <p>Only the rows visible in the current section and filter state are
               included in the export.</p>
        """,
    },
    {
        "id"     : "collectors",
        "title"  : "📡 Data Collectors Dock",
        "content": """
            <h3>Data Collectors Dock</h3>
            <p>The third dock icon (📡) opens the Data Collectors panel with buttons for
               each data source:</p>
            <ul>
                <li><strong>🔄 Refresh Incidents</strong> — calls the ServiceNow collector
                    API to pull the latest incidents.</li>
                <li><strong>🔄 Refresh Azure</strong> — pulls the latest Azure DevOps bugs.</li>
                <li><strong>🌐 Launch Edge (Debug)</strong> — opens Edge on port 9222,
                    required for the PTC automation.</li>
                <li><strong>🔄 Refresh PTC Cases</strong> — runs the automated PTC download.</li>
                <li><strong>📂 Upload Data Files</strong> — manually upload raw export files;
                    they are renamed and saved to the correct location automatically.</li>
            </ul>
            <p>A status message appears below each button showing success or error details.</p>
        """,
    },
    {
        "id"     : "logs",
        "title"  : "📋 Activity Logs",
        "content": """
            <h3>Activity Logs</h3>
            <p>All Operations Center activity is logged to:</p>
            <p><code>&lt;project_root&gt;/logs/operations_center.log</code></p>
            <p>Log files use rotating storage (5 MB × 7 backups). Each line includes:</p>
            <ul>
                <li>Timestamp (YYYY-MM-DD HH:MM:SS)</li>
                <li>Level — INFO, WARNING, or ERROR</li>
                <li>Module name</li>
                <li>Activity description</li>
            </ul>
            <p>Check this log first when diagnosing data-loading failures, PTC
               download issues, or unexpected empty dashboards.</p>
        """,
    },
]


# ── API endpoint ──────────────────────────────────────────────────────────────

@ops_help_bp.route("/api/help/operations-center")
def ops_help_api():
    """
    Return the help topics for the Operations Center module.
    Called automatically by common.js loadModuleHelpData() when the
    platform ? button is clicked.
    """
    return jsonify({
        "module_title": "Operations Center — Help Guide",
        "topics"      : _OPS_HELP_TOPICS,
    })
