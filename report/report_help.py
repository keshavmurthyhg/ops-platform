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
# ---
{
    "id": "downloads",
    "title": "📥 Downloads & PPT Export",
    "content": (
        "<h3>Downloads</h3>"
        "<p>All hyperlinks (INC, Azure, PTC, References) render in <strong>black with no underline</strong> in Word, PDF, and PPT.</p>"
        "<ul>"
        "<li><strong>Word / PDF / ZIP</strong> - incident header, RCA sections, References table on a separate page</li>"
        "<li><strong>PPT</strong> - Slide 1: incident info + References table; Slides 2-4: Problem / Root Cause / Resolution + images</li>"
        "</ul>"
    ),
},

# ---
# 6. REFERENCES
# ---
{
    "id": "references",
    "title": "🔗 References",
    "content": (
        "<h3>References</h3>"
        "<p>Auto-extracted from Work Notes, Additional Comments, and Resolution Notes."
        " Finds Azure User Stories (<code>dev.azure.com/.../edit/{ID}</code>)"
        " and PTC Articles (<code>ptc.com/.../article/{ID}</code>).</p>"
        "<h4>Environment badges</h4>"
        "<p>Each reference shows a coloured environment <strong>dropdown</strong>"
        " (PROD / QA / TEST / UAT / DEV / STAGE / none)."
        " Changing it immediately updates the badge and flows into"
        " <strong>all downloaded documents automatically</strong> without needing Update Preview.</p>"
        "<h4>In documents</h4>"
        "<p>A REFERENCE / ENVIRONMENT / LINK &amp; CONTEXT table appears after Resolution"
        " in Word/PDF/ZIP, and at the bottom of Slide 1 in PPT.</p>"
    ),
},

# ---
# 7. DATA SOURCE
# ---
{
    "id": "data-source",
    "title": "📂 Data Source",
    "content": (
        "<h3>Data Source</h3>"
        "<p>Read from <code>data/Snow.xlsx</code>."
        " Column names are normalised automatically.</p>"
        "<h4>Key columns</h4>"
        "<ul style=\"font-size:12px;line-height:1.8;\">"
        "<li><code>Number</code>, <code>Short description</code>, <code>Description</code></li>"
        "<li><code>Opened by</code>, <code>Assigned to</code>, <code>Priority</code>, <code>Created</code>, <code>Resolved</code></li>"
        "<li><code>Resolution notes</code>, <code>Work notes</code>, <code>Additional comments</code> - RCA and Reference source</li>"
        "<li><code>Vendor ticket</code> - PTC case(s); comma-separated lists and alpha-prefixed IDs (e.g. <code>C1234567</code>) are supported.</li>"
        "</ul>"
    ),
},

# ---
# 8. READING THE LOGS
# ---
{
    "id": "logs",
    "title": "📋 Reading the Logs",
    "content": (
        "<h3>Logs</h3>"
        "<p>Written to <code>logs/report.log</code> (5 MB rotating, 5 backups).</p>"
        '<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">"'
        "PREVIEW REQUESTED: INC109720389\n"
        "References extracted: 4 azure, 1 ptc (total=5)\n"
        "# After env badge edit:\n"
        "References preserved from incoming data: 5\n"
        "DOWNLOAD REQUESTED: INC109720389  format=WORD\n"
        "WORD READY: INC109720389.docx  (1842 KB)\n"
        "PPT EXPORT: INC109720389\n"
        "PPTX SAVED: INC109720389_RCA_23JUN2026.pptx (5006 KB)"
        "</pre>"
        "<h4>Error patterns</h4>"
        "<ul style=\"font-size:12px;\">"
        "<li><code>Incident not found</code> - not in Snow.xlsx</li>"
        "<li><code>PPT export failed: name 'incident_data' is not defined</code> - deploy latest ppt_creator.py</li>"
        "<li><code>RCA fields: problem=False</code> - no notes; enter manually</li>"
        "<li><code>References preserved from incoming data: 0</code> - no references found in notes</li>"
        "</ul>"
    ),
},

# ---
# 9. TROUBLESHOOTING
# ---
{
    "id": "troubleshoot",
    "title": "🔧 Troubleshooting",
    "content": (
        "<h3>Troubleshooting</h3>"
        "<h4>❌ Environment badge change not in documents</h4>"
        "<p>Use the <strong>dropdown in the References panel</strong> (not the text editor)."
        " Changes propagate to all downloads without needing Update Preview."
        " Confirm in logs: <code>References preserved from incoming data</code> count &gt; 0.</p>"
        "<h4>❌ Multiple PTC cases not individually linked</h4>"
        "<p>Deploy latest <code>word_renderer.py</code>, <code>layout/header.py</code>, <code>ppt_creator.py</code>.</p>"
        "<h4>❌ Incident not found</h4>"
        "<p>INC not in <code>data/Snow.xlsx</code>. Refresh the export file.</p>"
        "<h4>❌ PPT export 500 error</h4>"
        "<p>Check logs for <code>PPT export failed</code>. Ensure <code>outputs/</code> is writable."
        " Deploy latest ppt_creator.py.</p>"
        "<h4>❌ RCA sections empty after Preview</h4>"
        "<p>Logs show <code>RCA fields: problem=False</code> - no notes; enter text manually.</p>"
        "<h4>❌ Images not in Update Preview</h4>"
        "<p>Click <strong>Add Images</strong> and confirm chip appears, then click Update Preview.</p>"
        "<h4>❌ Help button does nothing</h4>"
        "<p>Register <code>report_help_bp</code> in <code>app.py</code>.</p>"
    ),
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
