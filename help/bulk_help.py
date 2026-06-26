# =============================================================================
#  BULK REPORT GENERATOR — HELP CONTENT API
#  bulk/bulk_help.py
#
#  Register in app.py:
#      from bulk.bulk_help import bulk_help_bp
#      app.register_blueprint(bulk_help_bp)
# =============================================================================

from flask import Blueprint, jsonify

bulk_help_bp = Blueprint("bulk_help", __name__)

_BULK_HELP_TOPICS = [
    {
        "id":      "overview",
        "title":   "📦 Module Overview",
        "content": """
            <h3>Bulk Report Generator</h3>
            <p>The Bulk Report Generator creates RCA documents for multiple
               ServiceNow incidents in a single batch operation. It uses the
               same intelligent RCA classification engine as the single-incident
               Report module.</p>
            <ul>
                <li>Enter one or more incident numbers separated by commas.</li>
                <li>Select output format (PDF, Word, or Both).</li>
                <li>Click <strong>Generate Reports</strong> — all documents are
                    packaged into a single ZIP for download.</li>
            </ul>
        """,
    },
    {
        "id":      "input",
        "title":   "✏️ Entering Incidents",
        "content": """
            <h3>Entering Incident Numbers</h3>
            <p>Type incident numbers into the <strong>Bulk Input</strong> text
               area, separated by commas:</p>
            <p><code>INC109720389, INC109720400, INC109720512</code></p>
            <p>The system reads each number from <code>data/Snow.xlsx</code>,
               generates the RCA, and adds the document to the batch ZIP.</p>
            <p>Incidents not found in the data file are logged as failed and
               appear in the <strong>Failed</strong> filter of the results table.
               Use <strong>⚠ Failed Report</strong> to download a CSV of
               failed incident numbers for retry.</p>
        """,
    },
    {
        "id":      "output-types",
        "title":   "📥 Output Types",
        "content": """
            <h3>Output Types</h3>
            <p>Select the format using the <strong>Output Type</strong> dock
               (⚡ icon) before generating:</p>
            <ul>
                <li><strong>PDF</strong> — one PDF per incident.</li>
                <li><strong>Word</strong> — one <code>.docx</code> per incident.</li>
                <li><strong>Both</strong> — PDF and Word for every incident,
                    all in one ZIP.</li>
            </ul>
            <p>The selected type is shown in the Results table under
               <em>Output Type</em>.</p>
        """,
    },
    {
        "id":      "filters",
        "title":   "🔍 Filters",
        "content": """
            <h3>Filters</h3>
            <p>Use the <strong>Filters</strong> dock (funnel icon) to narrow
               which incidents are processed:</p>
            <ul>
                <li><strong>Priority</strong> — process only incidents of a
                    specific priority level.</li>
                <li><strong>Date Range</strong> — use a preset (1 Week, 1 Month,
                    etc.) or pick custom From / To dates.</li>
                <li><strong>Year</strong> — filter by incident creation year.</li>
            </ul>
            <p>Filters apply when you click <strong>Generate Reports</strong>.</p>
        """,
    },
    {
        "id":      "results",
        "title":   "📊 Results Table",
        "content": """
            <h3>Results Table</h3>
            <p>The <strong>Bulk Results</strong> table shows the outcome for
               each incident after generation:</p>
            <ul>
                <li><strong>All</strong> — shows every processed incident.</li>
                <li><strong>Successful</strong> — incidents where documents
                    were generated without errors.</li>
                <li><strong>Failed</strong> — incidents that could not be
                    processed (not found, data errors, etc.).</li>
            </ul>
            <p>Click <strong>Resend Failed Jobs</strong> to retry all failed
               incidents automatically.</p>
        """,
    },
    {
        "id":      "downloads",
        "title":   "⬇ Downloads",
        "content": """
            <h3>Downloads</h3>
            <p>After generation completes, use the <strong>Downloads</strong>
               dock (⬇ icon):</p>
            <ul>
                <li><strong>⬇ Download ZIP</strong> — downloads all generated
                    documents in a single ZIP archive.</li>
                <li><strong>⚠ Failed Report</strong> — downloads a CSV listing
                    all incident numbers that failed, for re-submission or
                    manual handling.</li>
            </ul>
        """,
    },
    {
        "id":      "logs",
        "title":   "📋 Activity Logs",
        "content": """
            <h3>Activity Logs</h3>
            <p>All bulk generation activity is logged to:</p>
            <p><code>&lt;project_root&gt;/logs/bulk.log</code></p>
            <p>Each entry includes timestamp, level, module, and details.
               Check this log first when diagnosing batch failures or
               unexpected empty outputs.</p>
        """,
    },
]


@bulk_help_bp.route("/api/help/bulk")
def bulk_help_api():
    return jsonify({
        "module_title": "Bulk Report Generator — Help Guide",
        "topics":       _BULK_HELP_TOPICS,
    })
