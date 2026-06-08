# help/dcn_analytics_help.py
from flask import Blueprint, jsonify

dcn_help_bp = Blueprint("dcn_analytics_help", __name__)

@dcn_help_bp.route("/api/help/dcn-analytics")
def get_dcn_analytics_help():
    """Returns structured index and content data for the DCN Help Engine."""
    help_data = {
        "module_title": "DCN Analytics Help Guide",
        "topics": [
            {
                "id": "overview",
                "title": "📋 Dashboard Overview",
                "content": "<h3>Dashboard Overview</h3><p>The DCN Analytics Dashboard provides an interactive visibility matrix tracking sequence anomalies, gaps, and skipped numbers within your master data logs.</p><h4>Core Visualizations:</h4><ul><li><b>Monthly Trend Chart:</b> Displays a historical breakdown of sequence gaps, toggleable between Bar, Line, and Yearly Pie chart aggregations.</li><li><b>Monthly Pivot Summary:</b> An operations matrix organizing actual skipped frequencies by month and calendar year with automated live summary math.</li></ul>"
            },
            {
                "id": "filters",
                "title": "🔍 Filtering Options",
                "content": "<h3>Filtering Options Guide</h3><p>Use the filtering dock panel on the left side of the screen to isolate metric subsets safely without mutating the master dataset.</p><h4>Filter Rules:</h4><ul><li><b>Date Range:</b> Filters sequence anomalies strictly between a custom Start and End calendar boundary.</li><li><b>By Year:</b> Filters using an array match against all checked year boxes (2023-2026).</li><li><b>Quick Select:</b> Generates relative windows tracking backward from your newest master entry date (e.g., Last 7, 30, or 90 days).</li></ul>"
            },
            {
                "id": "upload",
                "title": "📤 Data Uploads",
                "content": "<h3>Uploading Master Datasets</h3><p>To refresh the dashboard visualization engine manually with an offline log entry, use the <b>Upload Latest Excel</b> toolbar button.</p><h4>System Processing Rules:</h4><ul><li>The engine parses incoming streams, validates columns, and saves the file directly into your secure backend repository.</li><li>The file is automatically normalized and saved directly to <code>data/DCN-analytics.xlsx</code>, overwriting the previous cache file seamlessly.</li></ul>"
            },
            {
                "id": "exports",
                "title": "⬇ Report Exports",
                "content": "<h3>Exporting Operational Data</h3><p>The download engine delivers production-ready Excel sheets configured with strict corporate font scaling to eliminate post-activity cleanups.</p><h4>Available Workbooks:</h4><ul><li><b>Full Excel Dashboard:</b> Ships a beautifully stylized master spreadsheet built natively with Calibri, complete with zero gridlines, frozen header panels, hidden unused columns, an interactive pivot table, and a live, editable embedded chart object.</li><li><b>Raw Lists:</b> Simple isolated CSV/XLSX extractions of filtered intervals.</li></ul>"
            }
        ]
    }
    return jsonify(help_data)