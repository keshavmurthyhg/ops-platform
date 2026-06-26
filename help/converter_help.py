from flask import Blueprint, jsonify
converter_help_bp = Blueprint("converter_help", __name__)

_TOPICS = [

# ─────────────────────────────────────────────────────────────────────────────
# 1. OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "overview", "title": "📄 Overview",
    "content": """
<h3>Converter — PPT to DOC</h3>
<p>The Converter transforms a PowerPoint incident walkthrough into a structured Word document
(and optionally PDF), enriched with live ServiceNow data. It also provides a full
<strong>RCA editor</strong> — write structured analysis, assign slide screenshots to each
section, preview the result, then generate a report or export back to PowerPoint.</p>

<h4>Processing pipeline</h4>
<ol>
  <li><strong>Upload &amp; Incident Detection</strong> — the INC number is read from the filename
      and/or slide 1, then looked up in ServiceNow.</li>
  <li><strong>Slide Conversion (automatic)</strong> — slides are filtered, background-stripped,
      and rendered to PNG immediately after Preview completes. No manual step required.</li>
  <li><strong>RCA Pre-fill</strong> — Problem Statement, Root Cause and Resolution text from
      ServiceNow are loaded into the editor automatically.</li>
  <li><strong>RCA Assignment</strong> — drag slides to sections, edit text with the rich-text
      toolbar, then click ↻ Update Preview to see the result inline.</li>
  <li><strong>Generate</strong> — produce Word / PDF (RCA report) or export to PPT.</li>
</ol>

<h4>What gets kept vs stripped from slides</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Element</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Location</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Result</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Screenshots / images</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Slide</td><td style="padding:5px 8px;border:1px solid #e2e8f0;color:#166534;">✓ Kept</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Arrows, connectors, callouts</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Slide</td><td style="padding:5px 8px;border:1px solid #e2e8f0;color:#166534;">✓ Kept</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Blue theme swooshes / gradients</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Master / Layout</td><td style="padding:5px 8px;border:1px solid #e2e8f0;color:#991b1b;">✗ Stripped</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Theme background (bgRef)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">All levels</td><td style="padding:5px 8px;border:1px solid #e2e8f0;color:#991b1b;">✗ → White</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Title / divider slides</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Whole slide</td><td style="padding:5px 8px;border:1px solid #e2e8f0;color:#7c3aed;">⊘ Skipped (configurable)</td></tr>
  </tbody>
</table>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 2. HOW TO USE
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "procedure", "title": "🚀 How to Use",
    "content": """
<h3>Step-by-Step Procedure</h3>

<h4>Step 1 — Upload</h4>
<p>Click <strong>Choose File</strong> and select a <code>.ppt</code> or <code>.pptx</code>.
Include the INC number in the filename: <code>INC109682818-walkthrough.pptx</code>.</p>

<h4>Step 2 — Preview</h4>
<p>Click <strong>Preview</strong>. The app simultaneously:</p>
<ul>
  <li>Fetches incident data from ServiceNow and renders the Incident Preview panel</li>
  <li>Pre-fills RCA editor text (Problem Statement, Root Cause, Resolution) from ServiceNow</li>
  <li>Converts and renders all slides in the background — the grid and tray populate automatically</li>
</ul>
<p>A green <strong>✓ Pre-filled</strong> badge appears in the 🗂️ RCA sidebar when text was found.</p>

<h4>Step 3 — Assign slides &amp; edit text (RCA Assignment panel)</h4>
<ul>
  <li>Drag thumbnails from the <strong>Slide Tray</strong> onto a section, or click to select
      then use the quick-assign bar (🔴 Problem / 🟡 Root Cause / 🟢 Resolution)</li>
  <li>Edit the pre-filled text using the rich-text toolbar (bold, colour, lists, case cycle…)</li>
  <li>Section headers show live image count and character count even when collapsed</li>
</ul>

<h4>Step 4 — ↻ Update Preview</h4>
<p>Click <strong>↻ Update Preview</strong> in the toolbar after assigning images or editing text.
The Incident Preview panel refreshes to show your RCA text and the assigned slide images
arranged side-by-side — exactly like the Report module. Your assignments are never affected
by this button.</p>

<h4>Step 5 — Generate</h4>
<ul>
  <li><strong>📝 RCA Report</strong> (🗂️ sidebar) — Word/PDF with RCA sections + images. The
      <em>Images in Report</em> option (⚙ Options) controls which remaining slides appear at
      the end: all / unassigned only / none.</li>
  <li><strong>📊 Export as PPT</strong> (⬇️ Download dock) — builds a new landscape PowerPoint
      from the RCA data and auto-downloads it.</li>
</ul>

<h4>Step 6 — Download</h4>
<p>The ⬇️ Download dock shows buttons for Word, PDF, and Both once a report is generated.
Slide images can be downloaded individually (⬇ on each card), as selected (ZIP), or all (ZIP).</p>

<h4>Apply Filters</h4>
<p><strong>Apply Filters</strong> in the sidebar toolbar re-renders slides with current Options
settings (DPI, skip settings) without resetting your RCA text or assignments.</p>

<h4>Clear Workspace</h4>
<p><strong>Clear Workspace</strong> resets everything — uploaded file, preview, slide grid, RCA
assignments, text, and the server-side image cache. Use before starting a new incident.</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 3. RCA EDITOR
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "rca", "title": "🗂 RCA Editor",
    "content": """
<h3>RCA Editor</h3>

<h4>Auto Pre-fill from ServiceNow</h4>
<p>Preview reads Problem Statement, Root Cause and Resolution from the incident record and
loads them into the editor. A <strong>✓ Pre-filled</strong> badge confirms this.
Click <strong>✕</strong> next to the badge to clear all pre-filled text, or use the
<strong>✕ Clear</strong> button inside each section to clear just that section.</p>

<h4>Collapsible sections</h4>
<p>All three zones (🔴 🟡 🟢) are collapsed by default. Click a section header to expand it.
The header always shows image count and character count while collapsed.
Click <strong>⊞ Expand All</strong> to open all at once. Dropping a slide or using quick-assign
automatically expands the target section.</p>

<h4>Slide Tray</h4>
<p>Converted slides appear in a scrollable tray. Each thumbnail can be:</p>
<ul>
  <li><strong>Dragged</strong> directly onto a section drop zone</li>
  <li><strong>Clicked</strong> to select (blue ring) → the quick-assign bar appears</li>
</ul>
<p>Tray borders reflect zone colour(s) the slide is assigned to. Slides can appear in multiple zones.</p>

<h4>Sidebar status rows</h4>
<p>The 🗂️ dock shows a row for each section with a coloured dot, image count chip, and chevron.
Click any row to expand/collapse that section without scrolling.</p>

<h4>Generating the RCA Report (Word/PDF)</h4>
<p>Click <strong>📝 RCA Report</strong> when at least one image is assigned.
The report uses the same Word renderer as the Report and Bulk modules:</p>
<ul>
  <li>Portrait A4, standard incident header table, description table</li>
  <li>RCA sections with colour-coded headings, your text, and inline section images</li>
  <li>A <em>PPT Slides</em> section at the end (controlled by Images in Report option)</li>
</ul>
<p>Filename: <code>{original_name}_RCA_{DDMMMYYYY}.docx</code></p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 4. OPTIONS
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "options", "title": "⚙ Options",
    "content": """
<h3>Options Dock</h3>
<p>Open with the <strong>⚙</strong> dock icon. Changes take effect when you click
<strong>Apply Filters</strong> (sidebar) or <strong>Preview</strong>.</p>

<h4>Slide Processing</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Option</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Default</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Effect</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Skip Titles</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">On</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Removes slide 1 and title-only slides</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Skip Dividers</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">On</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Removes low-content transition slides (≤10 words, no images)</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Slide DPI</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">200</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">150 = fast/small · 200 = balanced · 300 = print quality</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Output Format</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Word</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Word / PDF / Both — synced with ⬇️ Download dock</td></tr>
  </tbody>
</table>

<h4>Images in Report</h4>
<p>Controls which slide images appear in the <em>PPT Slides</em> section at the end of the
RCA document:</p>
<ul>
  <li><strong>All converted slides</strong> — every rendered slide is appended</li>
  <li><strong>Unassigned slides only</strong> — slides not in any RCA zone (zone slides are
      already inline in their sections)</li>
  <li><strong>RCA sections only</strong> — no PPT Slides section; images appear only inside
      their RCA sections</li>
</ul>

<h4>Apply Filters vs Preview</h4>
<p><strong>Apply Filters</strong> re-renders slides only (preserves all RCA state).
<strong>Preview</strong> re-fetches incident data from ServiceNow and re-renders everything.</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 5. IMAGE VIEWER (LIGHTBOX)
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "lightbox", "title": "🖼 Image Viewer",
    "content": """
<h3>Slide Image Viewer</h3>
<p>Click any slide thumbnail in the <strong>Converted PPT Slides Preview</strong> grid to
open it full-screen. Images assigned to RCA zones are also clickable in the lightbox.</p>

<h4>Navigation</h4>
<ul>
  <li><strong>‹ Prev / Next ›</strong> buttons or <kbd>←</kbd> <kbd>→</kbd> arrow keys</li>
  <li><strong>Escape</strong> or clicking the dark backdrop to close</li>
</ul>

<h4>Zoom</h4>
<ul>
  <li><strong>🔍− / 🔍+</strong> buttons or <kbd>−</kbd> / <kbd>+</kbd> keyboard keys</li>
  <li><strong>⊡ Fit</strong> — resets to original size</li>
</ul>

<h4>Add to RCA from lightbox</h4>
<p>The <strong>Add to RCA</strong> bar inside the viewer has three zone buttons (🔴 🟡 🟢).
Click one to assign the current slide to that section without closing the lightbox.
The button gets an outline when that slide is already in the zone.</p>

<h4>Download from lightbox</h4>
<p>Click <strong>⬇️</strong> (top-right) to download the current image:<br>
<code>{INCIDENT}_image-{NNN}_{DDMMMYYYY}.png</code></p>

<h4>Bulk download from grid</h4>
<ul>
  <li>Click <strong>☐</strong> on a card to select it (blue outline). <strong>☑ All</strong> selects all.</li>
  <li><strong>⬇️ All</strong> — ZIP of every converted slide</li>
  <li><strong>⬇️ Selected</strong> — ZIP of checked slides only</li>
  <li><strong>⬇</strong> on each card — single image download</li>
</ul>
<p>ZIP name: <code>{INCIDENT}_slides_{DDMMMYYYY}.zip</code></p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 6. RICH TEXT EDITOR
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "rich_text", "title": "✎ Rich Text Editor",
    "content": """
<h3>Rich Text Editor</h3>
<p>Each RCA zone has a Word-style toolbar above a <code>contenteditable</code> area.</p>

<h4>Toolbar reference</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Button</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">Action</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">11 ▾</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Font size 8–36 pt</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;"><b>B</b> / <i>I</i> / <u>U</u></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Bold / Italic / Underline</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;"><b>Aa</b></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Case cycle: ALL CAPS → Title Case → Sentence case → lowercase (repeats)</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">A (colour)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Text colour — 40 preset swatches + custom picker</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">▐ (highlight)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Background highlight colour</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">☰</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Bullet list</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">①</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Numbered list (1. 2. 3.)</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;"><i>a.</i></td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Alphabet list (a. b. c.) — click again to toggle back to numbered</td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">→ / ←</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Indent / outdent (creates nested sub-lists)</td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">✕ Reset</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Remove all formatting from selected text</td></tr>
  </tbody>
</table>

<h4>Case cycle detail (Aa)</h4>
<p>Select text first, then click <b>Aa</b> repeatedly. The app detects current case and advances:</p>
<ol style="font-size:12px;margin:4px 0 4px 1.2em;line-height:1.8;">
  <li>→ <b>ALL CAPS</b></li>
  <li>→ <b>Title Case</b></li>
  <li>→ <b>Sentence case</b></li>
  <li>→ <b>lowercase</b></li>
  <li>→ ALL CAPS again (cycles)</li>
</ol>

<h4>Auto-correct</h4>
<p>Common typos are fixed automatically on spacebar: <code>teh→the</code>, <code>incidnet→incident</code>,
<code>recieve→receive</code>, and 25+ more.</p>

<h4>Quick-insert row</h4>
<p>Below each editor is a row of placeholder buttons: <code>• Bullet</code>,
<code>[IMPACT]</code>, <code>[DATE/TIME]</code>, etc. They insert at the cursor position.</p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 7. PPT EXPORT
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "ppt_export", "title": "📊 PPT Export",
    "content": """
<h3>Export as PPT</h3>
<p>Click <strong>📊 Export as PPT</strong> in the ⬇️ Download dock to build a clean landscape
PowerPoint from your RCA data. The file downloads automatically — no separate download step.</p>

<h4>Slide structure</h4>
<ol>
  <li><strong>Slide 1 — Incident Info</strong>
    <ul>
      <li>Dark title band with INC number</li>
      <li>4-column metadata table (Incident / Created By / Azure Bug / Created Date / PTC Case /
          Assigned To / Priority / Resolved Date) — <strong>same proportions as Word/PDF</strong></li>
      <li>Incident, Azure Bug and PTC Case numbers are <strong>clickable hyperlinks</strong></li>
      <li>Dates formatted as <code>DD-MMM-YYYY</code> (e.g. 22-Jan-2026)</li>
      <li>Short Description / Description 2-column table</li>
      <li>RCA summary table (Problem / Root Cause / Resolution with coloured left stripe)</li>
    </ul>
  </li>
  <li><strong>Slides 2–4 — Problem / Root Cause / Resolution</strong>
    <ul>
      <li>Thin coloured accent bar at top (red / amber / green)</li>
      <li>Light grey heading band with section title</li>
      <li>Your RCA text in a soft body area</li>
      <li><strong>All assigned images on the same slide</strong> in a horizontal strip (up to 3 per row)</li>
      <li>Overflow slides created if more than 3 images are assigned</li>
    </ul>
  </li>
</ol>

<h4>Hyperlink URLs</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;">
  <thead><tr style="background:#e0f2fe;">
    <th style="padding:5px 8px;text-align:left;border:1px solid #bae6fd;">Field</th>
    <th style="padding:5px 8px;border:1px solid #bae6fd;">URL Pattern</th>
  </tr></thead>
  <tbody>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">Incident (INC…)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">ServiceNow — <code>volvoitsm.service-now.com/…number=INC…</code></td></tr>
    <tr style="background:#f8fafc;"><td style="padding:5px 8px;border:1px solid #e2e8f0;">Azure Bug (ID)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">Azure DevOps — <code>dev.azure.com/VolvoCarsGroup/VCE/_workitems/edit/{ID}</code></td></tr>
    <tr><td style="padding:5px 8px;border:1px solid #e2e8f0;">PTC Case (ID)</td><td style="padding:5px 8px;border:1px solid #e2e8f0;">PTC Support — <code>support.ptc.com/…solution.jsp?n={ID}</code></td></tr>
  </tbody>
</table>
<p style="font-size:11px;color:#64748b;margin-top:6px;">
  To update base URLs, edit <code>BASE_AZURE_URL</code> and <code>BASE_PTC_URL</code>
  in <code>converter/module/ppt_creator.py</code>.
</p>

<h4>Output filename</h4>
<p><code>{original_filename}_RCA_{DDMMMYYYY}.pptx</code><br>
e.g. <code>INC109682818-walkthrough_RCA_22JUN2026.pptx</code></p>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 8. READING THE LOGS
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "logs", "title": "📋 Reading the Logs",
    "content": """
<h3>Reading the Logs</h3>
<p>Log files: <code>logs/converter.log</code> · <code>logs/ppt_slide_renderer.log</code> ·
<code>logs/ppt_creator.log</code> · <code>logs/doc_to_pdf.log</code></p>

<h4>Preview + Auto-conversion</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
------------------------------------------------------------
USER PREFERENCES — PREVIEW
  Skip title slides : true
  Skip dividers     : true
  Slide DPI         : 200
  Output format     : word
  Images in doc     : all
------------------------------------------------------------
Incident: INC109682818
RCA PREFILL: problem=True  rootcause=True  resolution=True
PREVIEW COMPLETE: 7 slide(s) — auto-conversion will follow
PREVIEW_IMAGE_STORE cleared and refreshed: 7 entries</pre>
<p>The timestamp-prefixed filenames (e.g. <code>1750000000_slide_1.png</code>) guarantee
the browser never serves a cached image from a previous session.</p>

<h4>Update Preview</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
UPDATE PREVIEW: INC109682818
  problem    : 338 chars
  analysis   : 99 chars
  resolution : 125 chars
  problem_images   : 1
  root_images      : 2
  resolution_images: 4
UPDATE PREVIEW complete: INC109682818</pre>

<h4>Cache clear</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
CACHE CLEARED: 7 store entries, 7 files removed</pre>
<p>Triggered automatically by Clear Workspace. Ensures no stale images from a previous
incident appear in the next conversion.</p>

<h4>RCA report generation</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
================================================================
RCA DOCUMENT GENERATION
  problem      : 1 img, 338 chars
  rootcause    : 2 img, 99 chars
  resolution   : 4 img, 125 chars
  images_mode  : all
  format       : WORD
================================================================
Image paths resolved: problem=1 root=2 resolution=4
ppt_data_arg: outputs/INC109682818-…pptx (mode=all, remaining=7)
RCA DOCX: INC109682818-…_RCA_22JUN2026.docx (1842 KB)</pre>

<h4>PPT export</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
============================================================
RCA PPTX CREATION
  Incident : INC109682818
  Output   : outputs/INC109682818-…_RCA_22JUN2026.pptx
  Data keys: ['analysis', 'assigned_to', 'azure_bug', 'created_by', ...]
  problem      : 1 img, 338 chars
  rootcause    : 2 img, 99 chars
  resolution   : 4 img, 125 chars
Building incident slide: INC109682818
Incident slide built
Building problem — 338 chars, 1 images
  img 1/1 placed: 1750000000_slide_1.png
Building rootcause — 99 chars, 2 images
  img 1/2 placed: 1750000000_slide_6.png
  img 2/2 placed: 1750000000_slide_7.png
Building resolution — 125 chars, 4 images
  img 1/3 placed: 1750000000_slide_2.png
  ...
PPTX SAVED: outputs/INC109682818-…_RCA_22JUN2026.pptx (5006 KB)
============================================================</pre>

<h4>Slide filter decisions</h4>
<pre style="background:#0f172a;color:#e2e8f0;padding:10px;border-radius:6px;font-size:11px;overflow-x:auto;line-height:1.6;">
Slide 1 — SKIP (cover/title slide)
Slide 2 — KEEP | shapes=12  pics=2  text_boxes=4  connectors=3
Slide 7 — SKIP (divider: 4 word(s), no picture)
Slide filter result: 7 kept, 2 skipped</pre>""",
},


# ─────────────────────────────────────────────────────────────────────────────
# 9. TROUBLESHOOTING
# ─────────────────────────────────────────────────────────────────────────────
{
    "id": "troubleshoot", "title": "🔧 Troubleshooting",
    "content": """
<h3>Troubleshooting</h3>

<h4>❌ "Valid incident not found"</h4>
<p>Include the INC number in the filename: <code>INC109682818-description.pptx</code></p>

<h4>❌ RCA text not pre-filled / wrong text</h4>
<p>Check <code>converter.log</code> for <code>RCA PREFILL:</code>. If all show <code>False</code>,
the fields aren't populated in ServiceNow. You can type manually. If wrong text appears,
click <strong>✕</strong> next to the Pre-filled badge and type your own.</p>

<h4>❌ Stale images from a previous incident appearing in tray</h4>
<p>Always click <strong>Clear Workspace</strong> before loading a new PPT. This calls
<code>/converter/clear-cache</code> on the server, wiping the image store and disk files.
Each new conversion also generates timestamp-prefixed filenames so the browser can never
serve cached images from a previous session.</p>

<h4>❌ PPT export shows "PPT creation failed" but file is in outputs/</h4>
<p>The file saved successfully — the error was a browser navigation conflict.
The download now uses a hidden anchor element to avoid this. If you see the old error message,
refresh the page (Ctrl+R) and try again; the fix is in the latest <code>converter.js</code>.</p>

<h4>❌ Azure / PTC hyperlinks open the wrong URL</h4>
<p>Update <code>BASE_AZURE_URL</code> and <code>BASE_PTC_URL</code> at the top of
<code>converter/module/ppt_creator.py</code> to match your organisation's actual URLs.</p>

<h4>❌ Dates show as timestamps (2026-01-22 08:57:07) in PPT</h4>
<p>This was fixed — dates now format as <code>DD-MMM-YYYY</code> using the same
<code>format_date()</code> logic as Word/PDF. Clear the browser cache and reload.</p>

<h4>❌ Preview shows no slides / all skipped</h4>
<p>Turn off <strong>Skip Titles</strong> and <strong>Skip Dividers</strong> in ⚙ Options,
then click <strong>Apply Filters</strong>.</p>

<h4>❌ RCA Report button stays disabled</h4>
<p>At least one slide must be assigned to a zone. The button enables as soon as any zone
has an image. Check the image count on each section header.</p>

<h4>❌ Images in preview are stacked in a single column</h4>
<p>After Update Preview, images in the Incident Preview are automatically reflowed into
horizontal rows by JavaScript (<code>_reflowPreviewImages</code>). If this doesn't happen,
check the browser console for errors and ensure the latest <code>converter.js</code> is loaded
(hard refresh: Ctrl+Shift+R).</p>

<h4>❌ LibreOffice error "[WinError 2]"</h4>
<p>LibreOffice is not at <code>C:\\Program Files\\LibreOffice\\program\\soffice.exe</code>.
Update <code>LIBREOFFICE_PATH</code> in <code>ppt_slide_renderer.py</code> and
<code>doc_to_pdf.py</code>.</p>""",
},

]


@converter_help_bp.route("/api/help/converter")
def converter_help_api():
    return jsonify({"module_title": "Converter — PPT to DOC Help", "topics": _TOPICS})
