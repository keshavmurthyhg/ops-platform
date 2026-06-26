from flask import Blueprint, jsonify
gz_reader_help_bp = Blueprint("gz_reader_help", __name__)

_TOPICS = [
{
    "id": "overview", "title": "🗜️ Overview",
    "content": """
<h3>GZ Reader — Windchill JMX Analyzer</h3>
<p>The GZ Reader opens and analyzes <code>.gz</code> compressed files and plain
decompressed files exported from PTC Windchill — entirely in your browser.
No file is uploaded to any server; all parsing happens locally on your machine.</p>

<h4>Supported file types</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">File</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">How to get it</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Notes</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;"><code>JMXData.gz</code></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Windchill JMX export</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Binary framing stripped automatically</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Any <code>.gz</code> file</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">XML, CSV, JSON, text</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Format auto-detected</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Plain <code>JMXData</code></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">7-Zip extracted</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Drop without extension</td></tr>
  </tbody>
</table>

<h4>Data privacy</h4>
<p>⚠️ <strong>All data stays on your laptop.</strong> Files are read using the browser
File API — no bytes are transmitted over the network. The server is only contacted for the
Split feature (writes chunk files to your local <code>outputs/</code> folder).</p>""",
},
{
    "id": "open_file", "title": "📂 Opening a File",
    "content": """
<h3>Opening a File</h3>
<h4>Option 1 — Click the drop zone</h4>
<p>Click the dashed box in the 📂 File panel to open a file picker. Select your
<code>JMXData.gz</code> or the plain extracted file.</p>

<h4>Option 2 — Drag and Drop</h4>
<p>Drag a file from Windows Explorer directly onto the drop zone in the sidebar.</p>

<h4>Reading progress</h4>
<p>A progress card appears in the content area showing:</p>
<ul>
  <li><strong>File size</strong> — compressed size on disk</li>
  <li><strong>Decompressed</strong> — bytes read so far</li>
  <li><strong>Lines</strong> — total lines processed</li>
  <li><strong>Records</strong> — structured rows extracted</li>
</ul>
<p>The table appears automatically when reading is complete. For the 460 MB JMXData.gz
(~3.7 GB decompressed) expect 2–4 minutes depending on hardware.</p>

<h4>Row cap</h4>
<p>Up to <strong>500,000 rows</strong> are kept in memory. For files producing more,
use the Split feature to work with smaller chunks.</p>""",
},
{
    "id": "table", "title": "📊 Table View",
    "content": """
<h3>Table View — JMX Records</h3>
<p>JMX binary files are parsed into a structured table with these columns:</p>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Column</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Example</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Description</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Timestamp</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">2025-11-10 01:49:55</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">When the MBean stat was recorded</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">User</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">wcadmin</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">User or principal at time of capture</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Component</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">wt.fv</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Top-level Windchill namespace</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">MBean / Cache</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">wt.fv.master.ReplicaFolder</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Full MBean object name</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Attribute</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">hameln_cache_Folder_45</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">MBean attribute key</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Value</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">REMOVE_UNFER_JOB_RUNNING</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Attribute value at capture time</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Raw Segment</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">(first 120 chars)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Original text segment for verification</td></tr>
  </tbody>
</table>
<h4>Virtual scroll</h4>
<p>Only ~60 DOM rows are rendered at a time regardless of dataset size — even 500,000 rows scroll smoothly. Click any column header to sort.</p>""",
},
{
    "id": "filter", "title": "🔍 Filter & Navigate",
    "content": """
<h3>Filter &amp; Navigate</h3>
<p>Open the 🔍 Filter panel in the sidebar. All filters apply instantly as you type.</p>

<h4>Timestamp range</h4>
<p>Enter partial or full timestamps in <strong>From</strong> / <strong>To</strong> fields.
The filter uses string comparison so <code>2025-11-10 01</code> matches everything in that hour.</p>
<pre style="background:#0f172a;color:#e2e8f0;padding:8px;border-radius:5px;font-size:11px;">
From: 2025-11-10 01:49:00
To:   2025-11-10 02:30:00</pre>

<h4>Component filter</h4>
<p>Enter a namespace prefix: <code>wt.fv</code>, <code>wt.util</code>, <code>com.ptc</code></p>

<h4>MBean / Cache</h4>
<p>Partial match on the full MBean name: <code>ReplicaFolder</code>, <code>WTException</code></p>

<h4>Value</h4>
<p>Filter by attribute value: <code>REMOVE_UNFER</code>, <code>true</code>, <code>0</code></p>

<h4>Jump to Timestamp</h4>
<p>Enter a timestamp and click <strong>⏩ Jump</strong>. The table scrolls instantly
to the nearest matching row using binary search — useful for jumping to a known incident time.</p>

<h4>Quick search (toolbar)</h4>
<p>The search box in the toolbar searches across all columns simultaneously.</p>""",
},
{
    "id": "split", "title": "✂️ Split Feature",
    "content": """
<h3>Split Large File</h3>
<p>The Split feature decompresses a <code>.gz</code> file and saves it as multiple readable
plain-text chunks in <code>outputs/</code>. This is needed when:</p>
<ul>
  <li>The file is too large to open in a text editor</li>
  <li>You need to share specific time ranges with PTC developers</li>
  <li>You want to run grep/search on specific portions</li>
</ul>

<h4>How to split</h4>
<ol>
  <li>Open the ✂️ Split panel</li>
  <li>Select chunk size (25 / 50 / 100 / 200 MB or custom)</li>
  <li>Click <strong>✂ Split &amp; Preview Chunks</strong></li>
  <li>Chunks appear as tabs as each one is written — click any tab to preview</li>
</ol>

<h4>Output location</h4>
<p>Chunks are saved to: <code>ops-platform/outputs/JMXData_part001.txt</code>, <code>…_part002.txt</code>, etc.</p>
<p>⚠️ Split requires the <code>.gz</code> file to sync to the server first (shown as
<em>⏳ Syncing…</em> in the File panel after opening). Wait for <em>✓ Ready to split</em> before clicking.</p>

<h4>Chunk preview</h4>
<p>Each chunk tab shows the first 80 KB of the file with a path header and ⬇ Download button.
Full chunks are available in <code>outputs/</code> and can be opened in any text editor.</p>""",
},
{
    "id": "summary", "title": "📄 Summary Report",
    "content": """
<h3>Downloadable Summary Report</h3>
<p>Click <strong>⬇ Download Summary</strong> (available after loading a JMX file) to generate
a structured text report saved to <code>outputs/gz_summary/</code> and downloaded to your browser.</p>

<h4>Report contents</h4>
<ul>
  <li>File metadata (name, size, record count, timestamp range)</li>
  <li>Top 20 MBean / Cache names by record count</li>
  <li>Top 10 Component namespaces</li>
  <li>Top 10 Attribute names</li>
  <li>Top 10 Users / principals</li>
  <li>All rows matching current filter (up to 10,000)</li>
</ul>

<h4>Privacy</h4>
<p>The report file is written to your local <code>outputs/gz_summary/</code> folder only.
It is never transmitted externally.</p>""",
},
{
    "id": "troubleshoot", "title": "🔧 Troubleshooting",
    "content": """
<h3>Troubleshooting</h3>

<h4>❌ "DecompressionStream not supported"</h4>
<p>Update Microsoft Edge to version 103 or later. The GZ Reader uses a built-in browser API
that requires a modern Edge/Chrome version.</p>

<h4>❌ "Maximum call stack size exceeded"</h4>
<p>This was caused by loading the full 3.7 GB file into memory at once. Fixed in v09 —
the file is now read in 4 MB streaming chunks. Ensure you are running the latest version.</p>

<h4>❌ Table shows 0 records after loading</h4>
<p>The file may be plain text (non-JMX). Switch to <strong>Raw Text</strong> view.
If it's a JMX file, check that it contains Windchill namespace strings
(<code>wt.queue</code>, <code>wt.fv</code>, <code>com.ptc</code>) in the first 64 KB.</p>

<h4>❌ Split button stays disabled</h4>
<p>Split requires the file to finish syncing to the local server. Wait for
<em>✓ Ready to split</em> in the File panel. For a 460 MB file this typically takes 30–60 seconds.</p>

<h4>❌ Sidebar is unresponsive / nothing clickable</h4>
<p>A previous version introduced a <code>&lt;label&gt;</code> element that blocked the sidebar.
Ensure you are running the latest version. Clear browser cache with Ctrl+Shift+R.</p>

<h4>❌ Reading takes very long</h4>
<p>Use the plain decompressed file instead of the <code>.gz</code>: extract with 7-Zip first,
then drop the <code>JMXData</code> file directly. Reading plain text is 3–5× faster than
in-browser decompression.</p>""",
},
]

@gz_reader_help_bp.route("/api/help/gz-reader")
def gz_reader_help_api():
    return jsonify({"module_title": "🗜️ GZ Reader — Help", "topics": _TOPICS})
