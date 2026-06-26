from flask import Blueprint, jsonify
log_analyzer_help_bp = Blueprint("log_analyzer_help", __name__)

_TOPICS = [
{
    "id": "overview", "title": "📋 Overview",
    "content": """
<h3>Log Analyzer — Windchill Log4j Analyzer</h3>
<p>Reads and analyzes Windchill <strong>MethodServer log4j</strong> files directly in your browser.
No upload — all parsing happens locally. Multiple log files can be loaded together and are
automatically merged and sorted by timestamp.</p>

<h4>Log format parsed</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;line-height:1.6;">
2026-06-25 10:58:56,336 ERROR [ajp-nio-127.0.0.1-8011-exec-103]
    wt.servlet.ServletRequestMonitor.request A546072 - message text
    java.lang.Exception: stack trace line 1
        at com.ptc.method(...)
</pre>
<p>Multi-line stack traces are grouped with their parent log entry.</p>

<h4>Data privacy</h4>
<p>⚠️ <strong>All log data stays on your laptop.</strong> Files are read using the browser
File API — no bytes are transmitted over the network. Summary reports are saved only to
your local <code>outputs/log_analyzer/</code> folder.</p>""",
},
{
    "id": "open_file", "title": "📂 Opening Files",
    "content": """
<h3>Opening Log Files</h3>
<h4>Single file</h4>
<p>Click the drop zone or drag a <code>MethodServer-*.log.*</code> file onto the sidebar.</p>

<h4>Multiple files (recommended)</h4>
<p>Select all log rotation files at once (Ctrl+click in file picker, or drag multiple files).
They are automatically sorted by filename and merged chronologically by timestamp.</p>
<p>Example: load all 5 files together:</p>
<pre style="background:#0f172a;color:#e2e8f0;padding:8px;border-radius:5px;font-size:11px;">
MethodServer-…-log4j.log.2026-06-25_1   (9.2 MB)
MethodServer-…-log4j.log.2026-06-25_2   (9.2 MB)
MethodServer-…-log4j.log.2026-06-25_4   (9.2 MB)
MethodServer-…-log4j.log.2026-06-25_5   (9.2 MB)</pre>

<h4>Reading progress</h4>
<p>A card shows bytes read, lines parsed, total entries found, and error count in real time.</p>

<h4>Row cap</h4>
<p>Up to <strong>500,000 log entries</strong> are kept in memory. For very large combined
log sets, use the timestamp filters to focus on the incident window.</p>""",
},
{
    "id": "table", "title": "📊 Table View",
    "content": """
<h3>Table View — Log Entries</h3>
<p>Each row is one log entry with these columns:</p>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Column</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Example</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Description</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Timestamp</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">2026-06-25 10:58:56.336</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Date + time with milliseconds</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Level</td><td style="padding:5px 8px;border:1px solid #e2e8f0;"><span style="background:#fee2e2;color:#991b1b;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:700;">ERROR</span></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">FATAL / ERROR / WARN / INFO / DEBUG</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Thread</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">ajp-nio-127.0.0.1-8011-exec-103</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Server thread name</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Logger</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">wt.servlet.ServletRequestMonitor</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Java class that logged the entry</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">User</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">A546072</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">User or session identifier</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Message</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">**** Preferred Site is not found…</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Log message text</td></tr>
  </tbody>
</table>
<h4>Row colours</h4>
<ul>
  <li><span style="background:#fff1f2;padding:1px 6px;border-radius:3px;">Pink</span> — FATAL entries</li>
  <li><span style="background:#fff5f5;padding:1px 6px;border-radius:3px;">Light red</span> — ERROR entries</li>
  <li><span style="background:#fffbeb;padding:1px 6px;border-radius:3px;">Yellow</span> — WARN entries</li>
</ul>
<h4>Stack trace popup</h4>
<p>Rows with a <strong>＋</strong> button have a multi-line stack trace. Click it to open
a detail popup showing the full exception.</p>""",
},
{
    "id": "filter", "title": "🔍 Filter & Navigate",
    "content": """
<h3>Filter &amp; Navigate</h3>
<p>All filters in the 🔍 panel apply instantly as you type.</p>

<h4>Timestamp range</h4>
<p>Enter partial timestamps — <code>2026-06-25 10:58</code> filters to that minute.</p>

<h4>Level toggles</h4>
<p>Click level pills to include/exclude levels. Combine to show only what you need:
e.g. click WARN, INFO, DEBUG to deselect them and see only ERROR + FATAL.</p>

<h4>Thread filter</h4>
<p>Filter to a specific server thread: <code>exec-103</code> or <code>8011</code></p>

<h4>Logger / Class filter</h4>
<p>Filter by Java class: <code>wt.servlet</code>, <code>ServletRequestMonitor</code>,
<code>wt.identity</code></p>

<h4>User / Session ID</h4>
<p>Filter to a specific user session: <code>A546072</code>, <code>b0pl980</code></p>

<h4>Message filter</h4>
<p>Text search in message + stack trace: <code>Exception</code>, <code>Preferred Site</code>,
<code>BusinessAlgorithm</code>, <code>500</code></p>

<h4>Jump to Timestamp</h4>
<p>Enter a timestamp and click ⏩ Jump. Uses binary search — jumps instantly even in
500,000-entry datasets.</p>

<h4>Quick search (toolbar)</h4>
<p>Searches across all columns simultaneously.</p>""",
},
{
    "id": "summary_panel", "title": "📊 Error Summary",
    "content": """
<h3>Error Summary Panel</h3>
<p>Open the 📊 Summary panel to see a quick overview of the loaded logs.</p>

<h4>KPI boxes</h4>
<p>Shows counts of FATAL, ERROR, WARN, and INFO entries across all loaded files.</p>

<h4>Top Error Patterns</h4>
<p>The 8 most frequent error/warning message patterns, with counts. Click the 🔍 button
next to any pattern to filter the table to those entries immediately.</p>

<h4>Top Loggers with Errors</h4>
<p>The 6 Java classes that produced the most errors/warnings. Click 🔍 to filter.</p>

<h4>Quick Filters</h4>
<ul>
  <li><strong>Show only ERRORs</strong> — hides all other levels</li>
  <li><strong>Show only WARNs</strong></li>
  <li><strong>Show only FATALs</strong></li>
  <li><strong>ERRORs + WARNs + FATALs</strong> — the most useful view for incident analysis</li>
  <li><strong>Show All</strong> — clears all level filters</li>
</ul>""",
},
{
    "id": "report", "title": "📄 Summary Report",
    "content": """
<h3>Downloadable Summary Report</h3>
<p>Click <strong>⬇ Download Summary</strong> to generate a structured report of errors
found in the loaded log files.</p>

<h4>Report contents</h4>
<ul>
  <li>File metadata (names, sizes, entry count, time range)</li>
  <li>Error level counts (FATAL / ERROR / WARN / INFO)</li>
  <li>Top 20 error message patterns with occurrence counts</li>
  <li>Top 10 loggers (Java classes) with the most errors</li>
  <li>Top 10 users/sessions involved in errors</li>
  <li>All ERROR and FATAL entries (up to 5,000) with timestamps</li>
</ul>

<h4>Output location</h4>
<p>Saved to: <code>ops-platform/outputs/log_analyzer/</code><br>
Filename: <code>log_summary_YYYYMMDD_HHMMSS.txt</code></p>

<p>⚠️ The report file is written locally only — it is never transmitted externally.</p>""",
},
{
    "id": "troubleshoot", "title": "🔧 Troubleshooting",
    "content": """
<h3>Troubleshooting</h3>

<h4>❌ No entries appear after loading</h4>
<p>The log file format may not match the expected log4j pattern. The parser expects:</p>
<pre style="background:#0f172a;color:#e2e8f0;padding:8px;border-radius:5px;font-size:11px;">
YYYY-MM-DD HH:MM:SS,mmm LEVEL [thread] logger user - message</pre>
<p>Check that the file starts with a line in this format. Plain text log files with
a different pattern will show in Raw view.</p>

<h4>❌ Only partial entries visible</h4>
<p>The 500,000 entry cap was reached. Use timestamp filters in the Filter panel to
narrow down to the incident time window before loading, or split the file externally.</p>

<h4>❌ Stack traces not shown</h4>
<p>Stack traces appear as a <strong>＋</strong> button on the row. Click it to open
the detail popup. If the button is not visible, the entry has no continuation lines.</p>

<h4>❌ Multiple files not merged correctly</h4>
<p>Files are merged by timestamp after all are parsed. Ensure all files cover the same
date range and use the same log4j timestamp format. If a file uses a different format,
those entries may sort to the beginning (empty timestamp).</p>

<h4>❌ Summary report not downloading</h4>
<p>Check that the <code>outputs/log_analyzer/</code> folder exists or can be created.
The server must have write permission to the <code>outputs/</code> directory.</p>""",
},
]

@log_analyzer_help_bp.route("/api/help/log-analyzer")
def log_analyzer_help_api():
    return jsonify({"module_title": "📋 Log Analyzer — Help", "topics": _TOPICS})
