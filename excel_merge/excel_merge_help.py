# =============================================================================
#  EXCEL MERGE TOOL — HELP CONTENT API
#  excel_merge/excel_merge_help.py
#
#  Register in app.py:
#      from excel_merge.excel_merge_help import excel_merge_help_bp
#      app.register_blueprint(excel_merge_help_bp)
# =============================================================================

from flask import Blueprint, jsonify

excel_merge_help_bp = Blueprint("excel_merge_help", __name__)

_EXCEL_MERGE_HELP_TOPICS = [
    {
        "id":      "overview",
        "title":   "📊 Module Overview",
        "content": """
            <h3>Excel Merge Tool</h3>
            <p>The Excel Merge Tool combines two ServiceNow Excel exports (Old and New)
               into a single deduplicated master file. It detects new rows, updated cells,
               and duplicate entries, giving you a clean merged output with full
               change visibility.</p>
            <ul>
                <li>Upload the <strong>Old Excel</strong> (earlier export) and
                    <strong>New Excel</strong> (latest export).</li>
                <li>Specify the unique key column (e.g. <code>number</code>) and
                    your preferred merge strategy.</li>
                <li>Preview the merged result in the table, then download the
                    final <code>.xlsx</code> file.</li>
            </ul>
        """,
    },
    {
        "id":      "files",
        "title":   "📂 Uploading Files",
        "content": """
            <h3>Uploading Files</h3>
            <ol>
                <li>Click <strong>Choose Old Excel</strong> to select your earlier
                    <code>.xlsx</code> export (e.g. <code>Snow_22Apr2025.xlsx</code>).</li>
                <li>Click <strong>Choose New Excel</strong> to select the latest export
                    (e.g. <code>Snow_18Jun2026.xlsx</code>).</li>
                <li>The selected filenames appear next to each button in the toolbar.</li>
            </ol>
            <p>Both files must use the same column structure. The system normalises
               column headers (lowercased, stripped) before merging, so minor header
               casing differences are handled automatically.</p>
        """,
    },
    {
        "id":      "settings",
        "title":   "⚙️ Merge Settings",
        "content": """
            <h3>Merge Settings (Actions Panel)</h3>
            <p>Configure the merge via the <strong>Actions</strong> dock (⚙️ icon):</p>
            <ul>
                <li><strong>Unique Key Column</strong> — the column that uniquely
                    identifies each row (e.g. <code>number</code> for incident numbers).
                    Required — merge will fail without this.</li>
                <li><strong>Prefer New File / Prefer Old File</strong> — when the same
                    key exists in both files and the values differ, this controls which
                    file's data wins. <em>Prefer New File</em> is the default and
                    recommended for most use cases.</li>
                <li><strong>Date Column</strong> — optional. If set, the row with the
                    most recent date in this column is kept when duplicates are found.</li>
            </ul>
        """,
    },
    {
        "id":      "kpi",
        "title":   "📈 KPI Summary",
        "content": """
            <h3>KPI Summary</h3>
            <p>After a successful merge the KPI strip above the results table shows:</p>
            <ul>
                <li><strong>Total Rows</strong> — total records in the merged output.</li>
                <li><strong>Updated Rows</strong> — rows where one or more cell values
                    changed between old and new files (highlighted in amber in the table).</li>
                <li><strong>New Rows</strong> — rows present in the new file but not in
                    the old file (highlighted in green in the table).</li>
                <li><strong>Duplicates Removed</strong> — rows deduplicated based on
                    the unique key column and date column logic.</li>
            </ul>
        """,
    },
    {
        "id":      "table",
        "title":   "🗂 Preview Table",
        "content": """
            <h3>Preview Table</h3>
            <p>The merged results are shown in an interactive scrollable table:</p>
            <ul>
                <li>The <strong>first column</strong> (incident number / key) is frozen
                    and stays visible while scrolling horizontally.</li>
                <li><span style="background:#dcfce7;padding:2px 8px;border-radius:4px;color:#166534">
                    Green rows</span> — records that are new (only in the new file).</li>
                <li><span style="background:#fef3c7;padding:2px 8px;border-radius:4px;color:#92400e">
                    Amber cells</span> — individual cells where values changed.</li>
                <li>Hover over any truncated cell to see the full value in a tooltip.</li>
            </ul>
        """,
    },
    {
        "id":      "download",
        "title":   "⬇ Downloading Output",
        "content": """
            <h3>Downloading the Merged File</h3>
            <p>After a successful merge, the <strong>Download Output</strong> button
               appears in the toolbar. Click it to download the merged
               <code>.xlsx</code> file.</p>
            <p>The download includes all columns from both source files, with the
               merge strategy applied. Updated and new rows are preserved exactly
               as shown in the preview table.</p>
        """,
    },
    {
        "id":      "logs",
        "title":   "📋 Activity Logs",
        "content": """
            <h3>Activity Logs</h3>
            <p>All merge activity is logged to:</p>
            <p><code>&lt;project_root&gt;/logs/excel_merge.log</code></p>
            <p>Each entry includes timestamp, level, module, and details. Check
               this log when diagnosing merge failures, key column errors, or
               unexpected row counts.</p>
        """,
    },
]


@excel_merge_help_bp.route("/api/help/excel-merge")
def excel_merge_help_api():
    return jsonify({
        "module_title": "Excel Merge Tool — Help Guide",
        "topics":       _EXCEL_MERGE_HELP_TOPICS,
    })
