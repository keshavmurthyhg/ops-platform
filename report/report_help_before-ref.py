# =============================================================================
#  RCA REPORT GENERATOR — HELP CONTENT API
#  report/report_help.py
#
#  Serves help topics for the RCA Report Generator module.
#  common.js toggleHelpSystemModal() opens #helpSystemModal and calls
#  loadModuleHelpData(), which fetches GET /api/help/report.
#
#  Register in app.py:
#      from report.report_help import report_help_bp
#      app.register_blueprint(report_help_bp)
# =============================================================================

from flask import Blueprint, jsonify

report_help_bp = Blueprint("report_help", __name__)


_REPORT_HELP_TOPICS = [

# ─────────────────────────────────────────────────────────────────────────────
# 1. OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "overview",
    "title": "📄 Overview",
    "content": """
<h3>RCA Report Generator</h3>
<p>The RCA Report Generator loads a ServiceNow incident by number, intelligently builds
Problem Statement, Root Cause and Resolution sections from the incident notes, lets you
edit them with a rich-text editor, attach images, preview the result inline, and
download as Word, PDF, ZIP or PowerPoint.</p>

<h4>Processing pipeline</h4>
<ol>
  <li><strong>Fetch</strong> — incident data is loaded from <code>data/Snow.xlsx</code>
      (the ServiceNow export).</li>
  <li><strong>RCA build</strong> — the <code>rca_service</code> classifies sentences from
      Work Notes and Resolution Notes into the three sections automatically.</li>
  <li><strong>Preview</strong> — the incident header table and RCA sections are rendered
      inline. The Editable RCA panel is pre-filled with the generated text.</li>
  <li><strong>Edit</strong> — use the rich-text editor to refine each section and attach
      supporting images via the 📎 Add Images button.</li>
  <li><strong>Update Preview</strong> — click ↻ to refresh the preview panel with your
      edits and attached images side-by-side.</li>
  <li><strong>Download</strong> — Word / PDF / ZIP / PPT from the ⬇️ Downloads dock.</li>
</ol>

<h4>RCA section auto-classification</h4>
<ul>
  <li><strong>Problem Statement</strong> — drawn from Short Description and Description;
      hedging language ("I believe", "maybe") stripped automatically.</li>
  <li><strong>Root Cause</strong> — technical cause extracted from Work Notes; sentences
      about delegates, missing permissions, config changes are prioritised.</li>
  <li><strong>Resolution</strong> — steps taken or required; validation results included;
      if unresolved, escalation/bug tracking note is appended automatically.</li>
</ul>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 2. HOW TO USE
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "procedure",
    "title": "🚀 How to Use",
    "content": """
<h3>Step-by-Step Procedure</h3>

<h4>Step 1 — Enter the incident number</h4>
<p>Type the incident number (e.g. <code>INC109720389</code>) into the search bar in the
top toolbar and click <strong>Preview</strong>.</p>

<h4>Step 2 — Review the preview and pre-filled text</h4>
<p>The <strong>Preview</strong> card shows the incident header table (incident number,
priority, dates, assignee, etc.) and the three RCA sections. The
<strong>Editable RCA</strong> panel below is pre-filled with the auto-generated text.</p>

<h4>Step 3 — Edit each RCA section</h4>
<p>Each section (🔴 Problem / 🟡 Root Cause / 🟢 Resolution) is a <strong>collapsible
zone</strong>. Click the header to expand it, then:</p>
<ul>
  <li>Edit the pre-filled text using the rich-text toolbar (bold, colour, lists, case…)</li>
  <li>Use quick-insert buttons (• Bullet, [IMPACT], [ACTION]…) to add placeholders at the cursor</li>
  <li>Click <strong>📎 Add Images</strong> to attach supporting screenshots; remove them
      with the × chip</li>
  <li>Click <strong>✕ Clear</strong> to wipe that section's text</li>
</ul>
<p>The sidebar 🗂️ RCA dock shows a live character count per section.</p>

<h4>Step 4 — ↻ Update Preview</h4>
<p>Click <strong>↻ Update Preview</strong> (toolbar bottom or sidebar RCA dock) to
regenerate the Preview card with your edited text and attached images. Images appear
side-by-side in the preview table.</p>

<h4>Step 5 — Download</h4>
<p>Open the ⬇️ <strong>Downloads</strong> dock and click:</p>
<ul>
  <li><strong>⬇️ Word</strong> — <code>.docx</code> with incident header + RCA sections + images</li>
  <li><strong>⬇️ PDF</strong> — same content as PDF</li>
  <li><strong>📦 ZIP</strong> — both Word and PDF together</li>
  <li><strong>📊 Export as PPT</strong> — landscape PowerPoint with incident info slide
      and one RCA slide per section (text + images on same slide)</li>
</ul>

<h4>Clear Workspace</h4>
<p>Click <strong>Clear Workspace</strong> in the sidebar toolbar to reset everything —
incident number, preview, all RCA text, and uploaded images.</p>

<h4>Apply Filters</h4>
<p>Click <strong>Apply Filters</strong> in the sidebar toolbar to re-run Update Preview
with the current text and images. Equivalent to clicking ↻ Update Preview.</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 3. RICH TEXT EDITOR
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "rich_text",
    "title": "✎ Rich Text Editor",
    "content": """
<h3>Rich Text Editor</h3>
<p>Each RCA section has a Word-style floating toolbar above a
<code>contenteditable</code> text area.</p>

<h4>Toolbar reference</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Button</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Action</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">11 ▾</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Font size 8–36 pt on selected text</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;"><b>B</b> / <i>I</i> / <u>U</u></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Bold / Italic / Underline</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;"><b>Aa</b></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Case cycle: ALL CAPS → Title Case → Sentence case → lowercase (repeats)</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">A (colour)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Text colour — 40 preset swatches + custom colour picker</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">▐ (highlight)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Background highlight colour</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">☰</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Bullet list (• • •)</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">①</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Numbered list (1. 2. 3.)</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;"><i>a.</i></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Alphabet list (a. b. c.) — click again to toggle back to numbered</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">→ / ←</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Indent / outdent list level</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">✕ Reset</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Remove all formatting from selected text</td></tr>
  </tbody>
</table>

<h4>Case cycling (Aa button)</h4>
<p>Select text, then click <b>Aa</b> repeatedly — the app detects the current case and
advances to the next:</p>
<ol style="font-size:12px;margin:4px 0 4px 1.2em;line-height:1.8;">
  <li>→ <b>ALL CAPS</b></li>
  <li>→ <b>Title Case</b></li>
  <li>→ <b>Sentence case</b></li>
  <li>→ <b>lowercase</b></li>
  <li>→ ALL CAPS again (repeats)</li>
</ol>

<h4>Quick-insert row</h4>
<p>Below each editor is a row of one-click placeholder buttons:
<code>• Bullet</code>, <code>[IMPACT]</code>, <code>[DATE/TIME]</code>, etc.
They insert text at the cursor position.</p>

<h4>Auto-correct</h4>
<p>Common typos are corrected automatically on spacebar: <code>teh→the</code>,
<code>incidnet→incident</code>, <code>recieve→receive</code>, and 20+ more.</p>

<h4>Collapsible sections</h4>
<p>All three zones collapse by default. Click a section header to expand it. The header
always shows the current character count while collapsed. Click <strong>⊞ Expand
All</strong> to open all three at once.</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 4. IMAGES
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "images",
    "title": "🖼 Adding Images",
    "content": """
<h3>Adding Images to RCA Sections</h3>
<p>Each expanded RCA zone has a <strong>📎 Add Images</strong> button. Click it to select
one or more image files (PNG, JPG, etc.). Selected files appear as chips below the button —
click <strong>×</strong> to remove one.</p>

<h4>Previewing images</h4>
<p>Click <strong>↻ Update Preview</strong> to regenerate the preview panel with your
images embedded. Multiple images per section are arranged <strong>side-by-side</strong>
(not stacked in a column) in the preview table.</p>

<h4>Images in downloaded documents</h4>
<p>The <strong>⚙ Options</strong> dock lets you choose:</p>
<ul>
  <li><strong>All uploaded images</strong> — images appear inline in each RCA section
      in Word / PDF / ZIP downloads</li>
  <li><strong>Text only</strong> — no images in the output document</li>
</ul>
<p>The PPT export always includes the uploaded images (one slide per section,
images in horizontal strips).</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 5. DOWNLOADS & PPT EXPORT
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "downloads",
    "title": "📥 Downloads & PPT Export",
    "content": """
<h3>Downloads &amp; PPT Export</h3>
<p>Open the ⬇️ <strong>Downloads</strong> dock in the sidebar after loading a preview.</p>

<h4>Report formats</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Button</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Output</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Filename</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">⬇️ Word</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Formatted .docx</td><td style="padding:5px 8px;border:1px solid #e2e8f0;"><code>INC109720389.docx</code></td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">⬇️ PDF</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Formatted .pdf</td><td style="padding:5px 8px;border:1px solid #e2e8f0;"><code>INC109720389.pdf</code></td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">📦 ZIP</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Word + PDF together</td><td style="padding:5px 8px;border:1px solid #e2e8f0;"><code>INC109720389.zip</code></td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">📊 Export as PPT</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Landscape PowerPoint</td><td style="padding:5px 8px;border:1px solid #e2e8f0;"><code>INC109720389_RCA_{DATE}.pptx</code></td></tr>
  </tbody>
</table>

<h4>PPT slide structure</h4>
<ol style="font-size:12px;margin:6px 0 6px 1.2em;line-height:1.8;">
  <li><strong>Slide 1 — Incident Info:</strong> 4-column metadata table (INC / Created By /
      Azure Bug / Created Date / PTC Case / Assigned To / Priority / Resolved Date),
      hyperlinks on INC/Azure/PTC, Short Description + Description table, RCA summary</li>
  <li><strong>Slide 2 — Problem Statement:</strong> your text + attached images side-by-side</li>
  <li><strong>Slide 3 — Root Cause:</strong> your text + images</li>
  <li><strong>Slide 4 — Resolution:</strong> your text + images</li>
</ol>
<p>The PPT downloads automatically — no separate "Download" click needed.</p>

<h4>Images in report option (⚙ Options dock)</h4>
<p>Select <strong>All uploaded images</strong> or <strong>Text only</strong> before
downloading Word / PDF / ZIP. The PPT always includes all images.</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 6. DATA SOURCE
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "data-source",
    "title": "📂 Data Source",
    "content": """
<h3>Data Source</h3>
<p>All incident data is read from <code>data/Snow.xlsx</code> — the ServiceNow export.</p>

<h4>Required columns</h4>
<p>Column names are normalised automatically (case and whitespace insensitive):</p>
<ul style="font-size:12px;line-height:1.8;">
  <li><code>Number</code> — incident number (INC…)</li>
  <li><code>Short description</code> — one-line summary</li>
  <li><code>Description</code> — full incident description</li>
  <li><code>Opened by</code> / <code>Assigned to</code> — personnel</li>
  <li><code>Priority</code> — P1–P4</li>
  <li><code>Created</code> / <code>Resolved</code> — dates</li>
  <li><code>Resolution notes</code> / <code>Work notes</code> — source for RCA classification</li>
  <li><code>Additional comments</code></li>
  <li><code>Azure bug</code> / <code>PTC case</code> — external ticket references</li>
</ul>

<h4>Missing or empty fields</h4>
<p>Any field not present in the export is shown as <code>-</code> in the report.
The RCA auto-classification falls back gracefully when notes are absent.</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 7. READING THE LOGS
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "logs",
    "title": "📋 Reading the Logs",
    "content": """
<h3>Reading the Logs</h3>
<p>All activity is written to <code>logs/report.log</code> (rotating, 5 MB × 5 backups).</p>

<h4>Preview load</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
============================================================
PREVIEW REQUESTED: INC109720389
  RCA fields: problem=True  analysis=True  resolution=True
  Priority: Priority 4  Assigned to: Keshavamurthy Hg
PREVIEW GENERATED: INC109720389
============================================================</pre>

<h4>Update Preview</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
UPDATE PREVIEW: INC109720389
  problem text     : 338 chars
  analysis text    : 99 chars
  resolution text  : 709 chars
  problem_images   : 1
  root_images      : 2
  resolution_images: 4</pre>

<h4>Download</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
------------------------------------------------------------
DOWNLOAD REQUESTED: INC109720389  format=WORD  images_mode=all
  Images: problem=1  root=2  resolution=4  (total=7, mode=all)
WORD READY: INC109720389.docx  (1842 KB)
------------------------------------------------------------</pre>

<h4>PPT Export</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
============================================================
PPT EXPORT: INC109720389
  problem    : 338 chars
  root_cause : 99 chars
  resolution : 709 chars
  Images: problem=1 root=2 resolution=4
Building incident slide: INC109720389
Incident slide built
Building problem — 338 chars, 1 images
  img 1/1 placed: screenshot_1.png
Building rootcause — 99 chars, 2 images
  img 1/2 placed: screenshot_2.png
  img 2/2 placed: screenshot_3.png
Building resolution — 709 chars, 4 images
  img 1/3 placed: screenshot_4.png
  ...
PPTX SAVED: INC109720389_RCA_23JUN2026.pptx (5006 KB)
============================================================</pre>

<h4>Error patterns to look for</h4>
<ul style="font-size:12px;line-height:1.8;">
  <li><code>Incident not found</code> — the INC number isn't in <code>data/Snow.xlsx</code></li>
  <li><code>UPDATE PREVIEW FAILED</code> — check if image paths are accessible</li>
  <li><code>PPT export failed</code> — likely a missing image file; check the path in the error</li>
  <li><code>RCA fields: problem=False analysis=False</code> — the incident has no notes;
      text will need to be entered manually in the editor</li>
</ul>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 8. TROUBLESHOOTING
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "troubleshoot",
    "title": "🔧 Troubleshooting",
    "content": """
<h3>Troubleshooting</h3>

<h4>❌ "Incident not found"</h4>
<p>The INC number is not in <code>data/Snow.xlsx</code>. Verify the number and ensure
the export file is up to date. The lookup is case-insensitive.</p>

<h4>❌ RCA sections are empty after Preview</h4>
<p>Check <code>logs/report.log</code> for <code>RCA fields: problem=False analysis=False</code>.
This means the incident record has no Work Notes or Resolution Notes to classify.
Type the analysis manually in the editor.</p>

<h4>❌ Images not appearing in Update Preview</h4>
<p>Ensure you clicked <strong>📎 Add Images</strong> and see the filename chip appear before
clicking ↻ Update Preview. Only files listed in the chips are sent to the server.</p>

<h4>❌ "Text only" option still includes images in Word</h4>
<p>The Images in Report setting is read at download time. Select <strong>Text only</strong>
in the ⚙ Options dock, then click the download button again.</p>

<h4>❌ PPT export fails or produces an empty file</h4>
<p>Check <code>logs/report.log</code> for <code>PPT export failed</code>. Common causes:</p>
<ul>
  <li>An uploaded image path was deleted before export — click 📎 Add Images again</li>
  <li>The <code>outputs/</code> folder doesn't exist or isn't writable on the server</li>
</ul>

<h4>❌ Preview images are stacked in a single column</h4>
<p>This is fixed by the <code>_reflowPreviewImages()</code> JS function which runs after
every Update Preview. If you still see stacked images, hard-refresh the page
(Ctrl+Shift+R) to load the latest <code>report.js</code>.</p>

<h4>❌ Help button (?) does nothing</h4>
<p>Ensure <code>report_help_bp</code> is registered in <code>app.py</code>:
<code>from report.report_help import report_help_bp</code> and
<code>app.register_blueprint(report_help_bp)</code>.</p>""",
},

]


@report_help_bp.route("/api/help/report")
def report_help_api():
    """
    Return help topics for the RCA Report Generator.
    Called by common.js loadModuleHelpData() when ? is clicked.
    """
    return jsonify({
        "module_title": "RCA Report Generator — Help",
        "topics":       _REPORT_HELP_TOPICS,
    })
